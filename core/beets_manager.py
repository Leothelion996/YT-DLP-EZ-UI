"""
Beets manager module for YT-DLP EZ-UI.
Handles music fingerprinting, tagging, and library organization using Beets.
"""

import logging
import os
import sys
import shutil
import yaml
import subprocess
from pathlib import Path
from typing import Dict, Optional, Callable, Any
from threading import Thread, Lock, Event

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

# Check if beets CLI is available
def _check_beets_cli():
    """Check if beets command-line tool is available."""
    try:
        result = subprocess.run(
            ["beet", "version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

BEETS_AVAILABLE = _check_beets_cli()

from config.constants import (
    BEETS_CONFIG_DIR,
    BEETS_CONFIG_FILE,
    BEETS_LIBRARY_DB
)
from utils.file_utils import FileUtils
from utils.chromaprint_installer import ChromaprintInstaller


class BeetsManager:
    """
    Manages music tagging and organization using Beets.
    Handles AcoustID fingerprinting, MusicBrainz lookup, and library management.
    """

    # Keyring identifiers for secure storage
    KEYRING_SERVICE = "YT-DLP_EZ-UI_Beets"
    KEYRING_USERNAME_ACOUSTID = "acoustid"

    def __init__(self):
        """Initialize the Beets manager."""
        self.logger = logging.getLogger(__name__)
        self._active_imports: Dict[str, bool] = {}
        self._lock = Lock()
        self._cancel_event = Event()  # Thread-safe cancellation flag

        # Check dependencies
        if not BEETS_AVAILABLE:
            self.logger.warning("Beets library not installed. Music tagging unavailable.")
        if not KEYRING_AVAILABLE:
            self.logger.warning("keyring library not installed. API key storage may be insecure.")

        # Ensure beets config directory exists
        self._ensure_config_directory()

    def _ensure_config_directory(self) -> None:
        """Create the beets configuration directory if it doesn't exist."""
        try:
            BEETS_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Beets config directory ensured at: {BEETS_CONFIG_DIR}")
        except Exception as e:
            self.logger.error(f"Failed to create beets config directory: {e}")
            raise

    def is_available(self) -> bool:
        """
        Check if Beets functionality is available.

        Returns:
            bool: True if beets is installed and configured
        """
        return BEETS_AVAILABLE

    def is_acoustid_configured(self) -> bool:
        """
        Check if AcoustID API key is configured.

        Returns:
            bool: True if API key is stored in keyring
        """
        if not KEYRING_AVAILABLE:
            return False

        try:
            api_key = keyring.get_password(self.KEYRING_SERVICE, self.KEYRING_USERNAME_ACOUSTID)
            return bool(api_key and api_key.strip())
        except Exception as e:
            self.logger.error(f"Error checking AcoustID configuration: {e}")
            return False

    def get_acoustid_key(self) -> Optional[str]:
        """
        Retrieve AcoustID API key from OS keyring.

        Returns:
            str or None: API key if found, None otherwise
        """
        if not KEYRING_AVAILABLE:
            self.logger.error("keyring library not available")
            return None

        try:
            api_key = keyring.get_password(self.KEYRING_SERVICE, self.KEYRING_USERNAME_ACOUSTID)
            if api_key:
                self.logger.info("AcoustID API key retrieved from keyring")
                return api_key
            else:
                self.logger.warning("No AcoustID API key found in keyring")
                return None
        except Exception as e:
            self.logger.error(f"Failed to retrieve API key from keyring: {e}")
            return None

    def set_acoustid_key(self, api_key: str) -> bool:
        """
        Store AcoustID API key in OS keyring.

        Args:
            api_key: The AcoustID API key to store

        Returns:
            bool: True if successful, False otherwise
        """
        if not KEYRING_AVAILABLE:
            self.logger.error("keyring library not available")
            return False

        if not api_key or not api_key.strip():
            self.logger.error("Invalid API key provided")
            return False

        try:
            keyring.set_password(self.KEYRING_SERVICE, self.KEYRING_USERNAME_ACOUSTID, api_key.strip())
            self.logger.info("AcoustID API key stored securely in keyring")
            return True
        except Exception as e:
            self.logger.error(f"Failed to store API key in keyring: {e}")
            return False

    def delete_acoustid_key(self) -> bool:
        """
        Remove AcoustID API key from OS keyring.

        Returns:
            bool: True if successful, False otherwise
        """
        if not KEYRING_AVAILABLE:
            return False

        try:
            keyring.delete_password(self.KEYRING_SERVICE, self.KEYRING_USERNAME_ACOUSTID)
            self.logger.info("AcoustID API key removed from keyring")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete API key from keyring: {e}")
            return False

    def validate_key(self, api_key: str) -> bool:
        """
        Validate AcoustID API key format.
        Basic validation only - actual validity checked on first use.

        Args:
            api_key: The API key to validate

        Returns:
            bool: True if key format appears valid
        """
        if not api_key or not isinstance(api_key, str):
            return False

        # AcoustID keys are typically 8 characters (alphanumeric)
        api_key = api_key.strip()
        if len(api_key) < 6:
            return False

        # Must be alphanumeric
        if not api_key.replace('-', '').isalnum():
            return False

        return True

    def _create_beets_config(self, library_path: str) -> Path:
        """
        Create customized beets configuration file from template.
        Injects AcoustID API key from keyring at runtime.

        Args:
            library_path: Path to music library directory

        Returns:
            Path: Path to created config file
        """
        try:
            # Get project root (3 levels up from this file)
            project_root = Path(__file__).parent.parent
            template_path = project_root / "beets_config" / "config_template.yaml"
            plugin_path = project_root / "beets_plugins"

            # Read template
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()

            # Ensure library path exists
            library_path_obj = Path(library_path)
            library_path_obj.mkdir(parents=True, exist_ok=True)

            # Ensure import log directory exists
            import_log_path = BEETS_CONFIG_DIR / "import.log"

            # Get AcoustID API key from keyring
            api_key = self.get_acoustid_key()
            if not api_key:
                raise ValueError("AcoustID API key not found in keyring")

            # Replace placeholders
            config_content = template_content.replace(
                'LIBRARY_PATH_PLACEHOLDER', str(library_path_obj)
            ).replace(
                'LIBRARY_DB_PLACEHOLDER', str(BEETS_LIBRARY_DB)
            ).replace(
                'IMPORT_LOG_PLACEHOLDER', str(import_log_path)
            ).replace(
                'PLUGIN_PATH_PLACEHOLDER', str(plugin_path)
            ).replace(
                'ACOUSTID_KEY_PLACEHOLDER', api_key
            )

            # Write customized config
            with open(BEETS_CONFIG_FILE, 'w', encoding='utf-8') as f:
                f.write(config_content)

            self.logger.info(f"Beets config created at: {BEETS_CONFIG_FILE}")
            return BEETS_CONFIG_FILE

        except Exception as e:
            self.logger.error(f"Failed to create beets config: {e}")
            raise

    def run_beets_import(
        self,
        source_path: str,
        library_path: str,
        dry_run: bool = False,
        progress_callback: Optional[Callable[[str], None]] = None,
        completion_callback: Optional[Callable[[bool, Optional[str]], None]] = None
    ) -> bool:
        """
        Run beets import process on audio files.

        Args:
            source_path: Path to directory containing audio files
            library_path: Path to organized music library
            dry_run: If True, preview changes without applying
            progress_callback: Callback for progress updates (receives status message)
            completion_callback: Callback on completion (receives success bool and error message)

        Returns:
            bool: True if import started successfully, False otherwise
        """
        if not BEETS_AVAILABLE:
            error_msg = "Beets library not installed"
            self.logger.error(error_msg)
            if completion_callback:
                completion_callback(False, error_msg)
            return False

        if not self.is_acoustid_configured():
            error_msg = "AcoustID API key not configured"
            self.logger.warning(error_msg)
            if completion_callback:
                completion_callback(False, error_msg)
            return False

        # Validate source path
        source_path_obj = Path(source_path)
        if not source_path_obj.exists() or not source_path_obj.is_dir():
            error_msg = f"Invalid source path: {source_path}"
            self.logger.error(error_msg)
            if completion_callback:
                completion_callback(False, error_msg)
            return False

        try:
            # Create/update beets config
            config_file = self._create_beets_config(library_path)

            # Start import in background thread
            thread = Thread(
                target=self._import_worker,
                args=(source_path, config_file, dry_run, progress_callback, completion_callback),
                daemon=True
            )
            thread.start()

            self.logger.info(f"Beets import started for: {source_path}")
            return True

        except Exception as e:
            error_msg = f"Failed to start beets import: {e}"
            self.logger.error(error_msg)
            if completion_callback:
                completion_callback(False, error_msg)
            return False

    def run_beets_import_async(
        self,
        source_path: str,
        library_path: str,
        dry_run: bool = False,
        progress_callback: Optional[Callable[[str], None]] = None,
        completion_callback: Optional[Callable[[bool, Optional[str]], None]] = None
    ) -> bool:
        """
        Async wrapper for run_beets_import (already async, kept for consistency).

        Args:
            source_path: Path to directory containing audio files
            library_path: Path to organized music library
            dry_run: If True, preview changes without applying
            progress_callback: Callback for progress updates
            completion_callback: Callback on completion

        Returns:
            bool: True if import started successfully
        """
        return self.run_beets_import(
            source_path, library_path, dry_run, progress_callback, completion_callback
        )

    def _import_worker(
        self,
        source_path: str,
        config_file: Path,
        dry_run: bool,
        progress_callback: Optional[Callable[[str], None]],
        completion_callback: Optional[Callable[[bool, Optional[str]], None]]
    ) -> None:
        """
        Worker thread for beets import process using subprocess.
        Runs the actual `beet import` CLI command with fingerprinting.

        Args:
            source_path: Path to audio files
            config_file: Path to beets config
            dry_run: Preview mode flag
            progress_callback: Progress update callback
            completion_callback: Completion callback
        """
        try:
            if progress_callback:
                progress_callback("Starting Beets fingerprinting and tagging...")

            # Build beet import command
            cmd = [
                "beet",
                "-c", str(config_file),  # Use our config file
                "import",
                "-q",  # Quiet mode (skip interactive prompts)
                "-A",  # Auto-tag: use fingerprints and metadata
                source_path
            ]

            if dry_run:
                cmd.insert(3, "-p")  # Preview mode

            self.logger.info(f"Running command: {' '.join(cmd)}")

            if progress_callback:
                mode = "DRY RUN" if dry_run else "LIVE IMPORT"
                progress_callback(f"{mode}: Analyzing audio fingerprints via AcoustID...")

            # Set up environment with fpcalc path if installed locally
            env = os.environ.copy()
            installer = ChromaprintInstaller()
            fpcalc_path = installer.get_fpcalc_path()
            if fpcalc_path:
                # Add the directory containing fpcalc.exe to PATH
                fpcalc_dir = str(Path(fpcalc_path).parent)
                env['PATH'] = fpcalc_dir + os.pathsep + env.get('PATH', '')
                self.logger.info(f"Using fpcalc from: {fpcalc_path}")

            # Run beet import process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env
            )

            # Stream output and provide progress updates
            output_lines = []
            for line in process.stdout:
                line = line.strip()
                if line:
                    output_lines.append(line)
                    self.logger.debug(f"Beets: {line}")

                    # Provide meaningful progress updates
                    if "Sending" in line or "fingerprint" in line.lower():
                        if progress_callback:
                            progress_callback("Fingerprinting audio and querying AcoustID...")
                    elif "Tagging" in line or "match" in line.lower():
                        if progress_callback:
                            progress_callback("Applying metadata from MusicBrainz...")
                    elif "Embedding" in line or "art" in line.lower():
                        if progress_callback:
                            progress_callback("Downloading and embedding album art...")

            # Wait for completion
            return_code = process.wait()

            if return_code == 0:
                if progress_callback:
                    progress_callback("Import complete! Files tagged and organized.")
                if completion_callback:
                    completion_callback(True, None)
                self.logger.info(f"Beets import completed successfully for: {source_path}")
            else:
                error_msg = f"Beets import failed with code {return_code}"
                if output_lines:
                    error_msg += f"\nOutput: {output_lines[-5:]}"  # Last 5 lines
                if progress_callback:
                    progress_callback(f"Import failed: {error_msg}")
                if completion_callback:
                    completion_callback(False, error_msg)
                self.logger.error(error_msg)

        except Exception as e:
            error_msg = f"Beets import failed: {e}"
            self.logger.error(error_msg)
            if progress_callback:
                progress_callback(f"Error: {error_msg}")
            if completion_callback:
                completion_callback(False, error_msg)

    def cancel_all(self) -> None:
        """Cancel all active import operations."""
        self._cancel_event.set()
        self.logger.info("Beets import cancellation requested")
