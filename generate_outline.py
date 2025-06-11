#!/usr/bin/env python3

import os
import json
import argparse
import requests
from pathlib import Path
from dotenv import load_dotenv
from datetime import timedelta
from tqdm import tqdm
import subprocess
from drive_uploader import DriveUploader
from ftp_uploader import FTPUploader

# Load environment variables
load_dotenv()

class LectureOutlineGenerator:
    def __init__(self):
        self.whisper_api_key = os.getenv('WHISPER_API_KEY')
        self.openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
        
        if not self.whisper_api_key or not self.openrouter_api_key:
            raise ValueError("Please set WHISPER_API_KEY and OPENROUTER_API_KEY in .env file")
        
        # Initialize uploaders if their configuration files exist
        self.drive_uploader = DriveUploader() if os.path.exists('google_drive_credentials.json') else None
        self.ftp_uploader = FTPUploader() if os.path.exists('ftp_settings.json') else None
        
        if not self.drive_uploader and not self.ftp_uploader:
            print("Warning: No upload service configured. Large files (>100MB) will not be processed.")
        
        # Base output directory
        self.base_output_dir = Path("web/public/videos")
        self.base_output_dir.mkdir(parents=True, exist_ok=True)

    def format_timestamp(self, seconds):
        """Convert seconds to HH:MM:SS format"""
        return str(timedelta(seconds=int(seconds)))

    def transcribe_video(self, video_path):
        """Transcribe video using WhisperAPI.com and return SRT content"""
        print(f"Transcribing video: {video_path}")
        
        # Prepare the video file for upload
        with open(video_path, 'rb') as video_file:
            files = {
                'file': (video_path.name, video_file, 'video/mp4'),
                'language': (None, 'cs'),
                'speaker_labels': (None, 'true'),
                'response_format': (None, 'srt')
            }
            
            headers = {
                'Authorization': f'Bearer {self.whisper_api_key}'
            }
            
            response = requests.post(
                'https://api.lemonfox.ai/v1/audio/transcriptions',
                headers=headers,
                files=files
            )
            
            if response.status_code != 200:
                raise Exception(f"WhisperAPI error: {response.text}")
            
            return response.text

    def save_srt(self, srt_content, output_path):
        """Save SRT content to file"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

    def generate_outline(self, srt_content):
        """Generate outline using OpenRouter API"""
        prompt = f"""Analyze this lecture transcript and create a structured outline in JSON format.
        Include main topics, subtopics, and their start times.
        Return ONLY valid JSON with this structure:
        [
            {{
                "title": "Main Topic",
                "start_time": "HH:MM:SS",
                "subsections": [
                    {{
                        "title": "Subtopic",
                        "start_time": "HH:MM:SS",
                        "subsections": []
                    }}
                ]
            }}
        ]

        Transcript:
        {srt_content}
        """

        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "anthropic/claude-3-opus-20240229",
            "messages": [{"role": "user", "content": prompt}]
        }

        print("Generating outline using OpenRouter API...")
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data
        )

        if response.status_code != 200:
            raise Exception(f"OpenRouter API error: {response.text}")

        try:
            outline = json.loads(response.json()["choices"][0]["message"]["content"])
            return outline
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse JSON response: {e}")

    def upload_to_whisper(self, audio_path):
        url = "https://api.lemonfox.ai/v1/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {self.whisper_api_key}"
        }
        
        # Check file size
        file_size = os.path.getsize(audio_path)
        file_url = None
        file_id = None
        filename = None
        
        if file_size > 100 * 1024 * 1024:  # 100MB in bytes
            print(f"File size ({file_size / (1024*1024):.2f}MB) exceeds direct upload limit (100MB)")
            
            # Try Google Drive first, then FTP
            if self.drive_uploader:
                print("Uploading to Google Drive...")
                file_id, file_url = self.drive_uploader.upload_file(audio_path)
                print(f"File uploaded to Google Drive: {file_url}")
            elif self.ftp_uploader:
                print("Uploading to FTP server...")
                file_url = self.ftp_uploader.upload_file(audio_path)
                filename = os.path.basename(audio_path)
                print(f"File uploaded to FTP: {file_url}")
            else:
                raise Exception("File too large for direct upload and no upload service configured.")
        
        data = {
            "language": "english",
            "response_format": "srt"
        }
        
        if file_url:
            data["file"] = file_url
            files = None
        else:
            files = {"file": open(audio_path, 'rb')}
        
        try:
            print(f"Attempting to connect to WhisperAPI at {url}")
            response = requests.post(url, headers=headers, files=files, data=data, timeout=30)
            if response.status_code != 200:
                print(f"WhisperAPI returned status code: {response.status_code}")
                print(f"Response text: {response.text}")
                raise Exception(f"WhisperAPI error: {response.text}")
            
            # Clean up uploaded file
            if file_id and self.drive_uploader:
                print("Cleaning up Google Drive file...")
                self.drive_uploader.delete_file(file_id)
            elif filename and self.ftp_uploader:
                print("Cleaning up FTP file...")
                self.ftp_uploader.delete_file(filename)
            
            return response.text
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error: {str(e)}")
            print("Please check your internet connection and DNS settings")
            raise
        except requests.exceptions.Timeout as e:
            print(f"Request timed out: {str(e)}")
            raise
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            raise
        finally:
            if files and 'file' in files:
                files['file'].close()

    def process_video(self, video_path):
        """Process video and generate outline"""
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Create video-specific output directory
        video_dir = self.base_output_dir / video_path.stem
        video_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate output paths within the video-specific directory
        srt_path = video_dir / f"{video_path.stem}.srt"
        outline_path = video_dir / f"{video_path.stem}_outline.json"

        # Extract audio from video (or use existing audio file)
        audio_path = extract_audio(video_path)
        
        # Upload audio to WhisperAPI
        response = self.upload_to_whisper(audio_path)
        
        # Transcribe video
        srt_content = self.transcribe_video(video_path)
        self.save_srt(srt_content, srt_path)
        print(f"Transcription saved to: {srt_path}")

        # Generate outline
        outline = self.generate_outline(srt_content)
        
        # Save outline
        with open(outline_path, "w", encoding="utf-8") as f:
            json.dump(outline, f, ensure_ascii=False, indent=2)
        print(f"Outline saved to: {outline_path}")

def extract_audio(video_path):
    audio_path = os.path.splitext(video_path)[0] + '.mp3'
    if not os.path.exists(audio_path):
        subprocess.run(['ffmpeg', '-i', video_path, '-q:a', '0', '-map', 'a', audio_path])
    return audio_path

def main():
    parser = argparse.ArgumentParser(description="Generate lecture outline from video")
    parser.add_argument("video_path", help="Path to the video file")
    args = parser.parse_args()

    try:
        generator = LectureOutlineGenerator()
        video_path = Path(args.video_path)
        generator.process_video(video_path)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)

if __name__ == "__main__":
    main() 