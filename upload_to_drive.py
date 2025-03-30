import os
import sys
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials
from googleapiclient.errors import HttpError
import traceback

def authenticate_google_drive():
    # ... (mantenha esta função como está)

def upload_file(service, file_path, parent_folder_id, mime_type=None):
    """Upload a file to Google Drive."""
    file_name = os.path.basename(file_path)
    
    print(f"Starting upload process for file: {file_name}")
    print(f"File path: {file_path}")
    print(f"Parent folder ID: {parent_folder_id}")
    print(f"MIME type: {mime_type}")

    # Check if file already exists in the folder
    query = f"name='{file_name}' and '{parent_folder_id}' in parents and trashed=false"
    print(f"Checking if file exists with query: {query}")
    results = service.files().list(q=query, fields="files(id, name)").execute()
    existing_files = results.get('files', [])
    
    file_metadata = {
        'name': file_name,
        'parents': [parent_folder_id]
    }
    media  MediaFileUpload(file_path, mimetype=mime_type, resumable=True)

    print(f"Preparing to upload file: {file_name}")
    print(f"File metadata: {file_metadata}")

    try:
        if existing_files:
            # Update existing file
            file_id = existing_files[0]['id']
            print(f"Updating existing file: {file_name}, ID: {file_id}")
            file = service.files().update(
                fileId=file_id,
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            print(f"Updated file: {file_name}, ID: {file.get('id')}")
        else:
            # Upload new file
            print(f"Uploading new file: {file_name}")
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            print(f"Uploaded new file: {file_name}, ID: {file.get('id')}")
        
        print(f"Upload process completed for file: {file_name}")
        return file.get('id')
    except HttpError as error:
        print(f"An error occurred while uploading {file_name}: {error}")
        print(f"Error details: {error.content.decode()}")
        return None

def create_folder(service, folder_name, parent_folder_id):
    # ... (mantenha esta função como está)

def sync_folder_to_drive(service, local_folder_path, parent_folder_id):
    """Recursively sync a local folder to Google Drive."""
    print(f"Starting sync process for folder: {local_folder_path}")
    print(f"Parent folder ID in Google Drive: {parent_folder_id}")

    # Get list of files already in Google Drive folder
    query = f"'{parent_folder_id}' in parents and trashed=false"
    print(f"Fetching existing files in Google Drive with query: {query}")
    results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
    drive_files = {file['name']: file for file in results.get('files', [])}
    print(f"Found {len(drive_files)} files in Google Drive folder")

    # Track local files for deletion check
    local_files = set()

    # Walk through local directory
    for root, dirs, files in os.walk(local_folder_path):
        rel_path = os.path.relpath(root, local_folder_path)
        print(f"Processing directory: {rel_path}")
        current_parent_id = parent_folder_id

        # If we're in a subdirectory, create/get the folder structure
        if rel_path != '.':
            folder_parts = rel_path.split(os.sep)
            for folder in folder_parts:
                print(f"Creating/getting folder: {folder}")
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
            elif file_name.endswith('.bsp'):
                mime_type = 'application/octet-stream'  # Define MIME type for BSP files

            print(f"Processing file: {file_name}")
            upload_file(service, file_path, current_parent_id, mime_type)

    print(f"Sync process completed for folder: {local_folder_path}")

    # Delete files that no longer exist locally
    for drive_file in drive_files.values():
        if drive_file['name'] not in local_files and drive_file['mimeType'] != 'application/vnd.google-apps.folder':
            try:
                service.files().delete(fileId=drive_file['id']).execute()
                print(f"Deleted file from Google Drive: {drive_file['name']}")
            except HttpError as error:
                print(f"Error deleting file {drive_file['name']}: {error}")

def main():
    # ... (mantenha esta função como está)

if __name__ == "__main__":
    main()
