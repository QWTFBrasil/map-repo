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
            scopes=['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/drive.file']
        )
        
        print("Credentials loaded successfully")
        service = build('drive', 'v3', credentials=creds)
        return service
    except Exception as e:
        print(f"Error in authenticate_google_drive: {str(e)}")
        traceback.print_exc()
        return None
        
        
def upload_file(service, file_path, parent_folder_id, mime_type=None):
    file_path="action.yml"
    file_name = os.path.basename(file_path)
    print(f"Starting upload process for file: {file_name}")
    
    try:
    
        file_metadata = {
            'name': os.path.basename(file_path),
            'parents': [parent_folder_id]
        }
        media = MediaFileUpload(file_path, resumable=True)
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        print(f"File uploaded with ID: {uploaded_file['id']}")
        
        
        
        return file.get('id')
        
    except Exception as e:
        print(f"Error uploading {file_name}: {str(e)}")
        if isinstance(e, HttpError):
            print(f"HTTP Error details: {e.content.decode()}")
        else:
            traceback.print_exc()
        return None
        
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
    print("Starting sync")
    # Track local files for deletion check
    local_files = set()
    
    # Walk through local directory
    count2 = 0
    for root, dirs, files in os.walk(local_folder_path):
        print(count2)
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
            print(f"File: {file_name}")
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

def list_files_to_upload(folder_path):
    print(f"Listing files in folder: {folder_path}")
    file_count = 0
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.bsp'):
                file_path = os.path.join(root, file)
                #print(f"File to be uploaded: {file_path}")
                file_count += 1
    print(f"Total files to be uploaded: {file_count}")

def main():
    """Main function to sync a local folder to Google Drive."""
    folder_path = os.environ.get('FOLDER_PATH')
    drive_folder_id = "13tnISDHDOI3ElTClWym_u4mbHhDpxqPF"
    
    if not folder_path or not drive_folder_id:
        print("Missing required environment variables: FOLDER_PATH or GOOGLE_DRIVE_FOLDER_ID")
        sys.exit(1)
    
    try:
        # Print debug info
        print("Environment variables available:")
        print(f"FOLDER_PATH: {folder_path}")
        print(f"GOOGLE_DRIVE_FOLDER_ID: {'Set' if drive_folder_id else 'Not set'}")
        print(f"GOOGLE_APPLICATION_CREDENTIALS: {'Set' if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS') else 'Not set'}")
        print(f"GOOGLE_DRIVE_CREDENTIALS: {'Set' if os.environ.get('GOOGLE_DRIVE_CREDENTIALS') else 'Not set'}")
        
        service = authenticate_google_drive()
        print(f"Authentication successful! Syncing folder {folder_path} to Google Drive folder ID: 13tnISDHDOI3ElTClWym_u4mbHhDpxqPF")
        list_files_to_upload(folder_path)
        sync_folder_to_drive(service, folder_path, "13tnISDHDOI3ElTClWym_u4mbHhDpxqPF")
        print("Sync completed successfully!")        
        print("Listing completed successfully!")
    except Exception as e:
        print(f"Error during listing: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
