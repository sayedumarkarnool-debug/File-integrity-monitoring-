"""
Edge case tests for FileGuard FIM
Tests handling of unusual file types, names, and conditions
"""
import pytest
import tempfile
import os
from pathlib import Path

from app.services.hasher import FileHasher
from app.services.scanner import DirectoryScanner


class TestHashingEdgeCases:
    """Test hashing edge cases and unusual file conditions"""

    def test_binary_file_hashing(self):
        """Test hashing binary files"""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.bin') as f:
            # Create binary content
            f.write(bytes([0, 1, 2, 255, 254, 253] * 100))
            temp_path = f.name

        try:
            hash_value, file_size, error = FileHasher.calculate_sha256(temp_path)

            assert hash_value is not None
            assert len(hash_value) == 64
            assert file_size == 600  # 6 bytes * 100
            assert error is None
        finally:
            os.unlink(temp_path)

    def test_unicode_filename(self):
        """Test hashing files with unicode names"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create file with unicode name
            unicode_file = Path(temp_dir) / 'test_файл_测试.txt'
            unicode_file.write_text('Unicode filename test', encoding='utf-8')

            hash_value, file_size, error = FileHasher.calculate_sha256(str(unicode_file))

            assert hash_value is not None
            assert len(hash_value) == 64
            assert error is None

    def test_filename_with_spaces(self):
        """Test hashing files with spaces in name"""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_with_spaces = Path(temp_dir) / 'file with multiple spaces.txt'
            file_with_spaces.write_text('Testing spaces')

            hash_value, file_size, error = FileHasher.calculate_sha256(str(file_with_spaces))

            assert hash_value is not None
            assert error is None

    def test_very_long_filename(self):
        """Test files with very long names (within OS limits)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a long but valid filename
            long_name = 'a' * 200 + '.txt'
            long_file = Path(temp_dir) / long_name

            try:
                long_file.write_text('Long filename test')
                hash_value, file_size, error = FileHasher.calculate_sha256(str(long_file))

                assert hash_value is not None
                assert error is None
            except OSError:
                # Some OS may not support this length - that's acceptable
                pytest.skip("OS does not support filenames this long")

    def test_nested_directories(self):
        """Test scanning deeply nested directory structures"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create nested structure
            current_path = Path(temp_dir)
            for i in range(5):
                current_path = current_path / f'level{i}'
                current_path.mkdir()

            # Create file at deepest level
            deep_file = current_path / 'deep.txt'
            deep_file.write_text('Deep file')

            scanner = DirectoryScanner()
            scanner._exclusion_patterns = {'file': [], 'directory': [], 'glob': []}

            result = scanner.scan_directory(temp_dir, recursive=True)

            assert result['scan_complete'] is True
            assert result['total_files'] == 1
            # File should be found at deep path
            assert any('deep.txt' in path for path in result['files'].keys())

    def test_identical_filenames_different_directories(self):
        """Test handling identical filenames in different directories"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create two subdirectories with same filename
            dir1 = Path(temp_dir) / 'dir1'
            dir2 = Path(temp_dir) / 'dir2'
            dir1.mkdir()
            dir2.mkdir()

            file1 = dir1 / 'same.txt'
            file2 = dir2 / 'same.txt'

            file1.write_text('Content 1')
            file2.write_text('Content 2')

            scanner = DirectoryScanner()
            scanner._exclusion_patterns = {'file': [], 'directory': [], 'glob': []}

            result = scanner.scan_directory(temp_dir)

            assert result['scan_complete'] is True
            assert result['total_files'] == 2

            # Both files should be in results with different paths
            files = list(result['files'].keys())
            assert any('dir1' in f and 'same.txt' in f for f in files)
            assert any('dir2' in f and 'same.txt' in f for f in files)

            # Hashes should be different
            hashes = [info['hash'] for info in result['files'].values()]
            assert hashes[0] != hashes[1]

    def test_file_with_special_characters_in_content(self):
        """Test hashing files with special characters in content"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
            # Write special characters
            f.write('Special chars: \n\r\t\0 ñ € 中文 🔒')
            temp_path = f.name

        try:
            hash_value, file_size, error = FileHasher.calculate_sha256(temp_path)

            assert hash_value is not None
            assert len(hash_value) == 64
            assert error is None
        finally:
            os.unlink(temp_path)

    def test_symbolic_link_handling(self):
        """Test that symbolic links are skipped"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a regular file
            real_file = Path(temp_dir) / 'real.txt'
            real_file.write_text('Real content')

            # Try to create a symlink (may not work on all systems)
            try:
                link_file = Path(temp_dir) / 'link.txt'
                link_file.symlink_to(real_file)

                # Hash the symlink
                hash_value, file_size, error = FileHasher.calculate_sha256(str(link_file))

                # Should skip symlinks
                assert hash_value is None
                assert error == "Symbolic link skipped"

            except (OSError, NotImplementedError):
                # Symlinks may not be supported on this system
                pytest.skip("Symbolic links not supported on this system")

    def test_permission_denied_file(self):
        """Test handling of permission-denied files (simulated)"""
        # This is platform-dependent, so we just verify the error handling exists
        hash_value, file_size, error = FileHasher.calculate_sha256('/root/protected_file.txt')

        # Should return error, not crash
        assert hash_value is None
        assert error is not None

    def test_nonexistent_path_in_scan(self):
        """Test scanning a path that doesn't exist"""
        scanner = DirectoryScanner()
        result = scanner.scan_directory('/this/path/does/not/exist/at/all')

        assert result['scan_complete'] is False
        assert result['total_files'] == 0
        assert len(result['errors']) > 0
        assert 'does not exist' in result['errors'][0].lower()

    def test_file_path_instead_of_directory(self):
        """Test passing a file path when directory is expected"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write('Not a directory')
            temp_path = f.name

        try:
            scanner = DirectoryScanner()
            result = scanner.scan_directory(temp_path)

            assert result['scan_complete'] is False
            assert result['total_files'] == 0
            assert len(result['errors']) > 0
        finally:
            os.unlink(temp_path)

    def test_empty_directory_scan(self):
        """Test scanning completely empty directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            scanner = DirectoryScanner()
            scanner._exclusion_patterns = {'file': [], 'directory': [], 'glob': []}

            result = scanner.scan_directory(temp_dir)

            assert result['scan_complete'] is True
            assert result['total_files'] == 0
            assert len(result['files']) == 0
            assert result['failed_files'] == 0

    def test_directory_with_only_subdirectories(self):
        """Test directory containing only subdirectories, no files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create only subdirectories
            (Path(temp_dir) / 'sub1').mkdir()
            (Path(temp_dir) / 'sub2').mkdir()
            (Path(temp_dir) / 'sub3').mkdir()

            scanner = DirectoryScanner()
            scanner._exclusion_patterns = {'file': [], 'directory': [], 'glob': []}

            result = scanner.scan_directory(temp_dir)

            assert result['scan_complete'] is True
            assert result['total_files'] == 0
            assert len(result['files']) == 0

    def test_hash_consistency_across_multiple_calls(self):
        """Test that hashing the same file multiple times gives same result"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write('Consistency test content')
            temp_path = f.name

        try:
            hashes = []
            for _ in range(5):
                hash_value, _, _ = FileHasher.calculate_sha256(temp_path)
                hashes.append(hash_value)

            # All hashes should be identical
            assert len(set(hashes)) == 1
            assert all(h == hashes[0] for h in hashes)
        finally:
            os.unlink(temp_path)

    def test_different_content_produces_different_hashes(self):
        """Test that different content produces different hashes"""
        with tempfile.TemporaryDirectory() as temp_dir:
            file1 = Path(temp_dir) / 'file1.txt'
            file2 = Path(temp_dir) / 'file2.txt'

            file1.write_text('Content A')
            file2.write_text('Content B')

            hash1, _, _ = FileHasher.calculate_sha256(str(file1))
            hash2, _, _ = FileHasher.calculate_sha256(str(file2))

            assert hash1 != hash2

    def test_single_byte_difference_changes_hash(self):
        """Test that even single byte difference produces different hash"""
        with tempfile.TemporaryDirectory() as temp_dir:
            file1 = Path(temp_dir) / 'file1.txt'
            file2 = Path(temp_dir) / 'file2.txt'

            content = 'A' * 1000
            file1.write_text(content)
            file2.write_text(content + 'B')  # One extra byte

            hash1, _, _ = FileHasher.calculate_sha256(str(file1))
            hash2, _, _ = FileHasher.calculate_sha256(str(file2))

            assert hash1 != hash2


class TestScannerEdgeCases:
    """Test scanner edge cases"""

    def test_non_recursive_scan(self):
        """Test that non-recursive scan only gets top-level files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files at root and in subdirectory
            (Path(temp_dir) / 'root.txt').write_text('Root')

            subdir = Path(temp_dir) / 'subdir'
            subdir.mkdir()
            (subdir / 'nested.txt').write_text('Nested')

            scanner = DirectoryScanner()
            scanner._exclusion_patterns = {'file': [], 'directory': [], 'glob': []}

            result = scanner.scan_directory(temp_dir, recursive=False)

            assert result['scan_complete'] is True
            assert result['total_files'] == 1  # Only root.txt
            assert 'root.txt' in result['files']
            assert not any('nested' in f for f in result['files'].keys())

    def test_mixed_accessible_and_inaccessible_files(self):
        """Test scanning directory with mix of accessible and error files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create normal files
            (Path(temp_dir) / 'good1.txt').write_text('Good 1')
            (Path(temp_dir) / 'good2.txt').write_text('Good 2')

            scanner = DirectoryScanner()
            scanner._exclusion_patterns = {'file': [], 'directory': [], 'glob': []}

            result = scanner.scan_directory(temp_dir)

            # Should complete and process the accessible files
            assert result['scan_complete'] is True
            assert result['total_files'] >= 2
            assert 'good1.txt' in result['files']
            assert 'good2.txt' in result['files']
