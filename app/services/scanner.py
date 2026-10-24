import os
from pathlib import Path
from typing import List, Dict, Optional, Set
import fnmatch
from datetime import datetime

from app.services.hasher import FileHasher
from app.models.exclusion import Exclusion
from app.extensions import db

class DirectoryScanner:
    """Service for scanning directories and calculating file hashes"""

    def __init__(self, max_file_size_bytes: Optional[int] = None):
        self.max_file_size_bytes = max_file_size_bytes
        self.hasher = FileHasher()
        self._exclusion_patterns = None

    def _load_exclusions(self) -> Dict[str, List[str]]:
        """Load enabled exclusion patterns from database"""
        if self._exclusion_patterns is not None:
            return self._exclusion_patterns

        patterns = {
            'file': [],
            'directory': [],
            'glob': []
        }
        try:
            exclusions = Exclusion.query.filter_by(is_enabled=True).all()
            for exclusion in exclusions:
                if exclusion.pattern_type in patterns:
                    patterns[exclusion.pattern_type].append(exclusion.pattern)
        except Exception:
            pass

        return patterns

    def _is_excluded(self, path: str, is_directory: bool = False) -> bool:
        """Check if a path should be excluded"""
        patterns = self._load_exclusions()
        path_obj = Path(path)

        # Check directory exclusions
        if is_directory:
            for pattern in patterns['directory']:
                if fnmatch.fnmatch(path_obj.name, pattern) or fnmatch.fnmatch(str(path_obj), pattern):
                    return True

        # Check file exclusions
        for pattern in patterns['file']:
            if fnmatch.fnmatch(path_obj.name, pattern):
                return True

        # Check glob patterns
        for pattern in patterns['glob']:
            if fnmatch.fnmatch(str(path_obj), pattern):
                return True

        return False

    def scan_directory(self, directory_path: str, recursive: bool = True) -> Dict:
        """
        Scan a directory and calculate hashes for all files.

        Args:
            directory_path: Path to directory to scan
            recursive: Whether to scan subdirectories

        Returns:
            Dictionary with:
                - files: Dict of {relative_path: {hash, size, mtime, error}}
                - errors: List of error messages
                - scan_complete: Whether scan completed successfully
                - total_files: Total files processed
                - failed_files: Number of files that failed
        """
        directory_path = os.path.abspath(directory_path)

        if not os.path.exists(directory_path):
            return {
                'files': {},
                'errors': [f"Directory does not exist: {directory_path}"],
                'scan_complete': False,
                'total_files': 0,
                'failed_files': 0
            }

        if not os.path.isdir(directory_path):
            return {
                'files': {},
                'errors': [f"Not a directory: {directory_path}"],
                'scan_complete': False,
                'total_files': 0,
                'failed_files': 0
            }

        files = {}
        errors = []
        total_files = 0
        failed_files = 0
        scan_complete = True

        try:
            # Walk the directory tree
            for root, dirs, filenames in os.walk(directory_path):
                # Filter out excluded directories (modifies dirs in-place to prevent walking into them)
                dirs[:] = [d for d in dirs if not self._is_excluded(os.path.join(root, d), is_directory=True)]

                for filename in filenames:
                    file_path = os.path.join(root, filename)

                    # Skip excluded files
                    if self._is_excluded(file_path, is_directory=False):
                        continue

                    total_files += 1

                    # Calculate relative path
                    try:
                        relative_path = os.path.relpath(file_path, directory_path)
                    except ValueError:
                        # Can happen on Windows with different drives
                        relative_path = file_path

                    # Calculate hash
                    file_hash, file_size, error = self.hasher.calculate_sha256(
                        file_path,
                        self.max_file_size_bytes
                    )

                    if error:
                        failed_files += 1
                        files[relative_path] = {
                            'hash': None,
                            'size': file_size,
                            'mtime': None,
                            'error': error
                        }
                        errors.append(f"{relative_path}: {error}")
                    else:
                        # Get modification time
                        try:
                            mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                        except:
                            mtime = None

                        files[relative_path] = {
                            'hash': file_hash,
                            'size': file_size,
                            'mtime': mtime,
                            'error': None
                        }

                # If not recursive, break after first iteration
                if not recursive:
                    break

        except PermissionError as e:
            scan_complete = False
            errors.append(f"Permission denied accessing directory: {str(e)}")
        except Exception as e:
            scan_complete = False
            errors.append(f"Scan error: {str(e)}")

        return {
            'files': files,
            'errors': errors,
            'scan_complete': scan_complete,
            'total_files': total_files,
            'failed_files': failed_files
        }
