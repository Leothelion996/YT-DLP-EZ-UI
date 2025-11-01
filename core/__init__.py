"""
Core functionality package for YT-DLP EZ-UI.
Contains download management, URL parsing, metadata handling, and queue management.
"""

from .downloader import DownloadManager
from .url_parser import URLParser
from .metadata import MetadataHandler
from .queue_manager import QueueManager

__all__ = ['DownloadManager', 'URLParser', 'MetadataHandler', 'QueueManager']
