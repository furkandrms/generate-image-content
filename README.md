# 🖼️ Image Content Generator

A Python application that automatically generates sales-oriented descriptions and hashtags for images using Google Gemini 2.5 Flash AI model. Optimized for e-commerce, social media marketing, and content creation.

## ✨ Features

- 🤖 **AI-Powered Content Generation**: Powerful visual analysis with Google Gemini 2.5 Flash model
- 📝 **Sales-Oriented Descriptions**: Compelling product descriptions within 190 character limit
- 🏷️ **Automatic Hashtag Generation**: 30+ relevant hashtags for each image
- ⚡ **Batch Processing**: Automatically processes all images in a folder
- 📊 **Quota Management**: Tracks daily API usage limits
- 🔄 **Smart Retry Logic**: Automatic retry on rate limits and error conditions
- 💾 **Progress Tracking**: Tracks processing progress with checkpoint saves
- 📈 **CSV Export**: Saves results in organized CSV format

## 📋 Supported Formats

- JPG/JPEG
- PNG
- WebP
- BMP

## 🚀 Installation

### Requirements

- Python 3.11+
- Google Gemini API key

### Install Dependencies

```bash
pip install google-generativeai python-dotenv tqdm aiofiles
```

### Environment Setup

1. Create a `.env` file:
```bash
touch .env
```

2. Add your API key:
```env
GEMINI_API_KEY=your_api_key_here
```

## ⚙️ Configuration

You can customize the following settings in `config.py`:

```python
CONFIG = {
    # API Settings
    "max_workers": 1,              # Number of concurrent processes
    "batch_size": 3,               # Batch size
    "rate_limit_delay": 5.0,       # Delay between requests (seconds)
    "max_retries": 5,              # Number of retry attempts
    "max_daily_quota": 250,        # Daily maximum quota
    
    # File Settings
    "output_csv": "image_captions.csv",    # Output file
    "checkpoint_interval": 25,             # Checkpoint save frequency
    
    # Supported formats
    "image_extensions": (".jpg", ".jpeg", ".png", ".webp", ".bmp"),
}
```

## 📖 Usage

### 1. Set Image Folder Path

In `image_to_text.py`, change the `folder_path` variable to your image folder:

```python
folder_path = "/path/to/your/images"
```

### 2. Run the Application

```bash
python image_to_text.py
```

### 3. Check Results

Once processing is complete, find your results in `image_captions.csv`:

| file_name | response_text | hashtags |
|-----------|---------------|-----------|
| product1.jpg | Stylish modern design... | #modern, #design, #style... |

## 📊 Output Format

Generated content for each image:

- **Content**: Sales-oriented description within 190 character limit
- **Hashtags**: 30+ relevant English hashtags

### Example Output

```
content: Modern minimalist coffee cup perfect for morning routine. Premium quality ceramic with elegant design for coffee lovers.
hashtags: [coffee, coffeecup, morning, minimalist, modern, ceramic, premium, elegant, design, coffeelovers, ...]
```

## 🛡️ Quota Management

The application automatically:
- ✅ Tracks daily API usage
- ✅ Checks quota limits
- ✅ Stops processing when daily limit is exceeded
- ✅ Saves quota information in `daily_quota.json`

## 🔧 Advanced Features

### Batch Processing
- Images are processed in groups
- Memory-efficient approach
- Progress tracking with visual feedback

### Error Handling
- Automatic waiting on rate limit errors
- Exponential backoff strategy
- Error reporting for unprocessable files

### Resume Capability
- Continues interrupted processes from where they left off
- Skips already processed files
- Safe saving with checkpoint system

## 📁 Project Structure

```
generate-image-content/
├── image_to_text.py      # Main application
├── config.py             # Configuration settings
├── quota_tracker.py      # Quota management
├── .env                  # Environment variables
├── README.md             # Documentation
├── daily_quota.json      # Quota tracking file (auto-generated)
└── image_captions.csv    # Output file (auto-generated)
```

## 🚨 Important Notes

1. **API Key**: Store your Google Gemini API key securely in the `.env` file
2. **Quota Limits**: Free tier has a daily limit of 250 requests
3. **Rate Limiting**: 5-second delay between requests to avoid rate limits
4. **Backup**: Regularly backup your important data

## 🤝 Contributing

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## 📞 Contact

Feel free to open an issue for questions or suggestions.

---

**⭐ If you find this project useful, don't forget to give it a star!**