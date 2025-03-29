import os
import sys
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials
from googleapiclient.errors import HttpError
import traceback
from google.oauth2 import service_account
from googleapiclient.discovery import build

def authenticate_google_drive():
    try:
        creds_file = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if not creds_file:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable is not set")
        
        print(f"Attempting to load credentials from: {creds_file}")
        creds = service_account.Credentials.from_service_account_file(
            creds_file, 
            scopes=['https://www.googleapis.com/auth/drive']
        )
        
        print("Credentials loaded successfully")
        service = build('drive', 'v3', credentials=creds)
        return service
    except Exception as e:
        print(f"Error in authenticate_google_drive: {str(e)}")
        traceback.print_exc()
        return None
        
        
def upload_file(service, file_path, parent_folder_id, mime_type=None):
    """Upload a file to Google Drive."""
    file_name = os.path.basename(file_path)
    
    # Check if file already exists in the folder
    query = f"name='{file_name}' and '{parent_folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    existing_files = results.get('files', [])
    
    file_metadata = {
        'name': file_name,
        'parents': [parent_folder_id]
    }
    
    media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
    
    if existing_files:
        # Update existing file
        file_id = existing_files[0]['id']
        file = service.files().update(
            fileId=file_id,
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        print(f"Updated file: {file_name}, ID: {file.get('id')}")
    else:
        # Upload new file
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        print(f"Uploaded new file: {file_name}, ID: {file.get('id')}")
    
    return file.get('id')

def create_folder(service, folder_name, parent_folder_id):
    """Create a folder in Google Drive, or get existing folder ID."""
    # Check if folder already exists
    query = f"name='{folder_name}' and '{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    folders = results.get('files', [])
    
    if folders:
        # Folder exists, return its ID
        folder_id = folders[0]['id']
        print(f"Found existing folder: {folder_name}, ID: {folder_id}")
    else:
        # Create folder
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id]
        }
        folder = service.files().create(
            body=folder_metadata,
            fields='id'
        ).execute()
        folder_id = folder.get('id')
        print(f"Created new folder: {folder_name}, ID: {folder_id}")
    
    return folder_id

def sync_folder_to_drive(service, local_folder_path, parent_folder_id):
    """Recursively sync a local folder to Google Drive."""
    # Get list of files already in Google Drive folder
    query = f"'{parent_folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
    drive_files = {file['name']: file for file in results.get('files', [])}
    
    # Track local files for deletion check
    local_files = set()
    
    # Walk through local directory
    for root, dirs, files in os.walk(local_folder_path):
        # Calculate relative path from the base folder
        rel_path = os.path.relpath(root, local_folder_path)
        current_parent_id = parent_folder_id
        
        # If we're in a subdirectory, create/get the folder structure
        if rel_path != '.':
            folder_parts = rel_path.split(os.sep)
            for folder in folder_parts:
                current_parent_id = create_folder(service, folder, current_parent_id)
        
        # Upload files in current directory
        for file_name in files:
            local_files.add(os.path.join(rel_path, file_name) if rel_path != '.' else file_name)
            file_path = os.path.join(root, file_name)
            
            # Determine file mime type based on extension
            mime_type = None
            if file_name.endswith('.html'):
                mime_type = 'text/html'
            elif file_name.endswith('.txt'):
                mime_type = 'text/plain'
            # Add more mime types as needed
            
            upload_file(service, file_path, current_parent_id, mime_type)
    
    # Delete files that no longer exist locally
    for drive_file in drive_files.values():
        if drive_file['name'] not in local_files and drive_file['mimeType'] != 'application/vnd.google-apps.folder':
            try:
                service.files().delete(fileId=drive_file['id']).execute()
                print(f"Deleted file: {drive_file['name']}")
            except HttpError as error:
                print(f"Error deleting file {drive_file['name']}: {error}")

def main():
    try:
        print("Starting main function")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Contents of current directory: {os.listdir('.')}")
        
        service = authenticate_google_drive()
        if service is None:
            raise ValueError("Failed to authenticate with Google Drive")
        
        folder_path = os.environ.get('FOLDER_PATH')
        drive_folder_id = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
        
        print(f"Folder path: {folder_path}")
        print(f"Drive folder ID: {drive_folder_id}")
        
        if not folder_path or not drive_folder_id:
            raise ValueError("FOLDER_PATH or GOOGLE_DRIVE_FOLDER_ID environment variables are not set")
        
        # Your sync_folder_to_drive function call here
        # sync_folder_to_drive(service, folder_path, drive_folder_id)
        
        print("Sync completed successfully!")
    except Exception as e:
        print(f"Error during sync: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
    
