"""
Upload file handling for Aquilia Request.

Provides:
- UploadFile: Async file upload abstraction
- FormData: Combined form fields and file uploads
- UploadStore protocol and LocalUploadStore implementation
"""

from __future__ import annotations

import os
import tempfile
import uuid
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    AsyncIterator, Dict, List, Mapping, Optional, 
    Protocol, Union, Any
)

try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False

from ._datastructures import MultiDict


# ============================================================================
# UploadFile
# ============================================================================

@dataclass
class UploadFile:
    """
    Uploaded file representation.
    
    Supports streaming and in-memory storage based on size.
    """
    
    filename: str
    content_type: str
    size: Optional[int] = None
    _content: Optional[bytes] = None
    _file_path: Optional[Path] = None
    _chunk_size: int = 64 * 1024
    
    async def read(self, size: int = -1) -> bytes:
        """
        Read file content.
        
        Args:
            size: Number of bytes to read (-1 for all)
        
        Returns:
            File content as bytes
        """
        if self._content is not None:
            # In-memory file
            if size == -1:
                return self._content
            else:
                return self._content[:size]
        
        elif self._file_path is not None:
            # File on disk
            if AIOFILES_AVAILABLE:
                async with aiofiles.open(self._file_path, "rb") as f:
                    if size == -1:
                        return await f.read()
                    else:
                        return await f.read(size)
            else:
                # Fallback to sync I/O
                with open(self._file_path, "rb") as f:
                    if size == -1:
                        return f.read()
                    else:
                        return f.read(size)
        
        return b""
    
    async def stream(self, chunk_size: Optional[int] = None) -> AsyncIterator[bytes]:
        """
        Stream file content in chunks.
        
        Args:
            chunk_size: Size of each chunk
        
        Yields:
            File chunks
        """
        chunk_size = chunk_size or self._chunk_size
        
        if self._content is not None:
            # In-memory file - yield in chunks
            for i in range(0, len(self._content), chunk_size):
                yield self._content[i:i + chunk_size]
        
        elif self._file_path is not None:
            # File on disk - stream
            if AIOFILES_AVAILABLE:
                async with aiofiles.open(self._file_path, "rb") as f:
                    while True:
                        chunk = await f.read(chunk_size)
                        if not chunk:
                            break
                        yield chunk
            else:
                # Fallback to sync I/O
                with open(self._file_path, "rb") as f:
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        yield chunk
    
    async def save(self, path: Union[str, Path], overwrite: bool = False) -> Path:
        """
        Save uploaded file to disk.
        
        Args:
            path: Destination path
            overwrite: Whether to overwrite existing file
        
        Returns:
            Path to saved file
        
        Raises:
            FileExistsError: If file exists and overwrite=False
        """
        dest = Path(path)
        
        if dest.exists() and not overwrite:
            raise FileExistsError(f"File already exists: {dest}")
        
        # Create parent directory if needed
        dest.parent.mkdir(parents=True, exist_ok=True)
        
        if self._content is not None:
            # Write in-memory content
            if AIOFILES_AVAILABLE:
                async with aiofiles.open(dest, "wb") as f:
                    await f.write(self._content)
            else:
                with open(dest, "wb") as f:
                    f.write(self._content)
        
        elif self._file_path is not None:
            # Copy temp file to destination
            if AIOFILES_AVAILABLE:
                async with aiofiles.open(self._file_path, "rb") as src:
                    async with aiofiles.open(dest, "wb") as dst:
                        while True:
                            chunk = await src.read(self._chunk_size)
                            if not chunk:
                                break
                            await dst.write(chunk)
            else:
                import shutil
                shutil.copy2(self._file_path, dest)
        
        return dest
    
    async def close(self) -> None:
        """Clean up temporary file if exists."""
        if self._file_path and self._file_path.exists():
            try:
                os.unlink(self._file_path)
            except OSError:
                pass
    
    def __del__(self):
        """Cleanup on garbage collection."""
        # Note: __del__ is called synchronously, so we can't await
        # This is best-effort cleanup only
        if self._file_path and self._file_path.exists():
            try:
                os.unlink(self._file_path)
            except OSError:
                pass


# ============================================================================
# FormData
# ============================================================================

@dataclass
class FormData:
    """
    Parsed form data containing both fields and files.
    
    Used for application/x-www-form-urlencoded and multipart/form-data.
    """
    
    fields: MultiDict = field(default_factory=MultiDict)
    files: Dict[str, List[UploadFile]] = field(default_factory=dict)
    
    def get(self, name: str, default: Optional[Any] = None) -> Optional[Any]:
        """
        Get field or file by name.
        
        Returns field value if present, otherwise first file.
        """
        # Try field first
        field_value = self.fields.get(name)
        if field_value is not None:
            return field_value
        
        # Try file
        files = self.files.get(name, [])
        if files:
            return files[0]
        
        return default
    
    def get_field(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get form field value."""
        return self.fields.get(name, default)
    
    def get_all_fields(self, name: str) -> List[str]:
        """Get all values for a form field."""
        return self.fields.get_all(name)
    
    def get_file(self, name: str) -> Optional[UploadFile]:
        """Get first uploaded file by name."""
        files = self.files.get(name, [])
        return files[0] if files else None
    
    def get_all_files(self, name: str) -> List[UploadFile]:
        """Get all uploaded files by name."""
        return self.files.get(name, [])
    
    async def cleanup(self) -> None:
        """Clean up all temporary upload files."""
        for file_list in self.files.values():
            for upload_file in file_list:
                await upload_file.close()


# ============================================================================
# UploadStore Protocol
# ============================================================================

class UploadStore(Protocol):
    """
    Protocol for upload storage backends.
    
    Implementations can store uploads to disk, S3, etc.
    """
    
    async def write_chunk(self, upload_id: str, chunk: bytes) -> None:
        """
        Write a chunk of uploaded data.
        
        Args:
            upload_id: Unique upload identifier
            chunk: Data chunk
        """
        ...
    
    async def finalize(self, upload_id: str, metadata: Optional[Dict[str, Any]] = None) -> Path:
        """
        Finalize upload and return final path/identifier.
        
        Args:
            upload_id: Unique upload identifier
            metadata: Optional metadata (filename, content_type, etc.)
        
        Returns:
            Final path or identifier
        """
        ...
    
    async def abort(self, upload_id: str) -> None:
        """
        Abort upload and clean up partial data.
        
        Args:
            upload_id: Unique upload identifier
        """
        ...


# ============================================================================
# LocalUploadStore
# ============================================================================

class LocalUploadStore:
    """
    Local filesystem upload store.
    
    Stores uploads in a configured directory with secure naming.
    """
    
    def __init__(
        self,
        upload_dir: Optional[Union[str, Path]] = None,
        use_hash_prefix: bool = True,
        temp_dir: Optional[Union[str, Path]] = None,
    ):
        """
        Initialize local upload store.
        
        Args:
            upload_dir: Directory for finalized uploads
            use_hash_prefix: Whether to prefix filenames with hash
            temp_dir: Directory for temporary in-progress uploads
        """
        self.upload_dir = Path(upload_dir) if upload_dir else Path.cwd() / "uploads"
        self.temp_dir = Path(temp_dir) if temp_dir else Path(tempfile.gettempdir()) / "aquilia_uploads"
        self.use_hash_prefix = use_hash_prefix
        
        # Create directories
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Track in-progress uploads
        self._uploads: Dict[str, Path] = {}
    
    async def write_chunk(self, upload_id: str, chunk: bytes) -> None:
        """Write chunk to temporary file."""
        if upload_id not in self._uploads:
            # Create temp file for this upload
            temp_path = self.temp_dir / f"{upload_id}.part"
            self._uploads[upload_id] = temp_path
        
        temp_path = self._uploads[upload_id]
        
        if AIOFILES_AVAILABLE:
            async with aiofiles.open(temp_path, "ab") as f:
                await f.write(chunk)
        else:
            with open(temp_path, "ab") as f:
                f.write(chunk)
    
    async def finalize(self, upload_id: str, metadata: Optional[Dict[str, Any]] = None) -> Path:
        """
        Finalize upload and move to final location.
        
        Args:
            upload_id: Upload identifier
            metadata: Optional metadata dict with 'filename', 'content_type', etc.
        
        Returns:
            Final file path
        """
        if upload_id not in self._uploads:
            raise ValueError(f"Unknown upload ID: {upload_id}")
        
        temp_path = self._uploads[upload_id]
        
        # Get filename from metadata or use upload_id
        if metadata and "filename" in metadata:
            filename = self._sanitize_filename(metadata["filename"])
        else:
            filename = f"{upload_id}.bin"
        
        # Add hash prefix if enabled
        if self.use_hash_prefix:
            file_hash = hashlib.sha256(upload_id.encode()).hexdigest()[:8]
            filename = f"{file_hash}_{filename}"
        
        # Final path
        final_path = self.upload_dir / filename
        
        # Atomic move
        temp_path.rename(final_path)
        
        # Clean up tracking
        del self._uploads[upload_id]
        
        return final_path
    
    async def abort(self, upload_id: str) -> None:
        """Abort upload and remove temp file."""
        if upload_id in self._uploads:
            temp_path = self._uploads[upload_id]
            if temp_path.exists():
                temp_path.unlink()
            del self._uploads[upload_id]
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for safe storage.
        
        Removes path separators, null bytes, and other dangerous characters.
        """
        # Remove path components
        filename = os.path.basename(filename)
        
        # Remove null bytes
        filename = filename.replace("\x00", "")
        
        # Remove/replace dangerous characters
        unsafe_chars = ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]
        for char in unsafe_chars:
            filename = filename.replace(char, "_")
        
        # Limit length
        name, ext = os.path.splitext(filename)
        if len(name) > 200:
            name = name[:200]
        
        filename = name + ext
        
        # Ensure not empty
        if not filename or filename == ".":
            filename = "unnamed"
        
        return filename


# ============================================================================
# Utility Functions
# ============================================================================

def create_upload_file_from_bytes(
    filename: str,
    content: bytes,
    content_type: str = "application/octet-stream",
) -> UploadFile:
    """
    Create an UploadFile from bytes (in-memory).
    
    Args:
        filename: Original filename
        content: File content
        content_type: MIME type
    
    Returns:
        UploadFile instance
    """
    return UploadFile(
        filename=filename,
        content_type=content_type,
        size=len(content),
        _content=content,
    )


def create_upload_file_from_path(
    filename: str,
    file_path: Path,
    content_type: str = "application/octet-stream",
) -> UploadFile:
    """
    Create an UploadFile from a disk path.
    
    Args:
        filename: Original filename
        file_path: Path to file on disk
        content_type: MIME type
    
    Returns:
        UploadFile instance
    """
    size = file_path.stat().st_size if file_path.exists() else None
    
    return UploadFile(
        filename=filename,
        content_type=content_type,
        size=size,
        _file_path=file_path,
    )
