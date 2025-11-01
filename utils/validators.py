"""
Input validation utilities for YT-DLP EZ-UI.
Provides URL validation and parsing functionality.
"""

import re
from typing import List, Optional
from urllib.parse import urlparse, parse_qs
from config.constants import YOUTUBE_DOMAINS


class URLValidator:
    """
    Validates and parses YouTube URLs.
    Supports individual videos, playlists, and various YouTube URL formats.
    """

    # Regex patterns for different YouTube URL formats
    YOUTUBE_REGEX = re.compile(
        r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')

    PLAYLIST_REGEX = re.compile(
        r'[?&]list=([^&]+)'
    )

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """
        Check if a URL is a valid format (basic URL validation).

        Args:
            url: The URL string to validate

        Returns:
            bool: True if URL format is valid
        """
        if not url or not isinstance(url, str):
            return False

        url = url.strip()
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    @staticmethod
    def is_youtube_url(url: str) -> bool:
        """
        Check if a URL is a valid YouTube URL.

        Args:
            url: The URL string to validate

        Returns:
            bool: True if URL is a valid YouTube URL
        """
        if not url or not isinstance(url, str):
            return False

        url = url.strip()

        # Check if it's a valid URL first
        if not URLValidator.is_valid_url(url):
            return False

        # Parse the URL and check domain
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Remove port if present
            domain = domain.split(':')[0]

            # Check if domain is in allowed YouTube domains
            return any(yt_domain in domain for yt_domain in YOUTUBE_DOMAINS)
        except Exception:
            return False

    @staticmethod
    def is_playlist_url(url: str) -> bool:
        """
        Check if a YouTube URL is a playlist.

        Args:
            url: The YouTube URL to check

        Returns:
            bool: True if URL is a playlist
        """
        if not URLValidator.is_youtube_url(url):
            return False

        # Check for playlist parameter
        return bool(URLValidator.PLAYLIST_REGEX.search(url))

    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """
        Extract the video ID from a YouTube URL.

        Args:
            url: The YouTube URL

        Returns:
            str or None: The video ID if found, None otherwise
        """
        if not URLValidator.is_youtube_url(url):
            return None

        match = URLValidator.YOUTUBE_REGEX.search(url)
        if match:
            return match.group(6)
        return None

    @staticmethod
    def extract_playlist_id(url: str) -> Optional[str]:
        """
        Extract the playlist ID from a YouTube URL.

        Args:
            url: The YouTube URL

        Returns:
            str or None: The playlist ID if found, None otherwise
        """
        if not URLValidator.is_playlist_url(url):
            return None

        match = URLValidator.PLAYLIST_REGEX.search(url)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def normalize_url(url: str) -> str:
        """
        Normalize a YouTube URL to a standard format.

        Args:
            url: The YouTube URL to normalize

        Returns:
            str: Normalized URL
        """
        url = url.strip()

        # Extract video ID
        video_id = URLValidator.extract_video_id(url)
        if not video_id:
            return url

        # Check if it's a playlist
        playlist_id = URLValidator.extract_playlist_id(url)

        if playlist_id:
            return f"https://www.youtube.com/playlist?list={playlist_id}"
        else:
            return f"https://www.youtube.com/watch?v={video_id}"

    @staticmethod
    def parse_batch_urls(text: str) -> List[str]:
        """
        Parse multiple URLs from text input.
        Supports CSV, line-by-line, and space-separated formats.

        Args:
            text: Text containing multiple URLs

        Returns:
            List[str]: List of extracted URLs
        """
        if not text or not isinstance(text, str):
            return []

        urls = []

        # First, try to find all URLs using regex
        url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )

        found_urls = url_pattern.findall(text)

        if found_urls:
            # URLs found via regex
            urls.extend(found_urls)
        else:
            # Try splitting by common delimiters
            # Try comma first (CSV)
            if ',' in text:
                urls.extend([u.strip() for u in text.split(',')])
            # Try newlines (line-by-line)
            elif '\n' in text:
                urls.extend([u.strip() for u in text.split('\n')])
            # Try spaces
            elif ' ' in text:
                urls.extend([u.strip() for u in text.split()])
            else:
                # Single URL
                urls.append(text.strip())

        # Filter out empty strings and validate
        urls = [u for u in urls if u and URLValidator.is_youtube_url(u)]

        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in urls:
            normalized = URLValidator.normalize_url(url)
            if normalized not in seen:
                seen.add(normalized)
                unique_urls.append(normalized)

        return unique_urls

    @staticmethod
    def validate_and_clean(url: str) -> Optional[str]:
        """
        Validate and clean a single URL.

        Args:
            url: The URL to validate and clean

        Returns:
            str or None: Cleaned URL if valid, None otherwise
        """
        if not url or not isinstance(url, str):
            return None

        url = url.strip()

        if URLValidator.is_youtube_url(url):
            return URLValidator.normalize_url(url)

        return None
