import os
import time
import requests
from pathlib import Path
import subprocess
from ..uploaders.drive_uploader import DriveUploader
from ..uploaders.ftp_uploader import FTPUploader

class WhisperTranscriber:
    def __init__(self, api_key, drive_uploader=None, ftp_uploader=None):
        self.whisper_api_key = api_key
        self.drive_uploader = drive_uploader
        self.ftp_uploader = ftp_uploader
        self.callback_url = "https://videooutliner.24gatel.eu/whisper_callback.php"

    def split_audio_into_chunks(self, audio_path, chunk_duration=1800):  # 1800 seconds = 30 minutes
        """Split audio file into chunks of specified duration"""
        audio_dir = Path(audio_path).parent
        base_name = Path(audio_path).stem
        chunks = []
        
        # Get audio duration using ffprobe
        duration_cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
                       '-of', 'default=noprint_wrappers=1:nokey=1', audio_path]
        duration = float(subprocess.check_output(duration_cmd).decode().strip())
        
        # Calculate number of chunks needed
        num_chunks = int(duration / chunk_duration) + (1 if duration % chunk_duration > 0 else 0)
        
        print(f"Splitting {duration:.2f} seconds audio into {num_chunks} chunks")
        
        for i in range(num_chunks):
            chunk_path = audio_dir / f"{base_name}_chunk_{i:03d}.mp3"
            start_time = i * chunk_duration
            
            # Extract chunk using ffmpeg
            cmd = [
                'ffmpeg', '-y',  # Overwrite output files
                '-i', audio_path,
                '-ss', str(start_time),
                '-t', str(chunk_duration),
                '-acodec', 'libmp3lame',
                '-ar', '44100',
                '-ab', '192k',
                str(chunk_path)
            ]
            
            subprocess.run(cmd, check=True)
            chunks.append(str(chunk_path))
            
        return chunks

    def _process_audio_chunk(self, audio_path):
        """Process a single audio chunk"""
        url = "https://api.lemonfox.ai/v1/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {self.whisper_api_key}"
        }
        
        # Check file size
        file_size = os.path.getsize(audio_path)
        file_url = None
        file_id = None
        filename = None
        
        # Get the chunk filename without extension
        chunk_name = Path(audio_path).stem
        
        # Add chunk name to callback URL
        callback_url = f"{self.callback_url}?chunk={chunk_name}"
        
        data = {
            "language": "cs",
            "response_format": "srt",
            "callback_url": callback_url
        }
        
        print(f"Using callback URL for chunk: {callback_url}")
        
        # Handle large files through Google Drive or FTP
        if file_size > 100 * 1024 * 1024:  # 100MB in bytes
            print(f"Chunk size ({file_size / (1024*1024):.2f}MB) exceeds direct upload limit (100MB)")
            
            # Try Google Drive first, then FTP
            if self.drive_uploader:
                print("Uploading chunk to Google Drive...")
                file_id, file_url = self.drive_uploader.upload_file(audio_path)
                print(f"Chunk uploaded to Google Drive: {file_url}")
            elif self.ftp_uploader:
                print("Uploading chunk to FTP server...")
                file_url = self.ftp_uploader.upload_file(audio_path)
                filename = os.path.basename(audio_path)
                print(f"Chunk uploaded to FTP: {file_url}")
            else:
                raise Exception("Chunk too large for direct upload and no upload service configured.")
        
        try:
            if file_url:
                print(f"Using file URL for transcription: {file_url}")
                data["file"] = file_url
                files = None
            else:
                print("Using local file for transcription")
                files = {"file": open(audio_path, 'rb')}

            try:
                print(f"Attempting to connect to WhisperAPI at {url}")
                response = requests.post(url, headers=headers, files=files, data=data)
                
                # debug the response
                print(f"WhisperAPI response: {response.text}")

                if response.status_code != 200:
                    print(f"WhisperAPI returned status code: {response.status_code}")
                    print(f"Response text: {response.text}")
                    raise Exception(f"WhisperAPI error: {response.text}")
                
                # Clean up uploaded file if needed
                if file_id and self.drive_uploader:
                    print("Cleaning up Google Drive file...")
                    self.drive_uploader.delete_file(file_id)
                elif filename and self.ftp_uploader:
                    print("Cleaning up FTP file...")
                    self.ftp_uploader.delete_file(filename)
                    
                print("Waiting for callback response...")
                return self.wait_for_callback_response(chunk_name)
                    
            except requests.exceptions.ConnectionError as e:
                print(f"Connection error: {str(e)}")
            except requests.exceptions.Timeout as e:
                print(f"Request timed out: {str(e)}")
            except Exception as e:
                print(f"Unexpected error: {str(e)}")
                raise
        finally:
            if files and 'file' in files:
                files['file'].close()

    def wait_for_callback_response(self, chunk_name, max_wait_time=60*3600, check_interval=30):
        """Wait for the callback response file to appear in the import directory"""
        start_time = time.time()
        import_dir = Path("/import")
        import_dir.mkdir(parents=True, exist_ok=True)  # Create import directory if it doesn't exist
        
        while time.time() - start_time < max_wait_time:
            # Look for the specific chunk response file if chunk_name is provided
            response_file = import_dir / f"{chunk_name}.srt"
            if response_file.exists() and response_file.stat().st_mtime > start_time:
                print(f"Found callback response file: {response_file}")
                try:
                    with open(response_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Check if the content starts with error
                    if content.strip().lower().startswith("error"):
                        error_msg = content.strip()
                        response_file.unlink()
                        raise Exception(f"Transcription failed: {error_msg}")
                            
                    # Clean up the response file
                    response_file.unlink()
                    return content
                except Exception as e:
                    # If there's an error reading the file
                    print(f"Error processing callback response: {str(e)}")
                    if response_file.exists():
                        response_file.unlink()
                    raise
            
            print(f"Waiting for callback response... ({int(time.time() - start_time)}s elapsed)")
            time.sleep(check_interval)
        
        raise TimeoutError("Timed out waiting for callback response")

    def transcribe_audio(self, audio_path):
        """Transcribe audio file, handling large files by splitting into chunks"""
        file_size = os.path.getsize(audio_path)
        
        # If file is larger than 20MB, split into chunks
        if file_size > 20 * 1024 * 1024:  # 20MB
            print(f"File size ({file_size / (1024*1024):.2f}MB) exceeds 20MB, splitting into chunks")
            chunks = self.split_audio_into_chunks(audio_path)
            srt_contents = []
            
            for i, chunk_path in enumerate(chunks):
                print(f"Processing chunk {i+1}/{len(chunks)}")
                try:
                    # Process each chunk
                    chunk_srt = self._process_audio_chunk(chunk_path)
                    srt_contents.append(chunk_srt)
                finally:
                    # Clean up chunk file
                    os.remove(chunk_path)
            
            # Merge all SRT contents
            print("Merging SRT contents from all chunks")
            return self.merge_srt_files(srt_contents)
        else:
            # Process small files normally
            return self._process_audio_chunk(audio_path) 