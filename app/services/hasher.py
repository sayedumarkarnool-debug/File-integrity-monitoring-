import hashlib
import os
from pathlib import Path
from typing import Optional, Tuple

class FileHasher:
    """Service for calculating SHA-256 hashes of files"""

    CHUNK_SIZE = 65536  # 64KB chunks

    @staticmethod
    def calculate_sha256(file_path: str, max_size_bytes: Optional[int] = None) -> Tuple[Optional[str], Optional[int], Optional[str]]:
        """
        Calculate SHA-256 hash of a file.

        Args:
            file_path: Path to the file
            max_size_bytes: Maximum file size to process (None for no limit)

        Returns:
            Tuple of (hash, file_size, error_message)
            Returns (None, None, error) if calculation fails
        """
        try:
            file_path_obj = Path(file_path)

            # Check if file exists
            if not file_path_obj.exists():
                return None, None, "File does not exist"

            # Check if it's a file (not directory or symlink)
            if not file_path_obj.is_file():
                return None, None, "Not a regular file"

            # Check if we should follow symlinks (we don't by default)
            if file_path_obj.is_symlink():
                return None, None, "Symbolic link skipped"

            # Get file size
            file_size = file_path_obj.stat().st_size

            # Check max size limit
            if max_size_bytes and file_size > max_size_bytes:
                return None, file_size, f"File too large ({file_size} bytes)"

            # Calculate hash in chunks to handle large files
            sha256_hash = hashlib.sha256()

            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(FileHasher.CHUNK_SIZE)
                    if not chunk:
                        break
                    sha256_hash.update(chunk)

            return sha256_hash.hexdigest(), file_size, None

        except PermissionError:
            return None, None, "Permission denied"
        except OSError as e:
            return None, None, f"OS error: {str(e)}"
        except Exception as e:
            return None, None, f"Unexpected error: {str(e)}"

    @staticmethod
    def verify_hash(file_path: str, expected_hash: str, max_size_bytes: Optional[int] = None) -> bool:
        """
        Verify if a file's hash matches the expected hash.

        Args:
            file_path: Path to the file
            expected_hash: Expected SHA-256 hash
            max_size_bytes: Maximum file size to process

        Returns:
            True if hash matches, False otherwise
        """
        actual_hash, _, error = FileHasher.calculate_sha256(file_path, max_size_bytes)

        if error or not actual_hash:
            return False

        return actual_hash.lower() == expected_hash.lower()
