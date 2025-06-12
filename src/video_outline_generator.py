import os
from pathlib import Path
import subprocess
from src.transcription.whisper_transcriber import WhisperTranscriber
from src.transcription.outline_generator import OutlineGenerator
from src.uploaders.drive_uploader import DriveUploader
from src.uploaders.ftp_uploader import FTPUploader

class VideoOutlineGenerator:
    def __init__(self, root_dir, import_dir=None, web_dir=None, logs_dir=None):

        # Set base directories
        self.import_dir = os.path.abspath(import_dir if import_dir else os.path.join(root_dir, "import"))
        self.base_output_dir = os.path.abspath(os.path.join(web_dir if web_dir else os.path.join(root_dir, "web"), "public", "videos"))
        self.logs_dir = os.path.abspath(logs_dir if logs_dir else os.path.join(root_dir, "logs"))
        
        # Create directories if they don't exist
        os.makedirs(self.base_output_dir, exist_ok=True)
        os.makedirs(self.import_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)

        self.whisper_api_key = os.getenv('WHISPER_API_KEY')
        self.openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
        
        if not self.whisper_api_key or not self.openrouter_api_key:
            raise ValueError("Please set WHISPER_API_KEY and OPENROUTER_API_KEY in .env file")
        
        # Initialize uploaders if their configuration files exist
        drive_creds_path = os.path.abspath(os.path.join('config', 'google_drive_credentials.json'))
        ftp_settings_path = os.path.abspath(os.path.join('config', 'ftp_settings.json'))
        
        self.drive_uploader = DriveUploader() if os.path.exists(drive_creds_path) else None
        self.ftp_uploader = FTPUploader() if os.path.exists(ftp_settings_path) else None
        
        if not self.drive_uploader and not self.ftp_uploader:
            print("Warning: No upload service configured. Large files (>100MB) will not be processed.")
        
        # Initialize transcriber and outline generator
        self.transcriber = WhisperTranscriber(
            self.whisper_api_key,
            logs_dir=self.logs_dir,
            import_path=self.import_dir,
            drive_uploader=self.drive_uploader,
            ftp_uploader=self.ftp_uploader
        )
        self.outline_generator = OutlineGenerator(
            self.openrouter_api_key,
            logs_dir=self.logs_dir,
            import_path=self.import_dir
            )        

    def process_video(self, video_path):
        """Process video and generate outline"""
        video_path = os.path.abspath(video_path)
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Generate output paths within the video-specific directory
        outline_path = os.path.join(self.import_dir, f"{os.path.splitext(os.path.basename(video_path))[0]}.outline.json")

        # Extract audio from video (or use existing audio file)
        audio_path = extract_audio(video_path)
        
        try:
            # Transcribe audio
            srt_content = self.transcriber.transcribe_audio(audio_path)
            
            # Generate outline
            outline = self.outline_generator.generate_outline(srt_content, outline_path)
            
            # Move processed file to a 'processed' subdirectory
            processed_dir = os.path.join(self.import_dir, "processed")
            os.makedirs(processed_dir, exist_ok=True)
            processed_path = os.path.join(processed_dir, os.path.basename(video_path))
            os.rename(video_path, processed_path)
            print(f"Moved processed file to: {processed_path}")
            
        finally:
            pass
            # Clean up audio file if it was created
            #print(f"Cleaning up audio file: {audio_path}")
            #if audio_path != video_path:
            #    os.remove(audio_path)

    def process_all_videos(self):
        """Process all video files in the import directory"""
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv'}
        
        # Get all video files in the import directory
        video_files = [
            os.path.join(self.import_dir, f) for f in os.listdir(self.import_dir)
            if os.path.isfile(os.path.join(self.import_dir, f)) and 
            os.path.splitext(f)[1].lower() in video_extensions
        ]
        
        if not video_files:
            print("No video files found in the import directory")
            return
        
        print(f"Found {len(video_files)} video files to process")
        
        for video_file in video_files:
            try:
                print(f"\nProcessing: {os.path.basename(video_file)}")
                self.process_video(video_file)
            except Exception as e:
                print(f"Error processing {os.path.basename(video_file)}: {e}")
                # Move failed file to a 'failed' subdirectory
                failed_dir = os.path.join(self.import_dir, "failed")
                os.makedirs(failed_dir, exist_ok=True)
                failed_path = os.path.join(failed_dir, os.path.basename(video_file))
                os.rename(video_file, failed_path)
                print(f"Moved failed file to: {failed_path}")

def extract_audio(video_path):
    """Extract audio from video file"""
    audio_path = os.path.splitext(video_path)[0] + '.mp3'
    if not os.path.exists(audio_path):
        subprocess.run(['ffmpeg', '-i', video_path, '-q:a', '0', '-map', 'a', audio_path])
    return audio_path 