import os
import time
import requests
from pathlib import Path
import subprocess
from src.utils.srt_utils import SRTUtils
from src.utils.api_interaction_logger import ApiInteractionLogger

class WhisperTranscriber:
    def __init__(self, api_key, logs_dir, import_path, drive_uploader=None, ftp_uploader=None, chunk_duration_minutes=30):
        self.whisper_api_key = api_key
        self.drive_uploader = drive_uploader
        self.ftp_uploader = ftp_uploader
        self.callback_url = "https://videooutliner.24gatel.eu/whisper_callback.php"
        self.import_path = os.path.abspath(import_path)
        self.logs_dir = os.path.abspath(logs_dir)
        self.chunk_duration_minutes = chunk_duration_minutes
        self.api_logger = ApiInteractionLogger(self.logs_dir)

    def split_audio_into_chunks(self, audio_path, chunk_duration=None):  # chunk_duration in seconds
        """Split audio file into chunks of specified duration"""
        if chunk_duration is None:
            chunk_duration = self.chunk_duration_minutes * 60  # Convert minutes to seconds
        audio_path = os.path.abspath(audio_path)
        audio_dir = os.path.abspath(os.path.dirname(audio_path))
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        chunks = []
        
        # Get audio duration using ffprobe
        duration_cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
                       '-of', 'default=noprint_wrappers=1:nokey=1', audio_path]
        duration = float(subprocess.check_output(duration_cmd).decode().strip())
        
        # Calculate number of chunks needed
        num_chunks = int(duration / chunk_duration) + (1 if duration % chunk_duration > 0 else 0)
        
        print(f"Splitting {duration:.2f} seconds audio into {num_chunks} chunks")
        
        for i in range(num_chunks):
            chunk_path = os.path.join(audio_dir, f"{base_name}_chunk_{i:03d}.mp3")
            
            # Check if chunk already exists
            if os.path.exists(chunk_path):
                print(f"Chunk {i+1}/{num_chunks} already exists, skipping: {chunk_path}")
                chunks.append(chunk_path)
                continue
                
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
                chunk_path
            ]
            
            print(f"Creating chunk {i+1}/{num_chunks}: {chunk_path}")
            subprocess.run(cmd, check=True)
            chunks.append(chunk_path)
            
        return chunks

    def _process_audio_chunk(self, audio_path):
        """Process a single audio chunk"""
        audio_path = os.path.abspath(audio_path)
        
        # Get the chunk filename without extension
        chunk_name = os.path.splitext(os.path.basename(audio_path))[0]
        
        # Check if SRT file already exists
        srt_path = os.path.join(self.import_path, f"{chunk_name}.srt")
        if os.path.exists(srt_path):
            print(f"SRT file already exists for chunk {chunk_name}, returning existing content")
            with open(srt_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.strip().lower().startswith("error"):
                    raise Exception(f"Existing transcription failed: {content.strip()}")
                return content
        
        url = "https://api.lemonfox.ai/v1/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {self.whisper_api_key}"
        }
        
        # Check file size
        file_size = os.path.getsize(audio_path)
        file_url = None
        file_id = None
        filename = None
        
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

            # Log the request before sending
            log_base_name = f"{audio_path}_{chunk_name}"
            self.api_logger.log_request(log_base_name, {
                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
                'url': url,
                'headers': headers,
                'data': data,
                'files': 'file_url' if file_url else 'local file',
                'chunk_name': chunk_name
            })

            try:
                print(f"Attempting to connect to WhisperAPI at {url}")
                response = requests.post(
                    url, 
                    headers=headers, 
                    files=files, 
                    data=data
                    )
                
                # debug the response
                print(f"WhisperAPI response: {response.text}")

                # Log the response after receiving
                self.api_logger.log_response(log_base_name, {
                    'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
                    'status_code': response.status_code,
                    'headers': dict(response.headers),
                    'text': response.text,
                    'encoding': response.encoding,
                    'chunk_name': chunk_name
                })

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
                    
                print(f"Go to waiting for callback response... {chunk_name}")
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

    def wait_for_callback_response(self, chunk_name, max_wait_time=3600, check_interval=30):
        """Wait for the callback response file to appear in the import directory"""
        start_time = time.time()
        os.makedirs(self.import_path, exist_ok=True)  # Create import directory if it doesn't exist
        
        while time.time() - start_time < max_wait_time:
            # Look for the specific chunk response file if chunk_name is provided
            response_file = os.path.join(self.import_path, f"{chunk_name}.srt")
            if os.path.exists(response_file):
                print(f"Found callback response file: {response_file}")
                try:
                    with open(response_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Check if the content starts with error
                    if content.strip().lower().startswith("error"):
                        error_msg = content.strip()
                        #os.remove(response_file)
                        raise Exception(f"Transcription failed: {error_msg}")
                            
                    # Clean up the response file
                    #os.remove(response_file)
                    return content
                except Exception as e:
                    # If there's an error reading the file
                    print(f"Error processing callback response: {str(e)}")
                    #if os.path.exists(response_file):
                    #    os.remove(response_file)
                    raise
            
            print(f"Waiting for callback response... {response_file} => ({int(time.time() - start_time)}s elapsed)")
            time.sleep(check_interval)
        
        raise TimeoutError("Timed out waiting for callback response")

    def transcribe_audio(self, audio_path):
        """Transcribe audio file, handling large files by splitting into chunks"""
        audio_path = os.path.abspath(audio_path)
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
                    #os.remove(chunk_path)
                    #print(f"Cleaning up chunk file: {chunk_path}")
                    pass
            
            # Generate destination path for merged SRT
            base_name = os.path.splitext(os.path.basename(audio_path))[0]
            destination_path = os.path.join(self.import_path, f"{base_name}.srt")
            
            # Merge all SRT contents using SRTUtils
            print("Merging SRT contents from all chunks")
            return SRTUtils.merge_srt_files(srt_contents, self.chunk_duration_minutes, destination_path)
        else:
            # Process small files normally
            return self._process_audio_chunk(audio_path) 