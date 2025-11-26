"""
Supabase client service for database and storage operations.

This service provides a wrapper around the Supabase Python client for:
- Database operations (via PostgreSQL)
- File storage operations (PDF uploads/downloads)
- Signed URL generation for secure file access
"""

from supabase import create_client, Client
from app.core.config import settings
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SupabaseService:
    """Supabase client wrapper for database and storage operations."""
    
    def __init__(self):
        """Initialize Supabase service (client created on initialize())."""
        self.client: Optional[Client] = None
    
    async def initialize(self):
        """
        Initialize Supabase client with service role key.
        
        Uses service role key for admin operations (bypass RLS policies).
        For user-specific operations, use anon key with JWT.
        
        Raises:
            Exception: If initialization fails
        """
        try:
            self.client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY
            )
            logger.info("✓ Supabase client initialized")
            
            # Test connection
            await self._test_connection()
            
        except Exception as e:
            logger.error(f"✗ Failed to initialize Supabase: {e}")
            raise
    
    async def _test_connection(self):
        """Test Supabase connection by querying system tables."""
        try:
            # Simple query to verify connection
            result = self.client.table("users").select("count").execute()
            logger.debug("Supabase connection test passed")
        except Exception as e:
            logger.warning(f"Supabase connection test failed: {e}")
            # Don't fail initialization, just log warning
    
    async def close(self):
        """
        Cleanup Supabase client.
        
        Note: Supabase Python client doesn't require explicit cleanup,
        but keeping this method for consistency with other services.
        """
        logger.info("Supabase client closed")
        self.client = None
    
    def get_client(self) -> Client:
        """
        Get Supabase client instance.
        
        Returns:
            Supabase client
        
        Raises:
            RuntimeError: If client not initialized
        """
        if not self.client:
            raise RuntimeError("Supabase client not initialized. Call initialize() first.")
        return self.client
    
    # ==================== Storage Operations ====================
    
    async def upload_file(
        self, 
        user_id: str, 
        filename: str, 
        file_data: bytes,
        content_type: str = "application/pdf"
    ) -> str:
        """
        Upload file to Supabase Storage.
        
        Files are organized by user_id in folder structure:
        documents/user_id/filename
        
        Args:
            user_id: User ID for folder organization
            filename: Original filename
            file_data: File bytes
            content_type: MIME type (default: application/pdf)
        
        Returns:
            Storage path of uploaded file (e.g., "user_id/filename")
        
        Raises:
            Exception: If upload fails
        """
        try:
            # Create path: user_id/filename
            storage_path = f"{user_id}/{filename}"
            
            # Upload to Supabase Storage
            result = self.client.storage.from_(settings.STORAGE_BUCKET_NAME).upload(
                path=storage_path,
                file=file_data,
                file_options={"content-type": content_type}
            )
            
            logger.info(f"✓ File uploaded to Supabase Storage: {storage_path}")
            return storage_path
        
        except Exception as e:
            logger.error(f"✗ Failed to upload file to Supabase Storage: {e}")
            raise
    
    async def download_file(self, storage_path: str) -> bytes:
        """
        Download file from Supabase Storage.
        
        Args:
            storage_path: Path in storage (e.g., "user_id/filename")
        
        Returns:
            File bytes
        
        Raises:
            Exception: If download fails
        """
        try:
            result = self.client.storage.from_(settings.STORAGE_BUCKET_NAME).download(
                storage_path
            )
            logger.debug(f"File downloaded from Supabase Storage: {storage_path}")
            return result
        
        except Exception as e:
            logger.error(f"✗ Failed to download file from Supabase Storage: {e}")
            raise
    
    async def delete_file(self, storage_path: str):
        """
        Delete file from Supabase Storage.
        
        Args:
            storage_path: Path in storage (e.g., "user_id/filename")
        
        Raises:
            Exception: If deletion fails
        """
        try:
            self.client.storage.from_(settings.STORAGE_BUCKET_NAME).remove([storage_path])
            logger.info(f"✓ File deleted from Supabase Storage: {storage_path}")
        
        except Exception as e:
            logger.error(f"✗ Failed to delete file from Supabase Storage: {e}")
            raise
    
    async def get_signed_url(self, storage_path: str, expires_in: int = 3600) -> str:
        """
        Generate signed URL for secure file download.
        
        Signed URLs are temporary and expire after specified duration.
        Use this for secure file access without exposing storage credentials.
        
        Args:
            storage_path: Path in storage (e.g., "user_id/filename")
            expires_in: URL expiration in seconds (default 1 hour)
        
        Returns:
            Signed URL for file download
        
        Raises:
            Exception: If URL generation fails
        """
        try:
            result = self.client.storage.from_(settings.STORAGE_BUCKET_NAME).create_signed_url(
                storage_path,
                expires_in
            )
            
            signed_url = result["signedURL"]
            logger.debug(f"Generated signed URL for: {storage_path}")
            return signed_url
        
        except Exception as e:
            logger.error(f"✗ Failed to generate signed URL: {e}")
            raise
    
    async def get_public_url(self, storage_path: str) -> str:
        """
        Get public URL for file (if bucket is public).
        
        Note: Our 'documents' bucket is private, so this will only work
        if you change the bucket to public. Use get_signed_url() instead.
        
        Args:
            storage_path: Path in storage
        
        Returns:
            Public URL
        """
        try:
            result = self.client.storage.from_(settings.STORAGE_BUCKET_NAME).get_public_url(
                storage_path
            )
            return result
        
        except Exception as e:
            logger.error(f"✗ Failed to get public URL: {e}")
            raise
    
    async def list_files(self, folder_path: str = "") -> list:
        """
        List files in a folder.
        
        Args:
            folder_path: Folder path (e.g., "user_id/") or empty for root
        
        Returns:
            List of file objects
        
        Raises:
            Exception: If listing fails
        """
        try:
            result = self.client.storage.from_(settings.STORAGE_BUCKET_NAME).list(
                folder_path
            )
            return result
        
        except Exception as e:
            logger.error(f"✗ Failed to list files: {e}")
            raise
    
    # ==================== Database Helpers ====================
    
    def table(self, table_name: str):
        """
        Get table accessor for database operations.
        
        Example:
            result = service.table("documents").select("*").execute()
        
        Args:
            table_name: Name of the table
        
        Returns:
            Table accessor
        """
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
        return self.client.table(table_name)
