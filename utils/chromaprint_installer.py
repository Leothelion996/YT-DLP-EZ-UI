"""
Chromaprint installer utility for YT-DLP EZ-UI.
Handles automatic download and installation of fpcalc.exe for Windows.
"""

import logging
import os
import sys
import zipfile
import shutil
import urllib.request
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# Chromaprint download URL for Windows
CHROMAPRINT_VERSION = "1.5.1"
CHROMAPRINT_URL = f"https://github.com/acoustid/chromaprint/releases/download/v{CHROMAPRINT_VERSION}/chromaprint-fpcalc-{CHROMAPRINT_VERSION}-windows-x86_64.zip"


class ChromaprintInstaller:
    """
    Manages Chromaprint (fpcalc.exe) installation.
    Downloads and installs fpcalc.exe to application directory.
    """

    def __init__(self, install_dir: Optional[Path] = None):
        """
        Initialize the installer.

        Args:
            install_dir: Directory to install fpcalc.exe (defaults to app directory)
        """
        self.logger = logging.getLogger(__name__)

        # Default install directory is app root
        if install_dir is None:
            install_dir = Path(__file__).parent.parent / "bin"

        self.install_dir = Path(install_dir)
        self.fpcalc_path = self.install_dir / "fpcalc.exe"

    def is_installed(self) -> bool:
        """
        Check if Chromaprint/fpcalc is already installed.

        Returns:
            bool: True if fpcalc.exe exists and is executable
        """
        # Check in install directory
        if self.fpcalc_path.exists():
            self.logger.info(f"fpcalc.exe found at: {self.fpcalc_path}")
            return True

        # Check in system PATH
        if shutil.which("fpcalc"):
            self.logger.info("fpcalc found in system PATH")
            return True

        return False

    def get_fpcalc_path(self) -> Optional[str]:
        """
        Get the path to fpcalc executable.

        Returns:
            str or None: Path to fpcalc.exe if found
        """
        if self.fpcalc_path.exists():
            return str(self.fpcalc_path)

        # Check system PATH
        system_fpcalc = shutil.which("fpcalc")
        if system_fpcalc:
            return system_fpcalc

        return None

    def install(
        self,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> bool:
        """
        Download and install Chromaprint/fpcalc.

        Args:
            progress_callback: Callback for progress updates (message, percentage)

        Returns:
            bool: True if installation successful
        """
        try:
            if self.is_installed():
                self.logger.info("Chromaprint already installed")
                if progress_callback:
                    progress_callback("Chromaprint already installed", 100)
                return True

            # Create install directory
            self.install_dir.mkdir(parents=True, exist_ok=True)

            # Download chromaprint zip
            zip_path = self.install_dir / "chromaprint.zip"

            if progress_callback:
                progress_callback("Downloading Chromaprint...", 10)

            self.logger.info(f"Downloading Chromaprint from: {CHROMAPRINT_URL}")

            # Download with progress
            def download_progress(block_num, block_size, total_size):
                if progress_callback and total_size > 0:
                    downloaded = block_num * block_size
                    percent = min(int((downloaded / total_size) * 60) + 10, 70)
                    progress_callback(f"Downloading... {downloaded // 1024}KB / {total_size // 1024}KB", percent)

            urllib.request.urlretrieve(
                CHROMAPRINT_URL,
                zip_path,
                reporthook=download_progress
            )

            if progress_callback:
                progress_callback("Extracting files...", 75)

            # Extract fpcalc.exe
            self.logger.info(f"Extracting to: {self.install_dir}")

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Find fpcalc.exe in the archive
                for file_info in zip_ref.filelist:
                    if file_info.filename.endswith('fpcalc.exe'):
                        # Extract just fpcalc.exe
                        file_info.filename = 'fpcalc.exe'
                        zip_ref.extract(file_info, self.install_dir)
                        break

            # Clean up zip file
            zip_path.unlink()

            if progress_callback:
                progress_callback("Installation complete!", 100)

            # Verify installation
            if self.fpcalc_path.exists():
                self.logger.info(f"Chromaprint installed successfully at: {self.fpcalc_path}")
                return True
            else:
                raise FileNotFoundError("fpcalc.exe not found after extraction")

        except Exception as e:
            error_msg = f"Failed to install Chromaprint: {e}"
            self.logger.error(error_msg)
            if progress_callback:
                progress_callback(f"Installation failed: {e}", 0)
            return False

    def uninstall(self) -> bool:
        """
        Remove installed Chromaprint/fpcalc.

        Returns:
            bool: True if uninstallation successful
        """
        try:
            if self.fpcalc_path.exists():
                self.fpcalc_path.unlink()
                self.logger.info("Chromaprint uninstalled")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to uninstall Chromaprint: {e}")
            return False
