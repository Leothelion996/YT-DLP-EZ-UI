"""
Settings management module for YT-DLP EZ-UI.
Handles loading, saving, and managing user preferences with JSON persistence.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from .constants import CONFIG_DIR, CONFIG_FILE, DEFAULT_SETTINGS


class SettingsManager:
    """
    Manages application settings with JSON-based persistence.
    Follows the Singleton pattern to ensure single instance across the app.
    """

    _instance: Optional['SettingsManager'] = None

    def __new__(cls) -> 'SettingsManager':
        """Ensure only one instance of SettingsManager exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the settings manager and load existing settings."""
        if not hasattr(self, '_initialized'):
            self.logger = logging.getLogger(__name__)
            self._settings: Dict[str, Any] = {}
            self._ensure_config_directory()
            self.load_settings()
            self._initialized = True

    def _ensure_config_directory(self) -> None:
        """Create the configuration directory if it doesn't exist."""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Configuration directory ensured at: {CONFIG_DIR}")
        except Exception as e:
            self.logger.error(f"Failed to create config directory: {e}")
            raise

    def load_settings(self) -> None:
        """
        Load settings from the JSON configuration file.
        Falls back to default settings if file doesn't exist or is corrupted.
        """
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    self._settings = {**DEFAULT_SETTINGS, **loaded_settings}
                    self.logger.info("Settings loaded successfully")
            else:
                self._settings = DEFAULT_SETTINGS.copy()
                self.save_settings()  # Create the file with defaults
                self.logger.info("Created new settings file with defaults")
        except json.JSONDecodeError as e:
            self.logger.error(f"Corrupted settings file, using defaults: {e}")
            self._settings = DEFAULT_SETTINGS.copy()
            self.save_settings()
        except Exception as e:
            self.logger.error(f"Error loading settings: {e}")
            self._settings = DEFAULT_SETTINGS.copy()

    def save_settings(self) -> bool:
        """
        Save current settings to the JSON configuration file.

        Returns:
            bool: True if save was successful, False otherwise
        """
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=4, ensure_ascii=False)
            self.logger.info("Settings saved successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save settings: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value by key.

        Args:
            key: The setting key to retrieve
            default: Default value if key doesn't exist

        Returns:
            The setting value or default if not found
        """
        return self._settings.get(key, default)

    def set(self, key: str, value: Any, save: bool = True) -> None:
        """
        Set a setting value and optionally save to disk.

        Args:
            key: The setting key to set
            value: The value to store
            save: Whether to immediately save to disk (default: True)
        """
        self._settings[key] = value
        if save:
            self.save_settings()

    def update(self, settings_dict: Dict[str, Any], save: bool = True) -> None:
        """
        Update multiple settings at once.

        Args:
            settings_dict: Dictionary of settings to update
            save: Whether to immediately save to disk (default: True)
        """
        self._settings.update(settings_dict)
        if save:
            self.save_settings()

    def reset_to_defaults(self) -> None:
        """Reset all settings to their default values."""
        self._settings = DEFAULT_SETTINGS.copy()
        self.save_settings()
        self.logger.info("Settings reset to defaults")

    def get_all(self) -> Dict[str, Any]:
        """
        Get all settings as a dictionary.

        Returns:
            Copy of all settings
        """
        return self._settings.copy()

    @property
    def download_directory(self) -> str:
        """Get the current download directory."""
        return self.get("download_directory")

    @download_directory.setter
    def download_directory(self, path: str) -> None:
        """Set the download directory."""
        self.set("download_directory", path)

    @property
    def file_format(self) -> str:
        """Get the current file format preference."""
        return self.get("file_format")

    @file_format.setter
    def file_format(self, format_type: str) -> None:
        """Set the file format preference."""
        self.set("file_format", format_type)

    @property
    def video_quality(self) -> str:
        """Get the current video quality preference."""
        return self.get("video_quality")

    @video_quality.setter
    def video_quality(self, quality: str) -> None:
        """Set the video quality preference."""
        self.set("video_quality", quality)

    @property
    def audio_quality(self) -> str:
        """Get the current audio quality preference."""
        return self.get("audio_quality")

    @audio_quality.setter
    def audio_quality(self, quality: str) -> None:
        """Set the audio quality preference."""
        self.set("audio_quality", quality)
