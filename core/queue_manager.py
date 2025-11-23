"""
Queue manager for YT-DLP EZ-UI.
Manages the download queue with add, remove, and edit operations.
"""

import logging
from typing import List, Optional, Dict
from threading import Lock

from core.url_parser import URLParser


class QueueItem:
    """Represents a single item in the download queue."""

    def __init__(self, url: str, title: str = None, is_playlist: bool = False, is_album: bool = False):
        """
        Initialize a queue item.

        Args:
            url: YouTube URL
            title: Video/playlist title (optional)
            is_playlist: Whether this is a playlist
            is_album: Whether this playlist should be treated as an album
        """
        self.url = url
        self.title = title or url
        self.is_playlist = is_playlist
        self.is_album = is_album
        self.status = "pending"  # pending, downloading, completed, failed

    def to_dict(self) -> Dict:
        """
        Convert queue item to dictionary.

        Returns:
            dict: Queue item data
        """
        return {
            'url': self.url,
            'title': self.title,
            'is_playlist': self.is_playlist,
            'is_album': self.is_album,
            'status': self.status
        }


class QueueManager:
    """
    Manages the download queue.
    Thread-safe queue operations with validation.
    """

    def __init__(self):
        """Initialize the queue manager."""
        self.logger = logging.getLogger(__name__)
        self.url_parser = URLParser()
        self._queue: List[QueueItem] = []
        self._lock = Lock()

    def add_url(self, url: str) -> bool:
        """
        Add a URL to the queue after validation.

        Args:
            url: YouTube URL to add

        Returns:
            bool: True if added successfully
        """
        try:
            # Parse and validate URL
            parsed = self.url_parser.parse_single_url(url)
            if not parsed:
                self.logger.warning(f"Invalid URL not added to queue: {url}")
                return False

            with self._lock:
                # Check for duplicates
                if any(item.url == parsed['url'] for item in self._queue):
                    self.logger.info(f"URL already in queue: {url}")
                    return False

                # Create queue item
                item = QueueItem(
                    url=parsed['url'],
                    title=parsed['url'],  # Will be updated when metadata is fetched
                    is_playlist=parsed['is_playlist']
                )

                self._queue.append(item)
                self.logger.info(f"Added to queue: {parsed['url']}")
                return True

        except Exception as e:
            self.logger.error(f"Error adding URL to queue: {e}")
            return False

    def add_urls(self, urls: List[str]) -> int:
        """
        Add multiple URLs to the queue.

        Args:
            urls: List of YouTube URLs

        Returns:
            int: Number of URLs successfully added
        """
        added_count = 0
        for url in urls:
            if self.add_url(url):
                added_count += 1
        return added_count

    def remove_url(self, url: str) -> bool:
        """
        Remove a URL from the queue.

        Args:
            url: YouTube URL to remove

        Returns:
            bool: True if removed successfully
        """
        try:
            with self._lock:
                original_length = len(self._queue)
                self._queue = [item for item in self._queue if item.url != url]

                if len(self._queue) < original_length:
                    self.logger.info(f"Removed from queue: {url}")
                    return True

                return False

        except Exception as e:
            self.logger.error(f"Error removing URL from queue: {e}")
            return False

    def remove_at_index(self, index: int) -> bool:
        """
        Remove an item at a specific index.

        Args:
            index: Index of item to remove

        Returns:
            bool: True if removed successfully
        """
        try:
            with self._lock:
                if 0 <= index < len(self._queue):
                    removed_item = self._queue.pop(index)
                    self.logger.info(f"Removed from queue at index {index}: {removed_item.url}")
                    return True
                return False

        except Exception as e:
            self.logger.error(f"Error removing item at index {index}: {e}")
            return False

    def update_title(self, url: str, title: str) -> bool:
        """
        Update the title of a queued item.

        Args:
            url: YouTube URL
            title: New title

        Returns:
            bool: True if updated successfully
        """
        try:
            with self._lock:
                for item in self._queue:
                    if item.url == url:
                        item.title = title
                        self.logger.info(f"Updated title for {url}: {title}")
                        return True
                return False

        except Exception as e:
            self.logger.error(f"Error updating title: {e}")
            return False

    def get_all_items(self) -> List[QueueItem]:
        """
        Get all queue items.

        Returns:
            list: Copy of all queue items
        """
        with self._lock:
            return self._queue.copy()

    def get_all_urls(self) -> List[str]:
        """
        Get all URLs in the queue.

        Returns:
            list: List of URLs
        """
        with self._lock:
            return [item.url for item in self._queue]

    def get_item_at_index(self, index: int) -> Optional[QueueItem]:
        """
        Get queue item at specific index.

        Args:
            index: Index of item to get

        Returns:
            QueueItem or None: Queue item if found
        """
        with self._lock:
            if 0 <= index < len(self._queue):
                return self._queue[index]
            return None

    def clear(self) -> None:
        """Clear all items from the queue."""
        with self._lock:
            self._queue.clear()
            self.logger.info("Queue cleared")

    def is_empty(self) -> bool:
        """
        Check if queue is empty.

        Returns:
            bool: True if queue is empty
        """
        with self._lock:
            return len(self._queue) == 0

    def get_count(self) -> int:
        """
        Get the number of items in the queue.

        Returns:
            int: Number of items
        """
        with self._lock:
            return len(self._queue)

    def update_status(self, url: str, status: str) -> bool:
        """
        Update the status of a queued item.

        Args:
            url: YouTube URL
            status: New status ('pending', 'downloading', 'completed', 'failed')

        Returns:
            bool: True if updated successfully
        """
        try:
            with self._lock:
                for item in self._queue:
                    if item.url == url:
                        item.status = status
                        self.logger.info(f"Updated status for {url}: {status}")
                        return True
                return False

        except Exception as e:
            self.logger.error(f"Error updating status: {e}")
            return False

    def set_album_status(self, url: str, is_album: bool) -> bool:
        """
        Set whether a playlist should be treated as an album.

        Args:
            url: YouTube URL
            is_album: Whether to treat as album

        Returns:
            bool: True if updated successfully
        """
        try:
            with self._lock:
                for item in self._queue:
                    if item.url == url:
                        item.is_album = is_album
                        self.logger.info(f"Set album status for {url}: {is_album}")
                        return True
                return False

        except Exception as e:
            self.logger.error(f"Error setting album status: {e}")
            return False

    def get_album_status(self, url: str) -> bool:
        """
        Get whether a playlist is marked as an album.

        Args:
            url: YouTube URL

        Returns:
            bool: True if marked as album, False otherwise
        """
        with self._lock:
            for item in self._queue:
                if item.url == url:
                    return item.is_album
            return False
