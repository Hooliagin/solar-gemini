import os
from supabase import create_client, Client
from config import settings
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Initialize Supabase Admin Client
# We use the Service Role Key to bypass RLS so the backend can manage files for users
_supabase: Client = None

def get_supabase_admin() -> Client:
    global _supabase
    if _supabase is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            logger.warning(f"Supabase credentials missing: URL={'Found' if settings.SUPABASE_URL else 'Missing'}, KEY={'Found' if settings.SUPABASE_SERVICE_ROLE_KEY else 'Missing'}")
            print(f"DEBUG: Supabase Config - URL: {settings.SUPABASE_URL}, KEY (len): {len(settings.SUPABASE_SERVICE_ROLE_KEY) if settings.SUPABASE_SERVICE_ROLE_KEY else 0}", flush=True)
            return None
        _supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    return _supabase

BUCKET_NAME = "audio-briefings"

def upload_file(local_path: str, destination_path: str) -> str:
    """
    Uploads a file to Supabase Storage.
    Returns the storage path (not the full URL).
    """
    client = get_supabase_admin()
    if not client:
        raise Exception("Supabase client not initialized")
    
    try:
        with open(local_path, 'rb') as f:
            # Upsert=True allows replacing if needed (though we usually use unique names)
            response = client.storage.from_(BUCKET_NAME).upload(
                path=destination_path,
                file=f,
                file_options={"content-type": "audio/wav", "upsert": "true"}
            )
            
        logger.info(f"Uploaded {local_path} to {BUCKET_NAME}/{destination_path}")
        return destination_path
        
    except Exception as e:
        logger.error(f"Failed to upload file to Supabase: {e}")
        raise e

def create_signed_url(storage_path: str, expires_in: int = 60) -> str:
    """
    Generates a temporary signed URL for a file.
    expires_in: Seconds until the link expires.
    """
    client = get_supabase_admin()
    if not client:
        raise Exception("Supabase client not initialized")
        
    try:
        response = client.storage.from_(BUCKET_NAME).create_signed_url(
            path=storage_path, 
            expires_in=expires_in
        )
        # response is usually a dict or object with 'signedURL'
        # Adjust based on library version, but typically:
        if isinstance(response, dict) and 'signedURL' in response:
             return response['signedURL']
        elif hasattr(response, 'signedURL'): # Newer client versions sometimes
             return response.signedURL
        
        # Fallback inspection
        logger.info(f"Signed URL response type: {type(response)} - {response}")
        return response # It might be the string directly in some versions?
        
    except Exception as e:
        logger.error(f"Failed to generate signed URL: {e}")
        raise e

def delete_old_files(retention_days: int = 3):
    """
    Deletes files older than retention_days from the bucket.
    Start from the root or iterate folders if structured.
    """
    # NOTE: Listing all files efficiently can be tricky if there are thousands.
    # For now, we will rely on the Database cleanup logic to tell us WHICH paths to delete.
    # This function creates a helper to delete a specific list of paths.
    pass

def delete_file(storage_path: str):
    """Delete a single file from storage."""
    client = get_supabase_admin()
    if not client:
        return

    try:
        client.storage.from_(BUCKET_NAME).remove([storage_path])
        logger.info(f"Deleted file {storage_path} from storage")
    except Exception as e:
        logger.error(f"Failed to delete file {storage_path}: {e}")

def download_file(storage_path: str) -> bytes:
    """Download a file from storage into memory (bytes)."""
    client = get_supabase_admin()
    if not client:
        raise Exception("Supabase client not initialized")
        
    try:
        # returns byte array usually
        response = client.storage.from_(BUCKET_NAME).download(storage_path)
        return response
    except Exception as e:
        logger.error(f"Failed to download file {storage_path}: {e}")
        raise e
