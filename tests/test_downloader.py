"""
Unit tests for download manager.
"""

import unittest
from unittest.mock import Mock, patch
from core.downloader import DownloadManager


class TestDownloadManager(unittest.TestCase):
    """Test cases for DownloadManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = DownloadManager()

    def test_initialization(self):
        """Test download manager initialization."""
        self.assertIsNotNone(self.manager)
        self.assertEqual(self.manager.get_active_downloads_count(), 0)

    def test_active_downloads_tracking(self):
        """Test tracking of active downloads."""
        url = "https://www.youtube.com/watch?v=test"

        # Initially not downloading
        self.assertFalse(self.manager.is_downloading(url))

        # Count should be 0
        self.assertEqual(self.manager.get_active_downloads_count(), 0)

    @patch('yt_dlp.YoutubeDL')
    def test_video_info_extraction(self, mock_ydl):
        """Test video info extraction without downloading."""
        # Mock yt-dlp response
        mock_instance = Mock()
        mock_instance.extract_info.return_value = {
            'title': 'Test Video',
            'uploader': 'Test Channel',
            'duration': 100,
        }
        mock_ydl.return_value.__enter__.return_value = mock_instance

        url = "https://www.youtube.com/watch?v=test"
        info = self.manager.get_video_info(url)

        self.assertIsNotNone(info)
        self.assertEqual(info['type'], 'video')
        self.assertEqual(info['title'], 'Test Video')
        self.assertEqual(info['uploader'], 'Test Channel')


if __name__ == '__main__':
    unittest.main()
