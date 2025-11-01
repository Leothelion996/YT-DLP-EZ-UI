"""
Unit tests for metadata handler.
"""

import unittest
from unittest.mock import Mock, patch
from core.metadata import MetadataHandler


class TestMetadataHandler(unittest.TestCase):
    """Test cases for MetadataHandler class."""

    def setUp(self):
        """Set up test fixtures."""
        self.handler = MetadataHandler()

    def test_initialization(self):
        """Test metadata handler initialization."""
        self.assertIsNotNone(self.handler)

    def test_year_formatting(self):
        """Test year extraction from upload date."""
        test_cases = [
            ("20231225", "2023"),
            ("20201231", "2020"),
            ("", None),
            (None, None),
        ]

        for upload_date, expected_year in test_cases:
            with self.subTest(upload_date=upload_date):
                result = self.handler._format_year(upload_date)
                self.assertEqual(result, expected_year)

    @patch('yt_dlp.YoutubeDL')
    def test_metadata_extraction_from_url(self, mock_ydl):
        """Test metadata extraction from YouTube URL."""
        # Mock yt-dlp response
        mock_instance = Mock()
        mock_instance.extract_info.return_value = {
            'title': 'Test Video',
            'uploader': 'Test Channel',
            'upload_date': '20231225',
            'duration': 100,
            'description': 'Test description',
        }
        mock_ydl.return_value.__enter__.return_value = mock_instance

        url = "https://www.youtube.com/watch?v=test"
        metadata = self.handler.extract_metadata_from_url(url)

        self.assertIsNotNone(metadata)
        self.assertEqual(metadata['title'], 'Test Video')
        self.assertEqual(metadata['uploader'], 'Test Channel')
        self.assertEqual(metadata['upload_date'], '20231225')


if __name__ == '__main__':
    unittest.main()
