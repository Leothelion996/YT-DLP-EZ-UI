"""
User profile manager for YT-DLP EZ-UI.
Tracks user state, setup completion, and feature configuration.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

from config.constants import CONFIG_DIR


class UserProfile:
    """
    Manages user profile and application state.
    Tracks setup completion, feature enablement, and user preferences.
    """

    PROFILE_FILE = CONFIG_DIR / "user_profile.json"

    DEFAULT_PROFILE = {
        "version": "1.0",
        "created_at": None,
        "last_updated": None,
        "setup_completed": False,
        "features": {
            "beets": {
                "enabled": False,
                "setup_completed": False,
                "acoustid_configured": False,
                "chromaprint_installed": False,
                "first_import_completed": False,
                "library_path": None
            }
        },
        "statistics": {
            "total_downloads": 0,
            "total_imports": 0,
            "last_download": None,
            "last_import": None
        },
        "preferences": {
            "auto_import_after_download": False,
            "show_import_preview": True,
            "delete_originals_after_import": False
        }
    }

    def __init__(self):
        """Initialize the user profile manager."""
        self.logger = logging.getLogger(__name__)
        self.profile = self._load_profile()

    def _load_profile(self) -> Dict[str, Any]:
        """
        Load user profile from disk.

        Returns:
            dict: User profile data
        """
        try:
            if self.PROFILE_FILE.exists():
                with open(self.PROFILE_FILE, 'r', encoding='utf-8') as f:
                    profile = json.load(f)
                    self.logger.info("User profile loaded")
                    return profile
            else:
                self.logger.info("No existing profile found, creating new profile")
                return self._create_new_profile()
        except Exception as e:
            self.logger.error(f"Failed to load user profile: {e}")
            return self._create_new_profile()

    def _create_new_profile(self) -> Dict[str, Any]:
        """
        Create a new user profile with default values.

        Returns:
            dict: New profile data
        """
        profile = self.DEFAULT_PROFILE.copy()
        profile["created_at"] = datetime.now().isoformat()
        profile["last_updated"] = datetime.now().isoformat()
        self._save_profile(profile)
        return profile

    def _save_profile(self, profile: Optional[Dict[str, Any]] = None) -> bool:
        """
        Save user profile to disk.

        Args:
            profile: Profile data to save (uses self.profile if None)

        Returns:
            bool: True if save successful
        """
        try:
            if profile is None:
                profile = self.profile

            # Update timestamp
            profile["last_updated"] = datetime.now().isoformat()

            # Ensure config directory exists
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)

            # Write to file
            with open(self.PROFILE_FILE, 'w', encoding='utf-8') as f:
                json.dump(profile, f, indent=2)

            self.logger.info("User profile saved")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save user profile: {e}")
            return False

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a value from the profile using dot notation.

        Args:
            key_path: Path to value (e.g., "features.beets.enabled")
            default: Default value if key not found

        Returns:
            Value at key_path or default
        """
        keys = key_path.split('.')
        value = self.profile

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path: str, value: Any) -> bool:
        """
        Set a value in the profile using dot notation.

        Args:
            key_path: Path to value (e.g., "features.beets.enabled")
            value: Value to set

        Returns:
            bool: True if successful
        """
        keys = key_path.split('.')
        target = self.profile

        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]

        # Set the value
        target[keys[-1]] = value

        return self._save_profile()

    # Convenience methods for common operations

    def is_setup_completed(self) -> bool:
        """Check if initial setup is completed."""
        return self.get("setup_completed", False)

    def mark_setup_completed(self) -> bool:
        """Mark initial setup as completed."""
        return self.set("setup_completed", True)

    def is_beets_enabled(self) -> bool:
        """Check if Beets feature is enabled."""
        return self.get("features.beets.enabled", False)

    def set_beets_enabled(self, enabled: bool) -> bool:
        """Enable or disable Beets feature."""
        return self.set("features.beets.enabled", enabled)

    def is_beets_setup_completed(self) -> bool:
        """Check if Beets setup is completed."""
        return self.get("features.beets.setup_completed", False)

    def mark_beets_setup_completed(self) -> bool:
        """Mark Beets setup as completed."""
        return self.set("features.beets.setup_completed", True)

    def is_acoustid_configured(self) -> bool:
        """Check if AcoustID API key is configured."""
        return self.get("features.beets.acoustid_configured", False)

    def mark_acoustid_configured(self, configured: bool = True) -> bool:
        """Mark AcoustID as configured."""
        return self.set("features.beets.acoustid_configured", configured)

    def is_chromaprint_installed(self) -> bool:
        """Check if Chromaprint is installed."""
        return self.get("features.beets.chromaprint_installed", False)

    def mark_chromaprint_installed(self, installed: bool = True) -> bool:
        """Mark Chromaprint as installed."""
        return self.set("features.beets.chromaprint_installed", installed)

    def get_beets_library_path(self) -> Optional[str]:
        """Get Beets library path."""
        return self.get("features.beets.library_path")

    def set_beets_library_path(self, path: str) -> bool:
        """Set Beets library path."""
        return self.set("features.beets.library_path", path)

    def increment_downloads(self) -> bool:
        """Increment download counter."""
        count = self.get("statistics.total_downloads", 0)
        self.set("statistics.total_downloads", count + 1)
        return self.set("statistics.last_download", datetime.now().isoformat())

    def increment_imports(self) -> bool:
        """Increment import counter."""
        count = self.get("statistics.total_imports", 0)
        self.set("statistics.total_imports", count + 1)
        return self.set("statistics.last_import", datetime.now().isoformat())

    def reset_profile(self) -> bool:
        """Reset profile to defaults."""
        self.profile = self._create_new_profile()
        return True

    def export_profile(self, file_path: Path) -> bool:
        """
        Export profile to a file.

        Args:
            file_path: Path to export file

        Returns:
            bool: True if successful
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.profile, f, indent=2)
            self.logger.info(f"Profile exported to: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to export profile: {e}")
            return False

    def get_profile_summary(self) -> str:
        """
        Get a human-readable summary of the profile.

        Returns:
            str: Profile summary
        """
        lines = [
            "=== User Profile Summary ===",
            f"Created: {self.get('created_at', 'Unknown')}",
            f"Last Updated: {self.get('last_updated', 'Unknown')}",
            f"Setup Completed: {self.is_setup_completed()}",
            "",
            "Beets Feature:",
            f"  Enabled: {self.is_beets_enabled()}",
            f"  Setup Completed: {self.is_beets_setup_completed()}",
            f"  AcoustID Configured: {self.is_acoustid_configured()}",
            f"  Chromaprint Installed: {self.is_chromaprint_installed()}",
            f"  Library Path: {self.get_beets_library_path() or 'Not set'}",
            "",
            "Statistics:",
            f"  Total Downloads: {self.get('statistics.total_downloads', 0)}",
            f"  Total Imports: {self.get('statistics.total_imports', 0)}",
        ]
        return "\n".join(lines)
