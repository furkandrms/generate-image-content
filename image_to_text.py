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
folder_path = "/Users/furkandurmus/Desktop/test"

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
    content = ""
    hashtags = []
    
    # Extract content
    content_match = re.search(r'content:\s*(.+?)(?=hashtags:|$)', response_text, re.DOTALL | re.IGNORECASE)
    if content_match:
        content = content_match.group(1).strip()
    
    # Extract hashtags
    hashtags_match = re.search(r'hashtags:\s*\[(.*?)\]', response_text, re.DOTALL | re.IGNORECASE)
    if hashtags_match:
        hashtags_text = hashtags_match.group(1)
        hashtags = [tag.strip().strip('"\'') for tag in hashtags_text.split(',') if tag.strip()]
    
    return content, hashtags

def image_to_text_single(file_path, prompt, client, max_retries=None):
    """Process single image with quota checking and retry mechanism"""
    max_retries = max_retries or CONFIG["max_retries"]
    
    # Check quota before processing
    if not quota_tracker.can_process():
        remaining = quota_tracker.get_remaining()
        print(f"Daily quota exceeded ({quota_tracker.used_today}/{MAX_DAILY_QUOTA}). Remaining: {remaining}")
        return file_path, "Error: Daily quota exceeded", []
    
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
            content, hashtags = parse_response(response_text)
            
            # Clean up uploaded file if API supports it
            try:
                client.files.delete(my_file.name)
            except Exception:
                pass
            
            # After successful processing, update quota
            quota_tracker.add_usage(1)
            
            return file_path, content, hashtags
        
        except Exception as e:
            error_str = str(e)
            
            # Check if it's a quota/rate limit error
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
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
                    return file_path, "Error: Quota exhausted after retries", []
            else:
                # For other errors, don't retry
                print(f"Error processing {file_path}: {str(e)}")
                return file_path, "Error generating content", []
    
    return file_path, "Error: Max retries exceeded", []

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
                    if row and len(row) > 0:
                        processed_files.add(row[0])  # file_name column
        except Exception as e:
            print(f"Warning: Could not load processed files: {e}")
    return processed_files

def save_to_csv_optimized(data, csv_path, append_mode=False):
    """Optimized CSV saving with progress"""
    mode = "a" if append_mode and os.path.exists(csv_path) else "w"
    write_header = mode == "w"
    
    with open(csv_path, mode=mode, newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        if write_header:
            writer.writerow(["file_name", "response_text", "hashtags"])
        
        for file_path, caption, hashtags in tqdm.tqdm(data, desc="Saving to CSV", unit="row"):
            file_name = Path(file_path).name
            writer.writerow([file_name, caption, ", ".join(hashtags)])

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