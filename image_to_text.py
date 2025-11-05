from google import genai
import os 
from dotenv import load_dotenv
import csv
import re
from concurrent.futures import ThreadPoolExecutor
import time
from pathlib import Path
import tqdm


from quota_tracker import QuotaTracker
from config import CONFIG


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
folder_path = "your folder path"  # Set your image folder path here

# Use config settings
MAX_WORKERS = CONFIG["max_workers"]
BATCH_SIZE = CONFIG["batch_size"]
RATE_LIMIT_DELAY = CONFIG["rate_limit_delay"]
MAX_DAILY_QUOTA = CONFIG["max_daily_quota"]

# Initialize quota tracker
quota_tracker = QuotaTracker(quota_file=CONFIG["quota_file"], max_daily=MAX_DAILY_QUOTA)

def create_client(): 
    client = genai.Client(api_key=GEMINI_API_KEY)
    print("Client initialized.")
    return client

prompt = CONFIG["prompt_template"]

def parse_response(response_text):
    """Parse the AI response to extract content and hashtags"""
    Description = ""
    Keywords = []
    Categories = []
    Editorial = "no"  # Default to no
    Mature_content = "no"  # Default to no
    illustration = "no"  # Default to no for photos

    # Extract content/description - look for the main descriptive text
    # Try different patterns to extract description
    content_patterns = [
        r'Description:\s*(.+?)(?=Keywords:|$)',  # Structured format
        r'^(.+?)(?:#|Keywords:|$)',  # Text before hashtags
        r'(.+?)(?=\n|$)'  # First line/paragraph
    ]
    
    for pattern in content_patterns:
        content_match = re.search(pattern, response_text, re.DOTALL | re.IGNORECASE)
        if content_match:
            Description = content_match.group(1).strip()
            # Clean up common formatting issues
            Description = re.sub(r'\n+', ' ', Description)  # Replace newlines with spaces
            Description = re.sub(r'\s+', ' ', Description)  # Replace multiple spaces with single space
            Description = Description.strip('"\'')  # Remove quotes
            if Description and len(Description) > 10:  # Make sure we have substantial content
                break
    
    # If no structured description found, use the whole response (cleaned)
    if not Description or len(Description) < 10:
        Description = response_text.strip()
        Description = re.sub(r'\n+', ' ', Description)
        Description = re.sub(r'\s+', ' ', Description)
        Description = Description.strip('"\'')

    # Extract keywords - try multiple patterns
    keywords_patterns = [
        r'Keywords:\s*\[(.*?)\]',  # [keyword1, keyword2]
        r'Keywords:\s*(.+?)(?=\n|$)',  # Keywords: keyword1, keyword2
        r'#(\w+)',  # #hashtags
        r'(?:^|\s)#([^\s,]+)',  # hashtags with boundaries
    ]
    
    for pattern in keywords_patterns:
        keywords_match = re.findall(pattern, response_text, re.DOTALL | re.IGNORECASE)
        if keywords_match:
            if pattern.startswith(r'Keywords:'):
                # Handle comma-separated keywords
                keywords_text = keywords_match[0] if keywords_match else ""
                Keywords = [tag.strip().strip('"\'') for tag in keywords_text.split(',') if tag.strip()]
            else:
                # Handle hashtag format
                Keywords = [tag.strip() for tag in keywords_match if tag.strip()]
            break
    
    # Clean up keywords
    Keywords = [kw for kw in Keywords if kw and len(kw) > 1]  # Remove empty or single char keywords
    
    # Extract categories if mentioned
    categories_match = re.search(r'Categories?:\s*(.+?)(?=\n|$)', response_text, re.IGNORECASE)
    if categories_match:
        categories_text = categories_match.group(1)
        Categories = [cat.strip().strip('"\'') for cat in categories_text.split(',') if cat.strip()]

    return Description, Keywords, Categories, Editorial, Mature_content, illustration

def image_to_text_single(file_path, prompt, client, max_retries=None):
    """Process single image with quota checking and retry mechanism"""
    max_retries = max_retries or CONFIG["max_retries"]
    
    # Check quota before processing
    if not quota_tracker.can_process():
        remaining = quota_tracker.get_remaining()
        print(f"Daily quota exceeded ({quota_tracker.used_today}/{MAX_DAILY_QUOTA}). Remaining: {remaining}")
        return file_path, "Error: Daily quota exceeded", [], [], "no", "no", "no"
    
    for attempt in range(max_retries):
        try:
            # Add rate limiting
            time.sleep(RATE_LIMIT_DELAY)
            
            my_file = client.files.upload(file=file_path)
            
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=[my_file, prompt],
            )

            response_text = response.text
            description, keywords, categories, editorial, mature_content, illustration = parse_response(response_text)
            
            # Clean up uploaded file if API supports it
            try:
                client.files.delete(my_file.name)
            except Exception:
                pass
            
            # After successful processing, update quota
            quota_tracker.add_usage(1)
            
            return file_path, description, keywords, categories, editorial, mature_content, illustration
        
        except Exception as e:
            error_str = str(e)
            
            # Check if it's a 503 service unavailable error
            if "503" in error_str or "UNAVAILABLE" in error_str or "overloaded" in error_str.lower():
                retry_delay = CONFIG["initial_backoff"] * (attempt + 1)  # Progressive delay
                retry_delay = min(retry_delay, CONFIG["max_backoff"])
                
                if attempt < max_retries - 1:
                    print(f"Model overloaded for {file_path}. Waiting {retry_delay:.1f}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"Model still overloaded after {max_retries} retries for {file_path}")
                    return file_path, "Error: Model overloaded", [], [], "no", "no", "no"
            
            # Check if it's a quota/rate limit error
            elif "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                # Extract retry delay from error message if available
                retry_delay = CONFIG["initial_backoff"]  # Use config value
                
                # Try to parse the retry delay from error message
                try:
                    import re
                    delay_match = re.search(r'retry in ([\d.]+)s', error_str)
                    if delay_match:
                        retry_delay = min(float(delay_match.group(1)) + 5, CONFIG["max_backoff"])  # Cap at max_backoff
                    else:
                        # Try milliseconds format
                        delay_match = re.search(r'retry in ([\d.]+)ms', error_str)
                        if delay_match:
                            retry_delay = min((float(delay_match.group(1)) / 1000) + 1, CONFIG["max_backoff"])
                except Exception:
                    pass
                
                if attempt < max_retries - 1:
                    print(f"Quota exceeded for {file_path}. Waiting {retry_delay:.1f}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"Max retries reached for {file_path}: {error_str}")
                    return file_path, "Error: Quota exhausted after retries", [], [], "no", "no", "no"
            else:
                # For other errors, don't retry
                print(f"Error processing {file_path}: {str(e)}")
                return file_path, "Error generating content", [], [], "no", "no", "no"
    
    return file_path, "Error: Max retries exceeded", [], [], "no", "no", "no"

def process_batch(file_paths, prompt, client):
    """Process a batch of images"""
    results = []
    for file_path in tqdm.tqdm(file_paths, desc="Batch processing", leave=False):
        result = image_to_text_single(file_path, prompt, client)
        results.append(result)
    return results

def get_image_files(folder_path):
    """Get all image files from folder"""
    image_extensions = CONFIG["image_extensions"]
    image_files = []
    
    all_files = os.listdir(folder_path)
    for file_name in tqdm.tqdm(all_files, desc="Scanning files", unit="file"):
        if file_name.lower().endswith(image_extensions):
            file_path = os.path.join(folder_path, file_name)
            image_files.append(file_path)
    
    return image_files

def load_processed_files(csv_path):
    """Load already processed files from CSV to avoid reprocessing"""
    processed_files = set()
    if os.path.exists(csv_path):
        try:
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                next(reader, None)  # Skip header
                for row in reader:
                    if row and len(row) >= 1:  # At least filename should exist
                        processed_files.add(row[0])  # file_name column
        except Exception as e:
            print(f"Warning: Could not load processed files: {e}")
    return processed_files

def save_to_csv_optimized(data, csv_path, append_mode=False):
    """Optimized CSV saving with Shutterstock format"""
    mode = "a" if append_mode and os.path.exists(csv_path) else "w"
    write_header = mode == "w"
    
    # Use UTF-8 with BOM for better compatibility with Shutterstock
    encoding = "utf-8-sig" if write_header else "utf-8"
    
    with open(csv_path, mode=mode, newline="", encoding=encoding) as csv_file:
        writer = csv.writer(csv_file)
        if write_header:
            writer.writerow(["Filename", "Description", "Keywords", "Categories", "Editorial", "Mature content", "illustration"])
        
        for file_path, description, keywords, categories, editorial, mature_content, illustration in tqdm.tqdm(data, desc="Saving to CSV", unit="row"):
            file_name = Path(file_path).name
            
            # Format keywords as comma-separated string
            keywords_str = ",".join(keywords) if keywords else ""
            
            # Format categories as comma-separated string
            categories_str = ",".join(categories) if categories else ""
            
            writer.writerow([
                file_name, 
                description, 
                keywords_str, 
                categories_str, 
                editorial, 
                mature_content, 
                illustration
            ])

def create_batches(items, batch_size):
    """Split items into batches"""
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]

if __name__ == "__main__":
    start_time = time.time()
    
    # Get all image files
    image_files = get_image_files(folder_path)
    total_files = len(image_files)
    
    if total_files == 0:
        print("No image files found!")
        exit()
    
    # Load already processed files to skip them
    csv_path = CONFIG["output_csv"]
    processed_files = load_processed_files(csv_path)
    
    # Filter out already processed files
    remaining_files = []
    for file_path in image_files:
        file_name = Path(file_path).name
        if file_name not in processed_files:
            remaining_files.append(file_path)
    
    print(f"Found {total_files} image files")
    print(f"Already processed: {len(processed_files)}")
    print(f"Remaining to process: {len(remaining_files)}")
    
    # Show quota status
    quota_status = quota_tracker.get_status()
    print(f"Daily quota status: {quota_status['used']}/{quota_status['max']} (Remaining: {quota_status['remaining']})")
    
    if len(remaining_files) == 0:
        print("All files have been processed!")
        exit()
    
    # Create client
    client = create_client()
    
    # Process in batches with threading
    all_results = []
    processed_count = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Create batches
        batches = list(create_batches(remaining_files, BATCH_SIZE))
        
        # Submit batch jobs
        future_to_batch = {
            executor.submit(process_batch, batch, prompt, client): batch 
            for batch in batches
        }
        
        # Collect results with progress bar
        with tqdm.tqdm(total=len(remaining_files), desc="Processing images", unit="image") as pbar:
            for future in future_to_batch:
                try:
                    batch_results = future.result()
                    all_results.extend(batch_results)
                    processed_count += len(batch_results)
                    
                    # Update progress bar
                    pbar.update(len(batch_results))
                    
                    # Save intermediate results (append mode)
                    if processed_count % CONFIG["checkpoint_interval"] == 0:  # Save every N files
                        save_to_csv_optimized(all_results[-len(batch_results):], csv_path, append_mode=True)
                        pbar.write(f"Saved progress: {processed_count}/{len(remaining_files)} files processed")
                    
                except Exception as e:
                    pbar.write(f"Batch processing error: {e}")
    
    # Save final results (append mode)
    if all_results:
        save_to_csv_optimized(all_results, csv_path, append_mode=True)
    
    # Performance summary
    end_time = time.time()
    total_time = end_time - start_time
    avg_time_per_image = total_time / len(remaining_files) if len(remaining_files) > 0 else 0
    
    print("\n=== Performance Summary ===")
    print(f"Files processed this session: {len(remaining_files)}")
    print(f"Total time: {total_time:.2f} seconds")
    print(f"Average time per image: {avg_time_per_image:.2f} seconds")
    print(f"Results saved to {csv_path}")