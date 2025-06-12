import os
import json
from ftplib import FTP
import urllib.parse

class FTPUploader:
    def __init__(self):
        self.settings = self.load_settings()
        self.ftp = None
        self.connect()

    def load_settings(self):
        """Load FTP settings from JSON file"""
        settings_path = os.path.abspath(os.path.join('config', 'ftp_settings.json'))
        with open(settings_path, 'r') as f:
            return json.load(f)

    def connect(self):
        """Connect to FTP server"""
        self.ftp = FTP(self.settings['host'])
        self.ftp.login(
            user=self.settings['username'],
            passwd=self.settings['password']
        )
        if 'path' in self.settings:
             # Create directory if it doesn't exist
            try:
                self.ftp.cwd(self.settings['path'])
            except:
                pass  # Directory might already exist

            # Change to the upload directory
            self.ftp.cwd(self.settings['path'])

    def upload_file(self, file_path):
        """Upload file to FTP server and return URL"""
        file_path = os.path.abspath(file_path)
        filename = os.path.basename(file_path)
        
        with open(file_path, 'rb') as file:
            self.ftp.storbinary(f'STOR {filename}', file)
        
        # Construct URL
        url = f"ftp://{self.settings['host']}"
        if 'path' in self.settings:
            url += f"/{self.settings['path']}"
        url += f"/{filename}"
        
        return url

    def delete_file(self, filename):
        """Delete file from FTP server"""
        try:
            self.ftp.delete(filename)
        except Exception as e:
            print(f"Error deleting file from FTP: {e}")

    def __del__(self):
        """Close FTP connection when object is destroyed"""
        if self.ftp:
            self.ftp.quit() 