
# 🎥 Automatic Lecture Outline Generator (Python + Whisper + OpenRouter)

## 🧠 Goal

This project creates a Python script that automatically generates a structured outline from a lecture video. It uses:

- [OpenAI Whisper](https://github.com/openai/whisper) for transcription
- [OpenRouter](https://openrouter.ai) for LLM-based outline creation

The result is a multi-level outline in JSON format, with time-stamped sections and subsections describing the lecture’s content.

---

## 🚀 Features

- Accepts a video file as input (`.mp4`)
- Transcribes the video to subtitles using Whisper
- Parses the transcript and sends it to an LLM (via OpenRouter)
- Returns a JSON structure with:
  - Main topics
  - Nested subtopics (multi-dimensional)
  - Start time for each section in `HH:MM:SS` format

---

## 🧾 Script Workflow

1. **Input:** Video filename passed as CLI argument  
   Example: `python generate_outline.py lecture.mp4`

2. **Transcription:**  
   - Uses Whisper (`large-v3` model) to create timestamped `.srt` file  
   - Language: Czech (or autodetected)  
   - Output: `./output/lecture.srt`

3. **LLM Prompting (OpenRouter):**  
   - Sends the parsed `.srt` content to an OpenRouter-compatible LLM  
   - Prompt instructs model to detect:
     - Main topics
     - Nested subtopics
     - Start times
   - Receives JSON output with arbitrarily deep nested structure

4. **Output:**  
   JSON saved to `./output/lecture_outline.json` in the format:

```json
[
  {
    "title": "Main Topic A",
    "start_time": "00:00:00",
    "subsections": [
      {
        "title": "Subtopic A1",
        "start_time": "00:03:12",
        "subsections": [
          {
            "title": "Nested Subpoint A1.1",
            "start_time": "00:04:00"
          }
        ]
      }
    ]
  }
]
```

---

## 🔐 Authentication

- The script uses an API key from OpenRouter.
- Store your key in a `.env` file:
  ```env
  OPENROUTER_API_KEY=your_api_key_here
  ```
- Or set it as an environment variable.

---

## 📦 Dependencies

Install dependencies via pip:

```bash
pip install -r requirements.txt
```

Dependencies:
- `openai-whisper`
- `ffmpeg` (must be installed on system and in PATH)
- `requests`
- `python-dotenv`

---

## 📂 Folder Structure

```
project/
│
├── generate_outline.py       # Main script
├── requirements.txt
├── .env                      # OpenRouter API key
└── output/
    ├── lecture.srt
    ├── lecture_outline.json
```

---

## 🏁 Example Usage

```bash
python generate_outline.py lecture.mp4
```

---

## ⚠️ Notes

- Make sure `ffmpeg` is installed and available in your system path.
- Whisper transcription might take time depending on video length and model size.
- The LLM must return **valid JSON**. It should support recursively nested `subsections` for deeply structured outlines.
