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
        # Comma-separated with valid 11-char IDs
        csv_text = "https://youtu.be/dQw4w9WgXcQ, https://youtu.be/-wtIMTCHWuI, https://youtu.be/_dQw4w9WgXc"
        urls = self.validator.parse_batch_urls(csv_text)
        self.assertEqual(len(urls), 3)

        # Line-by-line with valid 11-char IDs
        newline_text = "https://youtu.be/dQw4w9WgXcQ\nhttps://youtu.be/-wtIMTCHWuI\nhttps://youtu.be/_dQw4w9WgXc"
        urls = self.validator.parse_batch_urls(newline_text)
        self.assertEqual(len(urls), 3)

    def test_live_stream_urls(self):
        """Test validation and extraction from /live/ URLs."""
        live_urls = [
            "https://www.youtube.com/live/kqRMYFL4Zic",
            "https://www.youtube.com/live/kqRMYFL4Zic?si=oiLRAmy93Xuuyj3Q",
        ]

        for url in live_urls:
            with self.subTest(url=url):
                self.assertTrue(self.validator.is_youtube_url(url))
                video_id = self.validator.extract_video_id(url)
                self.assertEqual(video_id, "kqRMYFL4Zic")

    def test_shorts_urls(self):
        """Test validation and extraction from /shorts/ URLs."""
        shorts_urls = [
            "https://www.youtube.com/shorts/abc123def45",
            "https://youtube.com/shorts/XyZ-_123456",
        ]

        for url in shorts_urls:
            with self.subTest(url=url):
                self.assertTrue(self.validator.is_youtube_url(url))
                video_id = self.validator.extract_video_id(url)
                self.assertIsNotNone(video_id)
                self.assertEqual(len(video_id), 11)

    def test_malformed_video_ids(self):
        """Test rejection of malformed video IDs."""
        malformed_urls = [
            "https://www.youtube.com/watch?v=live/kqRMYF",
            "https://www.youtube.com/watch?v=test@123456",
            "https://www.youtube.com/watch?v=test/123456",
        ]

        for url in malformed_urls:
            with self.subTest(url=url):
                # URL might pass is_youtube_url (domain check)
                # but extract_video_id should return None
                video_id = self.validator.extract_video_id(url)
                self.assertIsNone(
                    video_id,
                    f"Should reject malformed video ID in: {url}"
                )

    def test_video_id_validation(self):
        """Test the validate_video_id helper method."""
        # Valid IDs
        self.assertTrue(self.validator.validate_video_id("dQw4w9WgXcQ"))
        self.assertTrue(self.validator.validate_video_id("-wtIMTCHWuI"))
        self.assertTrue(self.validator.validate_video_id("_dQw4w9WgXc"))
        self.assertTrue(self.validator.validate_video_id("kqRMYFL4Zic"))

        # Invalid IDs
        self.assertFalse(self.validator.validate_video_id("live/kqRMYF"))
        self.assertFalse(self.validator.validate_video_id("test@123456"))
        self.assertFalse(self.validator.validate_video_id("short"))
        self.assertFalse(self.validator.validate_video_id("waytolong123"))


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
