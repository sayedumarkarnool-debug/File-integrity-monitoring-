import pytest
import tempfile
import os
from pathlib import Path

from app.services.hasher import FileHasher

class TestFileHasher:
    """Tests for SHA-256 file hashing"""

    def test_calculate_hash_simple_file(self):
        """Test hashing a simple text file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write('Hello, FileGuard!')
            temp_path = f.name

        try:
            hash_value, file_size, error = FileHasher.calculate_sha256(temp_path)

            assert hash_value is not None
            assert len(hash_value) == 64  # SHA-256 produces 64 hex characters
            assert file_size == 17  # "Hello, FileGuard!" is 17 bytes
            assert error is None
        finally:
            os.unlink(temp_path)

    def test_calculate_hash_empty_file(self):
        """Test hashing an empty file"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name

        try:
            hash_value, file_size, error = FileHasher.calculate_sha256(temp_path)

            assert hash_value is not None
            assert file_size == 0
            assert error is None
            # SHA-256 of empty file
            assert hash_value == 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
        finally:
            os.unlink(temp_path)

    def test_hash_nonexistent_file(self):
        """Test hashing a file that doesn't exist"""
        hash_value, file_size, error = FileHasher.calculate_sha256('/nonexistent/path/file.txt')

        assert hash_value is None
        assert file_size is None
        assert error == 'File does not exist'

    def test_hash_consistency(self):
        """Test that same content produces same hash"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write('Test content for consistency')
            temp_path = f.name

        try:
            hash1, _, _ = FileHasher.calculate_sha256(temp_path)
            hash2, _, _ = FileHasher.calculate_sha256(temp_path)

            assert hash1 == hash2
        finally:
            os.unlink(temp_path)

    def test_verify_hash(self):
        """Test hash verification"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write('Verify me')
            temp_path = f.name

        try:
            expected_hash, _, _ = FileHasher.calculate_sha256(temp_path)

            # Verify with correct hash
            assert FileHasher.verify_hash(temp_path, expected_hash) is True

            # Verify with incorrect hash
            assert FileHasher.verify_hash(temp_path, 'wronghash' * 8) is False
        finally:
            os.unlink(temp_path)

    def test_large_file_chunked_reading(self):
        """Test that large files are read in chunks"""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            # Create a file larger than chunk size
            f.write(b'A' * (FileHasher.CHUNK_SIZE * 2 + 1000))
            temp_path = f.name

        try:
            hash_value, file_size, error = FileHasher.calculate_sha256(temp_path)

            assert hash_value is not None
            assert file_size == FileHasher.CHUNK_SIZE * 2 + 1000
            assert error is None
        finally:
            os.unlink(temp_path)

    def test_max_file_size_limit(self):
        """Test that files exceeding max size are rejected"""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            f.write(b'X' * 1000)
            temp_path = f.name

        try:
            # Set max size to 500 bytes
            hash_value, file_size, error = FileHasher.calculate_sha256(temp_path, max_size_bytes=500)

            assert hash_value is None
            assert file_size == 1000
            assert 'too large' in error.lower()
        finally:
            os.unlink(temp_path)
