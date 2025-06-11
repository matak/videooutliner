import os
import json
import ftplib
from urllib.parse import urlparse

class FTPUploader:
    def __init__(self):
        if not os.path.exists('ftp_settings.json'):
            raise Exception("ftp_settings.json not found")
        
        with open('ftp_settings.json', 'r') as f:
            settings = json.load(f)
            required_fields = ['host', 'username', 'password', 'path', 'public_url']
            for field in required_fields:
                if field not in settings:
                    raise Exception(f"Missing required field '{field}' in ftp_settings.json")
            
            self.host = settings['host']
            self.username = settings['username']
            self.password = settings['password']
            self.path = settings['path']
            self.public_url = settings['public_url']
    
    def upload_file(self, file_path):
        """Upload a file to FTP server and return its public URL."""
        filename = os.path.basename(file_path)
        
        try:
            # Connect to FTP server
            ftp = ftplib.FTP(self.host)
            ftp.login(self.username, self.password)
            
            # Create directory if it doesn't exist
            try:
                ftp.mkd(self.path)
            except:
                pass  # Directory might already exist
            
            # Change to the upload directory
            ftp.cwd(self.path)
            
            # Upload the file
            with open(file_path, 'rb') as file:
                ftp.storbinary(f'STOR {filename}', file)
            
            # Close the connection
            ftp.quit()
            
            # Return the public URL
            return os.path.join(self.public_url, filename)
            
        except Exception as e:
            raise Exception(f"FTP upload failed: {str(e)}")
    
    def delete_file(self, filename):
        """Delete a file from FTP server."""
        try:
            ftp = ftplib.FTP(self.host)
            ftp.login(self.username, self.password)
            ftp.cwd(self.path)
            ftp.delete(filename)
            ftp.quit()
            return True
        except Exception as e:
            print(f"Error deleting file from FTP: {e}")
            return False 