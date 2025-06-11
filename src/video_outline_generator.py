import os
from pathlib import Path
import subprocess
from src.transcription.whisper_transcriber import WhisperTranscriber
from src.transcription.outline_generator import OutlineGenerator
from src.uploaders.drive_uploader import DriveUploader
from src.uploaders.ftp_uploader import FTPUploader

class VideoOutlineGenerator:
    def __init__(self):
        self.whisper_api_key = os.getenv('WHISPER_API_KEY')
        self.openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
        
        if not self.whisper_api_key or not self.openrouter_api_key:
            raise ValueError("Please set WHISPER_API_KEY and OPENROUTER_API_KEY in .env file")
        
        # Initialize uploaders if their configuration files exist
        drive_creds_path = os.path.join('config', 'google_drive_credentials.json')
        ftp_settings_path = os.path.join('config', 'ftp_settings.json')
        
        self.drive_uploader = DriveUploader() if os.path.exists(drive_creds_path) else None
        self.ftp_uploader = FTPUploader() if os.path.exists(ftp_settings_path) else None
        
        if not self.drive_uploader and not self.ftp_uploader:
            print("Warning: No upload service configured. Large files (>100MB) will not be processed.")
        
        # Initialize transcriber and outline generator
        self.transcriber = WhisperTranscriber(
            self.whisper_api_key,
            drive_uploader=self.drive_uploader,
            ftp_uploader=self.ftp_uploader
        )
        self.outline_generator = OutlineGenerator(self.openrouter_api_key)
        
        # Base directories
        self.import_dir = Path("import")
        self.base_output_dir = Path("web/public/videos")
        self.base_output_dir.mkdir(parents=True, exist_ok=True)
        self.import_dir.mkdir(parents=True, exist_ok=True)

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
        
        try:
            # Transcribe audio
            srt_content = self.transcriber.transcribe_audio(audio_path)
            
            # Save transcription
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)
            print(f"Transcription saved to: {srt_path}")

            # Exit after transcription
            exit()

            # Generate outline
            outline = self.outline_generator.generate_outline(srt_content)
            
            # Save outline
            self.outline_generator.save_outline(outline, outline_path)
            print(f"Outline saved to: {outline_path}")
            
            # Move processed file to a 'processed' subdirectory
            processed_dir = self.import_dir / "processed"
            processed_dir.mkdir(exist_ok=True)
            processed_path = processed_dir / video_path.name
            video_path.rename(processed_path)
            print(f"Moved processed file to: {processed_path}")
            
        finally:
            # Clean up audio file if it was created
            if audio_path != video_path:
                os.remove(audio_path)

    def process_all_videos(self):
        """Process all video files in the import directory"""
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv'}
        
        # Get all video files in the import directory
        video_files = [
            f for f in self.import_dir.iterdir()
            if f.is_file() and f.suffix.lower() in video_extensions
        ]
        
        if not video_files:
            print("No video files found in the import directory")
            return
        
        print(f"Found {len(video_files)} video files to process")
        
        for video_file in video_files:
            try:
                print(f"\nProcessing: {video_file.name}")
                self.process_video(video_file)
            except Exception as e:
                print(f"Error processing {video_file.name}: {e}")
                # Move failed file to a 'failed' subdirectory
                failed_dir = self.import_dir / "failed"
                failed_dir.mkdir(exist_ok=True)
                failed_path = failed_dir / video_file.name
                video_file.rename(failed_path)
                print(f"Moved failed file to: {failed_path}")

def extract_audio(video_path):
    """Extract audio from video file"""
    audio_path = os.path.splitext(video_path)[0] + '.mp3'
    if not os.path.exists(audio_path):
        subprocess.run(['ffmpeg', '-i', video_path, '-q:a', '0', '-map', 'a', audio_path])
    return audio_path 