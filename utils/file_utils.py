"""
File utilities for YT-DLP EZ-UI.
Handles file operations, path validation, and directory management.
"""

import os
import logging
from pathlib import Path
from typing import Optional


class FileUtils:
    """
    Utility class for file and directory operations.
    Provides safe file handling with proper error checking.
    """

    @staticmethod
    def is_valid_directory(path: str) -> bool:
        """
        Check if a path is a valid directory.

        Args:
            path: Directory path to validate

        Returns:
            bool: True if path is a valid, accessible directory
        """
        try:
            path_obj = Path(path)
            return path_obj.exists() and path_obj.is_dir()
        except Exception:
            return False

    @staticmethod
    def is_writable_directory(path: str) -> bool:
        """
        Check if a directory is writable.

        Args:
            path: Directory path to check

        Returns:
            bool: True if directory is writable
        """
        try:
            path_obj = Path(path)
            if not path_obj.exists():
                return False

            # Try to create a temporary file
            test_file = path_obj / '.write_test'
            try:
                test_file.touch()
                test_file.unlink()
                return True
            except Exception:
                return False
        except Exception:
            return False

    @staticmethod
    def ensure_directory(path: str) -> bool:
        """
        Ensure a directory exists, creating it if necessary.

        Args:
            path: Directory path to ensure

        Returns:
            bool: True if directory exists or was created successfully
        """
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logging.error(f"Failed to create directory '{path}': {e}")
            return False

    @staticmethod
    def get_safe_filename(filename: str) -> str:
        """
        Sanitize a filename by removing/replacing invalid characters.

        Args:
            filename: Original filename

        Returns:
            str: Sanitized filename safe for Windows filesystem
        """
        # Characters that are invalid in Windows filenames
        invalid_chars = '<>:"/\\|?*'

        # Replace invalid characters with underscore
        safe_name = filename
        for char in invalid_chars:
            safe_name = safe_name.replace(char, '_')

        # Remove leading/trailing spaces and dots
        safe_name = safe_name.strip('. ')

        # Ensure filename is not empty
        if not safe_name:
            safe_name = 'download'

        # Truncate if too long (Windows has 255 char limit)
        if len(safe_name) > 200:  # Leave room for extension
            safe_name = safe_name[:200]

        return safe_name

    @staticmethod
    def get_unique_filepath(directory: str, filename: str) -> Path:
        """
        Get a unique filepath by adding numbers if file exists.

        Args:
            directory: Directory path
            filename: Desired filename

        Returns:
            Path: Unique filepath that doesn't exist yet
        """
        base_path = Path(directory) / filename

        if not base_path.exists():
            return base_path

        # Split filename and extension
        stem = base_path.stem
        suffix = base_path.suffix

        # Try adding numbers until we find a unique name
        counter = 1
        while True:
            new_path = base_path.parent / f"{stem}_{counter}{suffix}"
            if not new_path.exists():
                return new_path
            counter += 1

            # Safety check to avoid infinite loop
            if counter > 9999:
                raise ValueError(f"Could not find unique filename for {filename}")

    @staticmethod
    def get_unique_folder_name(parent_dir: str, folder_name: str) -> str:
        """
        Get a unique folder name by adding (1), (2) etc. if folder exists.

        Args:
            parent_dir: Parent directory path
            folder_name: Desired folder name

        Returns:
            str: Unique folder name that doesn't exist yet
        """
        base_path = Path(parent_dir) / folder_name

        if not base_path.exists():
            return folder_name

        # Try adding (1), (2), (3)... until we find a unique name
        counter = 1
        while True:
            new_name = f"{folder_name} ({counter})"
            new_path = Path(parent_dir) / new_name
            if not new_path.exists():
                return new_name
            counter += 1

            # Safety check to avoid infinite loop
            if counter > 9999:
                raise ValueError(f"Could not find unique folder name for {folder_name}")

    @staticmethod
    def get_file_size_mb(filepath: str) -> Optional[float]:
        """
        Get file size in megabytes.

        Args:
            filepath: Path to the file

        Returns:
            float or None: File size in MB, or None if file doesn't exist
        """
        try:
            size_bytes = Path(filepath).stat().st_size
            return size_bytes / (1024 * 1024)
        except Exception:
            return None

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """
        Format file size in human-readable format.

        Args:
            size_bytes: File size in bytes

        Returns:
            str: Formatted file size (e.g., "1.5 MB", "500 KB")
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

    @staticmethod
    def get_available_disk_space(path: str) -> Optional[int]:
        """
        Get available disk space in bytes for the given path.

        Args:
            path: Directory path to check

        Returns:
            int or None: Available space in bytes, or None on error
        """
        try:
            import shutil
            stat = shutil.disk_usage(path)
            return stat.free
        except Exception as e:
            logging.error(f"Failed to get disk space for '{path}': {e}")
            return None
