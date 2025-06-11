# 🎥 Automatic Lecture Outline Generator

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

This Python script automatically generates a structured outline from lecture videos using WhisperAPI.com for transcription and OpenRouter's API for outline generation.

## Features

- Transcribes video to text using WhisperAPI.com (Whisper Large V3)
- Generates structured outlines with timestamps
- Supports Czech language (or auto-detection)
- Creates both SRT subtitles and JSON outlines
- Multi-level topic hierarchy
- Organizes output files in video-specific directories
- No local GPU required - uses cloud APIs
- Speaker detection included
- Affordable pricing ($0.17/hour after free trial)
- Handles large files (>100MB) via Google Drive or FTP upload

## Quick Start

```bash
# Clone the repository
git clone https://github.com/matak/videooutliner.git
cd videooutliner

# Install dependencies (using uv)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv pip install -r requirements.txt

# Set up your API keys
cp .env.example .env
# Edit .env with your API keys

# Run the script
python generate_outline.py path/to/lecture.mp4
```

## Alternative: Run with uv

You can also run the script directly using `uv`:

```bash
uv run python generate_outline.py path/to/lecture.mp4
```

## Prerequisites

- Python 3.8 or higher
- WhisperAPI.com API key (30 hours free trial available)
- OpenRouter API key
- FFmpeg (for audio extraction)
- Google Drive API credentials or FTP server (for files >100MB)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/matak/videooutliner.git
cd videooutliner
```

2. Install dependencies using either pip or uv:

Using pip:
```bash
pip install -r requirements.txt
```

Using uv (recommended, faster):
```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv pip install -r requirements.txt
```

3. Create a `.env` file in the project root:
```env
WHISPER_API_KEY=your_whisper_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

4. (Optional) Set up file upload for large files:

   a. For Google Drive:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Google Drive API
   - Create OAuth 2.0 credentials
   - Download the credentials and save as `google_drive_credentials.json` in the project directory

   b. For FTP:
   - Copy `ftp_settings.example.json` to `ftp_settings.json`
   - Edit `ftp_settings.json` with your FTP server details:
     ```json
     {
         "host": "ftp.example.com",
         "username": "your_username",
         "password": "your_password",
         "path": "/public_html/temp",
         "public_url": "https://example.com/temp"
     }
     ```

## Usage

Run the script with a video file as input:

```bash
python generate_outline.py path/to/lecture.mp4
```

The script will:
1. Create a `web/public/videos` directory if it doesn't exist
2. Create a subdirectory named after the video (without extension) in `web/public/videos`
3. Extract audio from the video file
4. For files >100MB:
   - Upload to Google Drive if configured
   - Or upload to FTP server if configured
   - Or raise an error if no upload service is configured
5. Upload the audio to WhisperAPI.com for transcription
6. Generate an SRT file with timestamps and transcript (including speaker detection)
7. Create a JSON outline with structured topics and timestamps
8. Clean up any temporary uploaded files

## Output Structure

For a video named `lecture.mp4`, the output will be organized as follows:

```
web/public/videos/
└── lecture/
    ├── lecture.srt
    └── lecture_outline.json
```

### SRT File
Standard subtitle format with timestamps and text, including speaker labels.

### JSON Outline
```json
[
  {
    "title": "Main Topic",
    "start_time": "00:00:00",
    "subsections": [
      {
        "title": "Subtopic",
        "start_time": "00:03:12",
        "subsections": []
      }
    ]
  }
]
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Notes

- Uses WhisperAPI.com for transcription (no local GPU required)
- First month includes 30 hours of free transcription
- After free trial, costs $0.17 per hour of audio
- Processing time depends on video length and API response times
- Each processed video gets its own directory in `web/public/videos`
- Includes speaker detection in the transcription
- Files larger than 100MB are automatically uploaded to Google Drive or FTP server
- Temporary uploaded files are automatically cleaned up after processing

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.