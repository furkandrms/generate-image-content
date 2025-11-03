# Configuration for image processing
CONFIG = {
    # API Settings
    "max_workers": 1,  # Single worker to avoid quota conflicts
    "batch_size": 3,   # Smaller batches
    "rate_limit_delay": 5.0,  # Seconds between requests
    "max_retries": 5,  # Number of retry attempts
    "max_daily_quota": 250,  # Free tier limit
    
    # Backoff Strategy
    "initial_backoff": 60,  # Initial backoff time in seconds
    "max_backoff": 3600,    # Maximum backoff time (1 hour)
    "backoff_multiplier": 2,  # Exponential backoff multiplier
    
    # File Settings
    "output_csv": "image_captions.csv",
    "quota_file": "daily_quota.json",
    "checkpoint_interval": 25,  # Save progress every N files
    
    # Supported image formats
    "image_extensions": (".jpg", ".jpeg", ".png", ".webp", ".bmp"),
    
    # Prompt template
    "prompt_template": """
Based on the following image subject:

Write a compelling and sales-oriented English description/title, with a maximum length of 190 characters.

Generate a list of at least 30 relevant English keywords (hashtags) to support the description.

Please format your response exactly like this:
content: [your description here]
hashtags: [hashtag1, hashtag2, hashtag3, ...]
"""
}