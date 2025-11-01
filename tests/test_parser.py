"""
Unit tests for URL parser and validator.
"""

import unittest
from utils.validators import URLValidator
from core.url_parser import URLParser


class TestURLValidator(unittest.TestCase):
    """Test cases for URLValidator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = URLValidator()

    def test_valid_youtube_urls(self):
        """Test validation of valid YouTube URLs."""
        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLtest",
        ]

        for url in valid_urls:
            with self.subTest(url=url):
                self.assertTrue(self.validator.is_youtube_url(url))

    def test_invalid_youtube_urls(self):
        """Test rejection of invalid URLs."""
        invalid_urls = [
            "",
            "not a url",
            "https://www.google.com",
            "https://vimeo.com/123456",
            "ftp://youtube.com/video",
        ]

        for url in invalid_urls:
            with self.subTest(url=url):
                self.assertFalse(self.validator.is_youtube_url(url))

    def test_playlist_detection(self):
        """Test playlist URL detection."""
        playlist_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLtest"
        video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        self.assertTrue(self.validator.is_playlist_url(playlist_url))
        self.assertFalse(self.validator.is_playlist_url(video_url))

    def test_video_id_extraction(self):
        """Test video ID extraction."""
        test_cases = [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ]

        for url, expected_id in test_cases:
            with self.subTest(url=url):
                video_id = self.validator.extract_video_id(url)
                self.assertEqual(video_id, expected_id)

    def test_batch_url_parsing(self):
        """Test parsing multiple URLs from text."""
        # Comma-separated
        csv_text = "https://youtu.be/test1, https://youtu.be/test2, https://youtu.be/test3"
        urls = self.validator.parse_batch_urls(csv_text)
        self.assertEqual(len(urls), 3)

        # Line-by-line
        newline_text = "https://youtu.be/test1\nhttps://youtu.be/test2\nhttps://youtu.be/test3"
        urls = self.validator.parse_batch_urls(newline_text)
        self.assertEqual(len(urls), 3)


class TestURLParser(unittest.TestCase):
    """Test cases for URLParser class."""

    def setUp(self):
        """Set up test fixtures."""
        self.parser = URLParser()

    def test_parse_single_video_url(self):
        """Test parsing a single video URL."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        result = self.parser.parse_single_url(url)

        self.assertIsNotNone(result)
        self.assertEqual(result['video_id'], "dQw4w9WgXcQ")
        self.assertFalse(result['is_playlist'])

    def test_parse_playlist_url(self):
        """Test parsing a playlist URL."""
        url = "https://www.youtube.com/playlist?list=PLtest123"
        result = self.parser.parse_single_url(url)

        self.assertIsNotNone(result)
        self.assertTrue(result['is_playlist'])
        self.assertEqual(result['playlist_id'], "PLtest123")


if __name__ == '__main__':
    unittest.main()
