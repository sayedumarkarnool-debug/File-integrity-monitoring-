import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from app.services.scanner import DirectoryScanner

class TestDirectoryScanner:
    """Tests for directory scanning"""

    def test_scan_simple_directory(self):
        """Test scanning a directory with a few files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            (Path(temp_dir) / 'file1.txt').write_text('Content 1')
            (Path(temp_dir) / 'file2.txt').write_text('Content 2')

            # Mock the exclusion loading to avoid database dependency
            scanner = DirectoryScanner()
            scanner._exclusion_patterns = {'file': [], 'directory': [], 'glob': []}

            result = scanner.scan_directory(temp_dir)

            assert result['scan_complete'] is True
            assert result['total_files'] == 2
            assert result['failed_files'] == 0
            assert len(result['files']) == 2
            assert 'file1.txt' in result['files']
            assert 'file2.txt' in result['files']

    def test_scan_with_subdirectories(self):
        """Test recursive directory scanning"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create nested structure
            subdir = Path(temp_dir) / 'subdir'
            subdir.mkdir()

            (Path(temp_dir) / 'root.txt').write_text('Root file')
            (subdir / 'nested.txt').write_text('Nested file')

            scanner = DirectoryScanner()
            scanner._exclusion_patterns = {'file': [], 'directory': [], 'glob': []}

            result = scanner.scan_directory(temp_dir, recursive=True)

            assert result['scan_complete'] is True
            assert result['total_files'] == 2
            assert 'root.txt' in result['files']
            assert str(Path('subdir') / 'nested.txt') in result['files'] or \
                   str(Path('subdir/nested.txt')) in result['files']

    def test_scan_nonexistent_directory(self):
        """Test scanning a directory that doesn't exist"""
        scanner = DirectoryScanner()
        result = scanner.scan_directory('/nonexistent/directory')

        assert result['scan_complete'] is False
        assert result['total_files'] == 0
        assert len(result['errors']) > 0

    def test_scan_empty_directory(self):
        """Test scanning an empty directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            scanner = DirectoryScanner()
            scanner._exclusion_patterns = {'file': [], 'directory': [], 'glob': []}

            result = scanner.scan_directory(temp_dir)

            assert result['scan_complete'] is True
            assert result['total_files'] == 0
            assert len(result['files']) == 0

    def test_file_hashes_calculated(self):
        """Test that file hashes are calculated"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / 'test.txt'
            test_file.write_text('Test content')

            scanner = DirectoryScanner()
            scanner._exclusion_patterns = {'file': [], 'directory': [], 'glob': []}

            result = scanner.scan_directory(temp_dir)

            assert 'test.txt' in result['files']
            file_info = result['files']['test.txt']
            assert file_info['hash'] is not None
            assert len(file_info['hash']) == 64
            assert file_info['size'] > 0
            assert file_info['error'] is None
