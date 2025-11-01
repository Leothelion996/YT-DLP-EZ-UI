"""
URL parsing module for YT-DLP EZ-UI.
Handles parsing, validation, and processing of YouTube URLs.
"""

import logging
from typing import Dict, List, Optional
from utils.validators import URLValidator


class URLParser:
    """
    High-level URL parsing and management.
    Provides business logic layer on top of URLValidator.
    """

    def __init__(self):
        """Initialize the URL parser."""
        self.logger = logging.getLogger(__name__)
        self.validator = URLValidator()

    def parse_single_url(self, url: str) -> Optional[Dict[str, any]]:
        """
        Parse a single URL and extract information.

        Args:
            url: The YouTube URL to parse

        Returns:
            dict or None: URL information if valid, None otherwise
            Dictionary contains:
                - url: Normalized URL
                - video_id: Video ID (if applicable)
                - playlist_id: Playlist ID (if applicable)
                - is_playlist: Boolean indicating if it's a playlist
        """
        try:
            cleaned_url = self.validator.validate_and_clean(url)
            if not cleaned_url:
                self.logger.warning(f"Invalid URL: {url}")
                return None

            is_playlist = self.validator.is_playlist_url(cleaned_url)
            video_id = self.validator.extract_video_id(cleaned_url)
            playlist_id = self.validator.extract_playlist_id(cleaned_url)

            result = {
                'url': cleaned_url,
                'video_id': video_id,
                'playlist_id': playlist_id,
                'is_playlist': is_playlist,
                'original_url': url.strip()
            }

            self.logger.info(f"Successfully parsed URL: {cleaned_url}")
            return result

        except Exception as e:
            self.logger.error(f"Error parsing URL '{url}': {e}")
            return None

    def parse_multiple_urls(self, text: str) -> List[Dict[str, any]]:
        """
        Parse multiple URLs from text input.

        Args:
            text: Text containing one or more URLs

        Returns:
            list: List of parsed URL information dictionaries
        """
        try:
            urls = self.validator.parse_batch_urls(text)
            parsed_urls = []

            for url in urls:
                parsed = self.parse_single_url(url)
                if parsed:
                    parsed_urls.append(parsed)

            self.logger.info(f"Parsed {len(parsed_urls)} valid URLs from batch input")
            return parsed_urls

        except Exception as e:
            self.logger.error(f"Error parsing multiple URLs: {e}")
            return []

    def validate_url(self, url: str) -> tuple[bool, str]:
        """
        Validate a URL and return validation result with message.

        Args:
            url: The URL to validate

        Returns:
            tuple: (is_valid, message)
        """
        if not url or not url.strip():
            return False, "URL cannot be empty"

        if not self.validator.is_valid_url(url):
            return False, "Invalid URL format"

        if not self.validator.is_youtube_url(url):
            return False, "URL is not a valid YouTube link"

        return True, "Valid YouTube URL"

    def get_url_type(self, url: str) -> Optional[str]:
        """
        Determine the type of YouTube URL.

        Args:
            url: The YouTube URL

        Returns:
            str or None: 'playlist', 'video', or None if invalid
        """
        if not self.validator.is_youtube_url(url):
            return None

        if self.validator.is_playlist_url(url):
            return 'playlist'
        else:
            return 'video'
