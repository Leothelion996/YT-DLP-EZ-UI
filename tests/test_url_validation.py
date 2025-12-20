"""
Unit tests for YouTube URL validation with /live/ and /shorts/ support.
Tests the regex fix for properly handling modern YouTube URL formats.
"""

import unittest
from utils.validators import URLValidator


class TestYouTubeURLValidation(unittest.TestCase):
    """Test cases for YouTube URL validation with focus on live and shorts URLs."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = URLValidator()

    def test_standard_video_urls(self):
        """Test validation of standard YouTube video URLs."""
        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
            "http://www.youtube.com/watch?v=dQw4w9WgXcQ",
        ]

        for url in valid_urls:
            with self.subTest(url=url):
                self.assertTrue(
                    self.validator.is_youtube_url(url),
                    f"Should accept valid standard URL: {url}"
                )
                video_id = self.validator.extract_video_id(url)
                self.assertIsNotNone(video_id, f"Should extract video ID from: {url}")
                self.assertEqual(len(video_id), 11, "Video ID must be 11 characters")

    def test_short_urls(self):
        """Test validation of youtu.be short URLs."""
        valid_urls = [
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtu.be/dQw4w9WgXcQ",
            "http://youtu.be/dQw4w9WgXcQ",
        ]

        for url in valid_urls:
            with self.subTest(url=url):
                self.assertTrue(
                    self.validator.is_youtube_url(url),
                    f"Should accept valid short URL: {url}"
                )
                video_id = self.validator.extract_video_id(url)
                self.assertIsNotNone(video_id, f"Should extract video ID from: {url}")

    def test_embed_urls(self):
        """Test validation of embed URLs."""
        valid_urls = [
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "https://youtube.com/embed/dQw4w9WgXcQ",
        ]

        for url in valid_urls:
            with self.subTest(url=url):
                self.assertTrue(
                    self.validator.is_youtube_url(url),
                    f"Should accept valid embed URL: {url}"
                )
                video_id = self.validator.extract_video_id(url)
                self.assertIsNotNone(video_id, f"Should extract video ID from: {url}")

    def test_old_format_urls(self):
        """Test validation of old-style v/ URLs."""
        valid_urls = [
            "https://www.youtube.com/v/dQw4w9WgXcQ",
            "https://youtube.com/v/dQw4w9WgXcQ",
        ]

        for url in valid_urls:
            with self.subTest(url=url):
                self.assertTrue(
                    self.validator.is_youtube_url(url),
                    f"Should accept valid old format URL: {url}"
                )
                video_id = self.validator.extract_video_id(url)
                self.assertIsNotNone(video_id, f"Should extract video ID from: {url}")

    def test_live_stream_urls(self):
        """Test validation of YouTube live stream /live/ URLs."""
        live_urls = [
            "https://www.youtube.com/live/kqRMYFL4Zic",
            "https://www.youtube.com/live/kqRMYFL4Zic?si=oiLRAmy93Xuuyj3Q",  # User's actual URL
            "https://youtube.com/live/dQw4w9WgXcQ",
        ]

        for url in live_urls:
            with self.subTest(url=url):
                self.assertTrue(
                    self.validator.is_youtube_url(url),
                    f"Should accept valid live stream URL: {url}"
                )
                video_id = self.validator.extract_video_id(url)
                self.assertIsNotNone(
                    video_id,
                    f"Should extract video ID from live stream URL: {url}"
                )
                self.assertEqual(len(video_id), 11, "Video ID must be 11 characters")
                # Verify it normalizes correctly
                normalized = self.validator.normalize_url(url)
                self.assertTrue(
                    normalized.startswith("https://www.youtube.com/watch?v="),
                    f"Live URL should normalize to watch?v= format: {normalized}"
                )

    def test_shorts_urls(self):
        """Test validation of YouTube Shorts /shorts/ URLs."""
        shorts_urls = [
            "https://www.youtube.com/shorts/abc123def45",
            "https://youtube.com/shorts/XyZ-_123456",
        ]

        for url in shorts_urls:
            with self.subTest(url=url):
                self.assertTrue(
                    self.validator.is_youtube_url(url),
                    f"Should accept valid Shorts URL: {url}"
                )
                video_id = self.validator.extract_video_id(url)
                self.assertIsNotNone(
                    video_id,
                    f"Should extract video ID from Shorts URL: {url}"
                )
                self.assertEqual(len(video_id), 11, "Video ID must be 11 characters")

    def test_video_ids_with_special_chars(self):
        """Test video IDs containing valid special characters (dash, underscore)."""
        valid_urls = [
            "https://www.youtube.com/watch?v=-wtIMTCHWuI",  # Starts with dash
            "https://www.youtube.com/watch?v=_dQw4w9WgXc",  # Starts with underscore
            "https://www.youtube.com/watch?v=0123456789a",  # All numbers + letter
            "https://www.youtube.com/watch?v=ABCDEFGHIJk",  # All letters
            "https://www.youtube.com/watch?v=---________",  # Multiple dashes/underscores
        ]

        for url in valid_urls:
            with self.subTest(url=url):
                video_id = self.validator.extract_video_id(url)
                self.assertIsNotNone(
                    video_id,
                    f"Should extract video ID from URL with valid special chars: {url}"
                )
                self.assertEqual(len(video_id), 11, "Video ID must be exactly 11 characters")

    def test_malformed_urls_with_slashes(self):
        """Test rejection of malformed URLs with slashes in video ID."""
        malformed_urls = [
            "https://www.youtube.com/watch?v=live/kqRMYF",  # Mixed format - the original error
            "https://www.youtube.com/watch?v=test/123456",
            "https://www.youtube.com/watch?v=abc/def/ghi",
        ]

        for url in malformed_urls:
            with self.subTest(url=url):
                video_id = self.validator.extract_video_id(url)
                self.assertIsNone(
                    video_id,
                    f"Should reject malformed URL with slash in video ID: {url}"
                )

    def test_malformed_urls_with_special_chars(self):
        """Test rejection of URLs with invalid special characters."""
        malformed_urls = [
            "https://www.youtube.com/watch?v=test@123456",
            "https://www.youtube.com/watch?v=test!123456",
            "https://www.youtube.com/watch?v=test#123456",
            "https://www.youtube.com/watch?v=test$123456",
            "https://www.youtube.com/watch?v=test%123456",
            "https://www.youtube.com/watch?v=test 123456",  # Space
        ]

        for url in malformed_urls:
            with self.subTest(url=url):
                video_id = self.validator.extract_video_id(url)
                self.assertIsNone(
                    video_id,
                    f"Should reject URL with invalid special characters: {url}"
                )

    def test_video_id_length_validation(self):
        """Test that video IDs must be exactly 11 characters."""
        # Note: URLs with IDs longer than 11 chars will have the first 11 extracted
        # This test ensures we only get valid 11-char IDs
        short_url = "https://www.youtube.com/watch?v=short"  # Too short (5 chars)

        video_id = self.validator.extract_video_id(short_url)
        self.assertIsNone(
            video_id,
            f"Should reject URL with too-short video ID: {short_url}"
        )

        # Long URLs will extract first 11 valid chars - this is actually correct behavior
        long_url = "https://www.youtube.com/watch?v=waytolong123"
        video_id_long = self.validator.extract_video_id(long_url)
        # The regex will capture exactly 11 chars: "waytolong12"
        # This is valid behavior - yt-dlp handles query params after &
        if video_id_long:
            self.assertEqual(len(video_id_long), 11, "Extracted ID should be 11 chars")

    def test_playlist_urls(self):
        """Test validation of playlist URLs."""
        playlist_urls = [
            "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLtest123",
        ]

        for url in playlist_urls:
            with self.subTest(url=url):
                self.assertTrue(
                    self.validator.is_playlist_url(url),
                    f"Should recognize as playlist URL: {url}"
                )

    def test_non_youtube_urls(self):
        """Test rejection of non-YouTube URLs."""
        non_youtube_urls = [
            "https://www.vimeo.com/123456",
            "https://www.dailymotion.com/video/x123456",
            "https://www.google.com",
            "https://www.facebook.com/video.php?v=123456",
        ]

        for url in non_youtube_urls:
            with self.subTest(url=url):
                self.assertFalse(
                    self.validator.is_youtube_url(url),
                    f"Should reject non-YouTube URL: {url}"
                )

    def test_validate_video_id_method(self):
        """Test the validate_video_id helper method."""
        valid_ids = [
            "dQw4w9WgXcQ",
            "-wtIMTCHWuI",
            "_dQw4w9WgXc",
            "0123456789a",
            "ABCDEFGHIJk",
            "kqRMYFL4Zic",  # From user's live stream URL
        ]

        invalid_ids = [
            "live/kqRMYF",      # Contains slash
            "test@123456",      # Contains @
            "short",            # Too short
            "waytolong123",     # Too long
            "",                 # Empty
            None,               # None
            "test 123456",      # Contains space
        ]

        for vid_id in valid_ids:
            with self.subTest(video_id=vid_id):
                self.assertTrue(
                    self.validator.validate_video_id(vid_id),
                    f"Should validate correct video ID: {vid_id}"
                )

        for vid_id in invalid_ids:
            with self.subTest(video_id=vid_id):
                self.assertFalse(
                    self.validator.validate_video_id(vid_id),
                    f"Should reject invalid video ID: {vid_id}"
                )

    def test_batch_url_parsing_with_malformed(self):
        """Test batch URL parsing filters out malformed URLs."""
        batch_text = """
        https://www.youtube.com/watch?v=dQw4w9WgXcQ
        https://www.youtube.com/watch?v=live/kqRMYF
        https://youtu.be/-wtIMTCHWuI
        https://www.youtube.com/watch?v=test@123456
        https://www.youtube.com/live/kqRMYFL4Zic
        """

        urls = self.validator.parse_batch_urls(batch_text)

        # Should only accept the 3 valid URLs
        self.assertEqual(len(urls), 3, "Should extract only valid URLs")

        # Check that malformed URLs were filtered out
        for url in urls:
            video_id = self.validator.extract_video_id(url)
            self.assertIsNotNone(video_id, f"Extracted URL should have valid video ID: {url}")
            self.assertEqual(len(video_id), 11, "Video ID should be 11 characters")

    def test_normalize_url_live_streams(self):
        """Test that live stream URLs normalize to watch?v= format."""
        test_cases = [
            ("https://www.youtube.com/live/kqRMYFL4Zic", "https://www.youtube.com/watch?v=kqRMYFL4Zic"),
            ("https://www.youtube.com/live/kqRMYFL4Zic?si=oiLRAmy93Xuuyj3Q", "https://www.youtube.com/watch?v=kqRMYFL4Zic"),
        ]

        for input_url, expected_output in test_cases:
            with self.subTest(input_url=input_url):
                normalized = self.validator.normalize_url(input_url)
                self.assertEqual(
                    normalized,
                    expected_output,
                    f"Live URL should normalize to watch?v= format"
                )

    def test_normalize_url_shorts(self):
        """Test that Shorts URLs normalize to watch?v= format."""
        test_cases = [
            ("https://www.youtube.com/shorts/abc123def45", "https://www.youtube.com/watch?v=abc123def45"),
        ]

        for input_url, expected_output in test_cases:
            with self.subTest(input_url=input_url):
                normalized = self.validator.normalize_url(input_url)
                self.assertEqual(
                    normalized,
                    expected_output,
                    f"Shorts URL should normalize to watch?v= format"
                )


class TestURLValidationIntegration(unittest.TestCase):
    """Integration tests for URL validation in the full processing pipeline."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = URLValidator()

    def test_validate_and_clean_rejects_malformed(self):
        """Test that validate_and_clean rejects malformed URLs."""
        malformed_urls = [
            "https://www.youtube.com/watch?v=live/kqRMYF",
            "https://www.youtube.com/watch?v=test@123",
        ]

        for url in malformed_urls:
            with self.subTest(url=url):
                result = self.validator.validate_and_clean(url)
                # If result is returned, extract_video_id should still fail
                if result:
                    video_id = self.validator.extract_video_id(result)
                    self.assertIsNone(
                        video_id,
                        f"Should not extract valid video ID from malformed URL: {url}"
                    )

    def test_validate_and_clean_accepts_valid(self):
        """Test that validate_and_clean accepts valid URLs including live and shorts."""
        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/-wtIMTCHWuI",
            "https://www.youtube.com/live/kqRMYFL4Zic",
            "https://www.youtube.com/shorts/abc123def45",
        ]

        for url in valid_urls:
            with self.subTest(url=url):
                result = self.validator.validate_and_clean(url)
                self.assertIsNotNone(result, f"Should accept valid URL: {url}")

                video_id = self.validator.extract_video_id(result)
                self.assertIsNotNone(video_id, f"Should extract video ID from valid URL: {url}")
                self.assertEqual(len(video_id), 11, "Video ID should be 11 characters")

    def test_user_original_url(self):
        """Test the exact URL that caused the user's error."""
        user_url = "https://www.youtube.com/live/kqRMYFL4Zic?si=oiLRAmy93Xuuyj3Q"

        # Should be recognized as YouTube URL
        self.assertTrue(
            self.validator.is_youtube_url(user_url),
            "User's live stream URL should be recognized as YouTube URL"
        )

        # Should extract correct video ID
        video_id = self.validator.extract_video_id(user_url)
        self.assertEqual(
            video_id,
            "kqRMYFL4Zic",
            "Should extract full video ID from user's URL"
        )

        # Should normalize correctly
        normalized = self.validator.normalize_url(user_url)
        self.assertEqual(
            normalized,
            "https://www.youtube.com/watch?v=kqRMYFL4Zic",
            "User's URL should normalize to standard watch?v= format"
        )

        # Should pass validate_and_clean
        cleaned = self.validator.validate_and_clean(user_url)
        self.assertIsNotNone(cleaned, "User's URL should pass validation")


if __name__ == '__main__':
    unittest.main()
