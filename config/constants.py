"""
Application constants for YT-DLP EZ-UI.
Defines all constant values used throughout the application.
"""

import os
from pathlib import Path

# Application metadata
APP_NAME = "YT-DLP EZ-UI"
APP_VERSION = "1.0.0"
APP_AUTHOR = "YT-DLP EZ-UI Team"

# File paths
USER_HOME = Path.home()
DOWNLOADS_DIR = USER_HOME / "Downloads"
APPDATA_DIR = Path(os.getenv('APPDATA', USER_HOME / 'AppData' / 'Roaming'))
CONFIG_DIR = APPDATA_DIR / APP_NAME
CONFIG_FILE = CONFIG_DIR / "settings.json"
LOG_FILE = CONFIG_DIR / "app.log"

# Download quality options
VIDEO_RESOLUTIONS = [
    "144p",
    "240p",
    "360p",
    "480p",
    "720p",
    "1080p",
    "1440p",
    "4K",
    "Best Available"
]

AUDIO_BITRATES = [
    "64kbps",
    "128kbps",
    "192kbps",
    "320kbps",
    "Best Available"
]

# File format options
FILE_FORMATS = {
    "Video": "video",
    "Audio Only": "audio"
}

# Default settings
DEFAULT_SETTINGS = {
    "download_directory": str(DOWNLOADS_DIR),
    "file_format": "video",
    "video_quality": "Best Available",
    "audio_quality": "Best Available",
    "last_window_size": [800, 600],
    "last_window_position": None
}

# URL validation patterns
YOUTUBE_DOMAINS = [
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "www.youtu.be"
]

# UI constants
WINDOW_MIN_WIDTH = 700
WINDOW_MIN_HEIGHT = 500
WINDOW_DEFAULT_WIDTH = 800
WINDOW_DEFAULT_HEIGHT = 600

# Threading constants
MAX_CONCURRENT_DOWNLOADS = 3
DOWNLOAD_TIMEOUT = 3600  # 1 hour in seconds

# Logging constants
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5
