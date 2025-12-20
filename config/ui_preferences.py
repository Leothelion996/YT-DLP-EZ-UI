"""
UI preferences manager for BatchRipTagger YT (v5.0).
Manages user-configurable UI preferences separate from core settings.
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from config.constants import APPDATA_DIR, APP_NAME


class UIPreferencesManager:
    """
    Manages UI preferences with JSON persistence.
    Singleton pattern for application-wide access.
    """

    _instance = None

    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the UI preferences manager."""
        if self._initialized:
            return

        self.logger = logging.getLogger(__name__)
        self.preferences_dir = APPDATA_DIR / APP_NAME
        self.preferences_file = self.preferences_dir / "ui_preferences.json"

        # Default preferences
        self._defaults = {
            # Download preferences
            "default_file_format": "audio",
            "default_video_quality": "Best Available",
            "default_audio_quality": "Best Available",
            "default_album_checkbox": True,  # Show album checkbox by default
            "default_beets_enabled": False,
            "remember_output_directory": True,

            # Metadata processor preferences
            "show_file_extensions": True,
            "auto_refresh_on_folder_change": True,

            # UI preferences
            "current_view": "downloader",  # Last active view
            "show_advanced_options": False,
        }

        self._preferences = {}
        self._load_preferences()
        self._initialized = True

        self.logger.info("UI Preferences Manager initialized")

    def _load_preferences(self):
        """Load preferences from JSON file."""
        if self.preferences_file.exists():
            try:
                with open(self.preferences_file, 'r', encoding='utf-8') as f:
                    loaded_prefs = json.load(f)
                    # Merge with defaults (in case new preferences were added)
                    self._preferences = {**self._defaults, **loaded_prefs}
                self.logger.info(f"Loaded UI preferences from {self.preferences_file}")
            except Exception as e:
                self.logger.error(f"Failed to load UI preferences: {e}")
                self._preferences = self._defaults.copy()
        else:
            self._preferences = self._defaults.copy()
            self.logger.info("Using default UI preferences")

    def _save_preferences(self):
        """Save preferences to JSON file."""
        try:
            self.preferences_dir.mkdir(parents=True, exist_ok=True)
            with open(self.preferences_file, 'w', encoding='utf-8') as f:
                json.dump(self._preferences, f, indent=2)
            self.logger.debug("UI preferences saved")
        except Exception as e:
            self.logger.error(f"Failed to save UI preferences: {e}")

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """
        Get a preference value.

        Args:
            key: Preference key
            default: Default value if key not found

        Returns:
            Preference value or default
        """
        return self._preferences.get(key, default if default is not None else self._defaults.get(key))

    def set(self, key: str, value: Any, save: bool = True):
        """
        Set a preference value.

        Args:
            key: Preference key
            value: Preference value
            save: Whether to save immediately (default: True)
        """
        self._preferences[key] = value
        if save:
            self._save_preferences()

    def get_all(self) -> dict:
        """
        Get all preferences.

        Returns:
            Dictionary of all preferences
        """
        return self._preferences.copy()

    def reset_to_defaults(self):
        """Reset all preferences to default values."""
        self._preferences = self._defaults.copy()
        self._save_preferences()
        self.logger.info("UI preferences reset to defaults")

    def reset_key(self, key: str):
        """
        Reset a single preference key to its default value.

        Args:
            key: Preference key to reset
        """
        if key in self._defaults:
            self._preferences[key] = self._defaults[key]
            self._save_preferences()
            self.logger.debug(f"Reset preference '{key}' to default")
