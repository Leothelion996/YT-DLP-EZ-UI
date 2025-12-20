"""
CSV validator for BatchRipTagger YT (v5.0).
Extracts and validates YouTube links from CSV files.
"""

import csv
import logging
import re
from pathlib import Path
from typing import Tuple, List
from urllib.parse import urlparse

from config.constants import YOUTUBE_DOMAINS


class CSVValidator:
    """
    Validates and extracts YouTube links from CSV files.
    Handles various CSV formats and filters invalid entries.
    """

    def __init__(self):
        """Initialize the CSV validator."""
        self.logger = logging.getLogger(__name__)

        # URL regex pattern
        self.url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )

    def extract_links_from_csv(self, file_path: Path) -> Tuple[List[str], List[str]]:
        """
        Extract YouTube links from a CSV file.

        Args:
            file_path: Path to the CSV file

        Returns:
            Tuple of (valid_links, rejected_items)
        """
        valid_links = []
        rejected_items = []

        if not file_path.exists():
            self.logger.error(f"CSV file not found: {file_path}")
            return ([], [f"File not found: {file_path}"])

        try:
            # Try reading with different delimiters
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Try to detect delimiter
            sniffer = csv.Sniffer()
            try:
                delimiter = sniffer.sniff(content[:1024]).delimiter
            except csv.Error:
                delimiter = ','  # Default to comma

            # Parse CSV
            lines = content.splitlines()
            reader = csv.reader(lines, delimiter=delimiter)

            row_count = 0
            for row in reader:
                row_count += 1

                # Skip empty rows
                if not row or all(cell.strip() == '' for cell in row):
                    continue

                # Process each cell in the row
                for cell in row:
                    cell = cell.strip()

                    # Skip empty cells
                    if not cell:
                        continue

                    # Check if it looks like a header
                    if self._is_likely_header(cell):
                        rejected_items.append(f"Row {row_count}: Skipped header - {cell}")
                        continue

                    # Extract URLs from cell
                    urls = self.url_pattern.findall(cell)

                    if urls:
                        for url in urls:
                            if self._is_youtube_url(url):
                                if url not in valid_links:  # Avoid duplicates
                                    valid_links.append(url)
                                    self.logger.debug(f"Valid YouTube URL found: {url}")
                            else:
                                rejected_items.append(f"Row {row_count}: Non-YouTube URL - {url}")
                    else:
                        # Not a URL
                        rejected_items.append(f"Row {row_count}: Not a URL - {cell[:50]}")

            self.logger.info(f"Extracted {len(valid_links)} valid links from {file_path}")
            self.logger.info(f"Rejected {len(rejected_items)} items")

        except Exception as e:
            self.logger.error(f"Error processing CSV file: {e}")
            rejected_items.append(f"Error reading file: {e}")

        return (valid_links, rejected_items)

    def _is_youtube_url(self, url: str) -> bool:
        """
        Check if URL is a valid YouTube URL.

        Args:
            url: URL to check

        Returns:
            True if valid YouTube URL, False otherwise
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Check if domain matches any YouTube domain
            for yt_domain in YOUTUBE_DOMAINS:
                if domain == yt_domain or domain.endswith(f".{yt_domain}"):
                    return True

            return False
        except Exception as e:
            self.logger.debug(f"Error parsing URL {url}: {e}")
            return False

    def _is_likely_header(self, text: str) -> bool:
        """
        Check if text looks like a CSV header.

        Args:
            text: Text to check

        Returns:
            True if likely a header, False otherwise
        """
        header_keywords = [
            'url', 'link', 'video', 'title', 'name', 'id', 'playlist',
            'channel', 'description', 'date', 'time', 'duration'
        ]

        text_lower = text.lower()

        # Check for common header patterns
        if any(keyword in text_lower for keyword in header_keywords):
            # Make sure it's not actually a URL
            if not text.startswith('http'):
                return True

        return False
