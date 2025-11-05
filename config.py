# Configuration for image processing
CONFIG = {
    # API Settings
    "max_workers": 1,  # Single worker to avoid quota conflicts
    "batch_size": 1,   # Process one at a time to reduce server load
    "rate_limit_delay": 10.0,  # Increased delay between requests
    "max_retries": 5,  # Number of retry attempts
    "max_daily_quota": 250,  # Free tier limit
    
    # Backoff Strategy
    "initial_backoff": 120,  # Start with 2 minutes for 503 errors
    "max_backoff": 1800,    # Maximum 30 minutes wait
    "backoff_multiplier": 1.5,  # Gradual increase
    
    # File Settings
    "output_csv": "image_captions.csv",
    "quota_file": "daily_quota.json",
    "checkpoint_interval": 25,  # Save progress every N files
    
    # Supported image formats
    "image_extensions": (".jpg", ".jpeg", ".png", ".webp", ".bmp"),
    
    # Prompt template
    "prompt_template": """
Based on the image provided, generate Shutterstock-compliant metadata in English:

1. Description: Write a unique and detailed description of the image (maximum 200 characters). Focus on what is visible, the mood, style, and composition. Make it descriptive and searchable.

2. Keywords: Generate up to 50 relevant keywords separated by commas. Include:
   - Main subjects and objects in the image
   - Colors, mood, and style
   - Composition and perspective
   - Potential use cases
   - Related concepts

3. Categories: Select ONLY 1-2 categories from this EXACT list (do not create new categories):
   Abstract, Animals/Wildlife, Arts, Backgrounds/Textures, Beauty/Fashion, Buildings/Landmarks, Business/Finance, Celebrities, Education, Food and drink, Healthcare/Medical, Holidays, Industrial, Interiors, Miscellaneous, Nature, Objects, Parks/Outdoor, People, Religion, Science, Signs/Symbols, Sports/Recreation, Technology, Transportation, Vintage

4. Editorial: Answer "yes" if the image contains recognizable people, places, brands, or copyrighted material that would require editorial licensing. Otherwise "no".

5. Mature content: Answer "yes" if the image contains nudity, violence, or adult themes. Otherwise "no".

6. Illustration: Answer "yes" if this is an illustration, drawing, or digitally created artwork. Answer "no" if it's a photograph.

Please format your response exactly like this:
Description: [your description here]
Keywords: [keyword1, keyword2, keyword3, ...]
Categories: [category1, category2]
Editorial: [yes]
Mature content: [yes/no]
illustration: [yes/no]
"""
}