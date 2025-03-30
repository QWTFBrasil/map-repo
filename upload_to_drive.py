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
    """Authenticate with Google Drive API using service account credentials."""
    try:
        # Try different ways to get credentials, since GitHub Actions environment can vary
        creds = None
        creds_file = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        creds_json = os.environ.get('GOOGLE_DRIVE_CREDENTIALS')
        
        print("Authenticating with Google Drive...")
        
        # Define API scopes
        SCOPES = [
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/drive.file'
        ]
        
        if creds_file and os.path.exists(creds_file):
            print(f"Using credentials file from environment")
            creds = service_account.Credentials.from_service_account_file(
                creds_file, 
                scopes=SCOPES
            )
        elif creds_json:
            print("Using credentials from environment variable")
            import json
            creds_info = json.loads(creds_json)
            creds = service_account.Credentials.from_service_account_info(
                creds_info,
                scopes=SCOPES
            )
        else:
            # Try to use default credentials provided by google-github-actions/auth
            print("Using default credentials from GitHub Actions")
            creds = service_account.Credentials.from_service_account_info(
                info=None,
                scopes=SCOPES
            )
        
        if not creds:
            raise ValueError("Failed to obtain credentials through any method")
        
        service = build('drive', 'v3', credentials=creds)
        
        # Test the connection
        about = service.about().get(fields="user").execute()
        print(f"Authentication successful!")
        
        return service
    except Exception as e:
        print(f"Error in authentication: {str(e)}")
        traceback.print_exc()
        return None
        
        
def upload_file(service, file_path, parent_folder_id, mime_type=None):
    file_name = os.path.basename(file_path)
    print(f"Processing file: {file_name}")
    
    try:
        # Check if file exists locally
        if not os.path.exists(file_path):
            print(f"Error: Local file {file_path} does not exist")
            return None
        
        # Check if file already exists in Drive folder
        query = f"name='{file_name}' and '{parent_folder_id}' in parents and trashed=false"
        results = service.files().list(q=query, fields="files(id, name, modifiedTime)").execute()
        existing_files = results.get('files', [])
        
        if existing_files:
            existing_file = existing_files[0]
            print(f"File already exists in Drive: {file_name} (ID: {existing_file.get('id')})")
            return existing_file.get('id')  # Skip upload and return existing ID
    
        file_metadata = {
            'name': file_name,
            'parents': [parent_folder_id]
        }
        
        media = MediaFileUpload(file_path, resumable=True)
        
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        file_id = uploaded_file.get('id')
        print(f"File uploaded successfully: {file_name} (ID: {file_id})")
        return file_id
        
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
        return folder_id
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
        print(f"Created folder: {folder_name}")
        return folder_id

def sync_folder_to_drive(service, local_folder_path, parent_folder_id):
    """Recursively sync a local folder to Google Drive."""
    print(f"Starting sync of folder {local_folder_path} to Drive folder ID: {parent_folder_id}")
    
    # Verify parent folder ID exists
    try:
        folder_info = service.files().get(fileId=parent_folder_id, fields="name,id").execute()
        print(f"Target Drive folder: {folder_info.get('name')} (ID: {folder_info.get('id')})")
        
        # Test if we can create a file in this folder to verify permissions
        print("Testing write permissions...")
        test_metadata = {
            'name': '_test_permissions.txt',
            'parents': [parent_folder_id],
            'mimeType': 'text/plain'
        }
        
        try:
            # Create a test file
            test_file = service.files().create(
                body=test_metadata,
                fields='id'
            ).execute()
            
            # Delete the test file
            service.files().delete(fileId=test_file.get('id')).execute()
            print("Write permissions confirmed")
        except Exception as perm_err:
            print(f"WARNING: Could not write to target folder. Permission issue: {str(perm_err)}")
            return
            
    except Exception as e:
        print(f"ERROR: Target Drive folder ID {parent_folder_id} is not accessible or doesn't exist")
        print(f"Exception: {str(e)}")
        return
    
    # Get list of files already in Google Drive folder
    try:
        query = f"'{parent_folder_id}' in parents and trashed=false"
        results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
        drive_files = {file['name']: file for file in results.get('files', [])}
        print(f"Found {len(drive_files)} existing files in Drive folder")
    except Exception as e:
        print(f"Error listing Drive folder contents: {str(e)}")
        drive_files = {}
    
    # Track local files for deletion check
    local_files = set()
    
    # Check if the local folder exists
    if not os.path.exists(local_folder_path):
        print(f"ERROR: Local folder {local_folder_path} does not exist")
        return
    
    # Walk through local directory
    file_count = 0
    upload_count = 0
    skip_count = 0
    error_count = 0
    
    for root, dirs, files in os.walk(local_folder_path):
        # Calculate relative path from the base folder
        rel_path = os.path.relpath(root, local_folder_path)
        current_parent_id = parent_folder_id
        
        # If we're in a subdirectory, create/get the folder structure
        if rel_path != '.':
            folder_parts = rel_path.split(os.sep)
            for folder in folder_parts:
                try:
                    current_parent_id = create_folder(service, folder, current_parent_id)
                except Exception as e:
                    print(f"Error creating/finding folder '{folder}': {str(e)}")
                    # Continue with parent_folder_id as fallback
                    current_parent_id = parent_folder_id
        
        # Upload files in current directory
        for file_name in files:
            file_count += 1
            file_path = os.path.join(root, file_name)
            
            # Add to tracking set
            local_files.add(os.path.join(rel_path, file_name) if rel_path != '.' else file_name)
            
            # Determine file mime type based on extension
            mime_type = None
            if file_name.endswith('.html'):
                mime_type = 'text/html'
            elif file_name.endswith('.txt'):
                mime_type = 'text/plain'
            elif file_name.endswith('.bsp'):
                mime_type = 'application/octet-stream'
            
            # Attempt upload
            try:
                # Check if file exists in Drive (from earlier query)
                if file_name in drive_files:
                    print(f"Skipping existing file: {file_name}")
                    skip_count += 1
                    continue
                
                result = upload_file(service, file_path, current_parent_id, mime_type)
                if result:
                    upload_count += 1
                else:
                    error_count += 1
            except Exception as e:
                print(f"Exception during upload of {file_name}: {str(e)}")
                error_count += 1
    
    print(f"\nSync summary:")
    print(f"- Total files processed: {file_count}")
    print(f"- Files uploaded: {upload_count}")
    print(f"- Files skipped (already exist): {skip_count}")
    print(f"- Errors: {error_count}")
    
    # Don't attempt to delete files if we had errors uploading
    if error_count > 0:
        print("Skipping file deletion due to upload errors")
        return
        
    # Delete files that no longer exist locally
    delete_count = 0
    for drive_file in drive_files.values():
        if drive_file['name'] not in local_files and drive_file['mimeType'] != 'application/vnd.google-apps.folder':
            try:
                service.files().delete(fileId=drive_file['id']).execute()
                print(f"Deleted file: {drive_file['name']}")
                delete_count += 1
            except HttpError as error:
                print(f"Error deleting file {drive_file['name']}: {error}")
    
    print(f"- Files deleted: {delete_count}")
    print("Sync completed successfully")

def main():
    """Main function to sync a local folder to Google Drive."""
    folder_path = os.environ.get('FOLDER_PATH')
    drive_folder_id = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
    
    # Print config info
    print("==== Google Drive Sync Tool ====")
    print(f"Local folder: {folder_path}")
    print(f"Drive folder ID: {drive_folder_id}")
    print("===============================")
    
    # Basic validation
    if not folder_path:
        print("ERROR: FOLDER_PATH environment variable is not set")
        sys.exit(1)
    
    if not drive_folder_id:
        print("ERROR: GOOGLE_DRIVE_FOLDER_ID is not set")
        sys.exit(1)
    
    # Validate folder ID format
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', drive_folder_id):
        print(f"ERROR: Invalid Google Drive folder ID format: {drive_folder_id}")
        print("Folder IDs should only contain letters, numbers, hyphens, and underscores")
        sys.exit(1)
        
    if not os.path.exists(folder_path):
        print(f"ERROR: Folder path does not exist: {folder_path}")
        sys.exit(1)
    
    try:
        # Authenticate with Google Drive
        service = authenticate_google_drive()
        if not service:
            print("ERROR: Failed to authenticate with Google Drive")
            sys.exit(1)
        
        # Check if files exist to upload
        file_count = 0
        for _, _, files in os.walk(folder_path):
            file_count += len(files)
            
        if file_count == 0:
            print(f"WARNING: No files found in {folder_path}")
            sys.exit(0)
        else:
            print(f"Found {file_count} files to process")
        
        # Run the sync
        sync_folder_to_drive(service, folder_path, drive_folder_id)
    except Exception as e:
        print(f"ERROR during sync process: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
