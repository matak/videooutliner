import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

class DriveUploader:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/drive.file']
        self.creds = None
        self.service = None
        self.initialize_service()

    def initialize_service(self):
        """Initialize Google Drive service"""
        token_path = os.path.join('config', 'token.json')
        credentials_path = os.path.join('config', 'google_drive_credentials.json')
        
        if os.path.exists(token_path):
            self.creds = Credentials.from_authorized_user_info(
                json.loads(open(token_path).read()), self.SCOPES)
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, self.SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            with open(token_path, 'w') as token:
                token.write(self.creds.to_json())

        self.service = build('drive', 'v3', credentials=self.creds)

    def upload_file(self, file_path):
        """Upload file to Google Drive and return file ID and web view link"""
        file_metadata = {'name': os.path.basename(file_path)}
        media = MediaFileUpload(file_path, resumable=True)
        
        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,webViewLink'
        ).execute()
        
        return file.get('id'), file.get('webViewLink')

    def delete_file(self, file_id):
        """Delete file from Google Drive"""
        try:
            self.service.files().delete(fileId=file_id).execute()
        except Exception as e:
            print(f"Error deleting file from Google Drive: {e}") 