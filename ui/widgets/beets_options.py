"""
Beets options widget for YT-DLP EZ-UI.
Provides controls for music fingerprinting and tagging with AcoustID.
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QCheckBox,
    QLineEdit, QPushButton, QDialog, QDialogButtonBox,
    QMessageBox, QGroupBox, QTextEdit, QProgressDialog
)
from PyQt6.QtCore import pyqtSignal, Qt, QThread
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl

from config.settings import SettingsManager
from config.user_profile import UserProfile
from core.beets_manager import BeetsManager
from utils.chromaprint_installer import ChromaprintInstaller


class AcoustIDSetupDialog(QDialog):
    """
    Modal dialog for first-time AcoustID API key setup.
    Provides link to key registration and secure input.
    """

    def __init__(self, parent=None):
        """
        Initialize the setup dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.api_key = None

        self.setWindowTitle("AcoustID Setup")
        self.setModal(True)
        self.setMinimumWidth(500)

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("<h2>Music Fingerprinting Setup</h2>")
        layout.addWidget(title)

        # Description
        description = QTextEdit()
        description.setReadOnly(True)
        description.setMaximumHeight(120)
        description.setHtml("""
        <p>This feature uses <b>AcoustID fingerprinting</b> to automatically identify and tag your music files with accurate metadata from MusicBrainz.</p>
        <p><b>Features:</b></p>
        <ul>
            <li>Automatic artist, album, and track identification</li>
            <li>Album art download and embedding</li>
            <li>Organized library structure</li>
        </ul>
        <p>To use this feature, you need a free AcoustID API key.</p>
        """)
        layout.addWidget(description)

        # API key link
        link_layout = QHBoxLayout()
        link_label = QLabel("Get your free API key:")
        link_button = QPushButton("Open AcoustID Registration")
        link_button.clicked.connect(self._open_acoustid_website)
        link_layout.addWidget(link_label)
        link_layout.addWidget(link_button)
        link_layout.addStretch()
        layout.addLayout(link_layout)

        # API key input
        key_layout = QVBoxLayout()
        key_label = QLabel("Enter your AcoustID API key:")
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Paste your API key here")
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        key_layout.addWidget(key_label)
        key_layout.addWidget(self.key_input)
        layout.addLayout(key_layout)

        # Show/hide key checkbox
        self.show_key_checkbox = QCheckBox("Show API key")
        self.show_key_checkbox.stateChanged.connect(self._toggle_key_visibility)
        layout.addWidget(self.show_key_checkbox)

        # Security info
        security_info = QLabel(
            "🔒 Your API key will be stored securely in Windows Credential Manager "
            "and never saved in plaintext."
        )
        security_info.setWordWrap(True)
        security_info.setStyleSheet("color: #666; font-size: 10pt; margin-top: 10px;")
        layout.addWidget(security_info)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _open_acoustid_website(self):
        """Open AcoustID API key registration page in browser."""
        url = QUrl("https://acoustid.org/api-key")
        QDesktopServices.openUrl(url)
        self.logger.info("Opened AcoustID registration page")

    def _toggle_key_visibility(self, state):
        """
        Toggle visibility of API key in input field.

        Args:
            state: Checkbox state
        """
        if state == Qt.CheckState.Checked.value:
            self.key_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.key_input.setEchoMode(QLineEdit.EchoMode.Password)

    def _validate_and_accept(self):
        """Validate API key and install dependencies before accepting dialog."""
        api_key = self.key_input.text().strip()

        if not api_key:
            QMessageBox.warning(
                self,
                "Missing API Key",
                "Please enter your AcoustID API key."
            )
            return

        # Basic validation
        beets_manager = BeetsManager()
        if not beets_manager.validate_key(api_key):
            QMessageBox.warning(
                self,
                "Invalid API Key",
                "The API key format appears invalid. AcoustID keys are typically 8+ alphanumeric characters."
            )
            return

        # Check if chromaprint is installed, install if needed
        installer = ChromaprintInstaller()
        if not installer.is_installed():
            # Ask user permission to install
            reply = QMessageBox.question(
                self,
                "Install Chromaprint",
                "Chromaprint (fpcalc) is required for audio fingerprinting.\n\n"
                "Would you like to download and install it now? (~2MB download)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if reply == QMessageBox.StandardButton.Yes:
                # Show progress dialog
                progress = QProgressDialog(
                    "Installing Chromaprint...",
                    "Cancel",
                    0, 100,
                    self
                )
                progress.setWindowTitle("Installing Dependencies")
                progress.setWindowModality(Qt.WindowModality.WindowModal)
                progress.show()

                # Install chromaprint
                def update_progress(message: str, percent: int):
                    progress.setLabelText(message)
                    progress.setValue(percent)

                success = installer.install(progress_callback=update_progress)
                progress.close()

                if not success:
                    QMessageBox.critical(
                        self,
                        "Installation Failed",
                        "Failed to install Chromaprint. You can install it manually from:\n"
                        "https://acoustid.org/chromaprint"
                    )
                    return

                self.logger.info("Chromaprint installed successfully")
            else:
                QMessageBox.warning(
                    self,
                    "Installation Required",
                    "Chromaprint is required for audio fingerprinting.\n"
                    "You can install it manually from: https://acoustid.org/chromaprint"
                )
                return

        self.api_key = api_key
        self.accept()

    def get_api_key(self) -> str:
        """
        Get the entered API key.

        Returns:
            str: The API key entered by user
        """
        return self.api_key


class BeetsOptionsWidget(QWidget):
    """
    Widget for controlling Beets music tagging feature.
    Provides checkbox to enable/disable and first-time setup modal.
    """

    beets_enabled_changed = pyqtSignal(bool)  # Emits True/False when toggled

    def __init__(self, settings: SettingsManager, beets_manager: BeetsManager, parent=None):
        """
        Initialize the beets options widget.

        Args:
            settings: Settings manager instance
            beets_manager: Beets manager instance
            parent: Parent widget
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)
        self.settings = settings
        self.beets_manager = beets_manager
        self.user_profile = UserProfile()

        self._init_ui()
        self._load_saved_settings()
        self._connect_signals()

    def _init_ui(self):
        """Initialize the user interface."""
        # Main horizontal layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Checkbox for enabling beets
        self.beets_checkbox = QCheckBox("Auto-tag with music fingerprinting (beets)")
        self.beets_checkbox.setStyleSheet("color: black;")
        self.beets_checkbox.setToolTip(
            "Automatically identify and tag music files using AcoustID fingerprinting"
        )
        layout.addWidget(self.beets_checkbox)

        # Status label
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addWidget(self.status_label)

        # Configure button
        self.config_button = QPushButton("Configure")
        self.config_button.setMaximumWidth(100)
        self.config_button.clicked.connect(self._show_setup_dialog)
        layout.addWidget(self.config_button)

        layout.addStretch()

        # Update initial status
        self._update_status_label()

    def _connect_signals(self):
        """Connect signals and slots."""
        self.beets_checkbox.stateChanged.connect(self._on_checkbox_changed)

    def _load_saved_settings(self):
        """Load saved beets settings."""
        # Check if beets is available
        if not self.beets_manager.is_available():
            self.beets_checkbox.setEnabled(False)
            self.status_label.setText("(Beets not installed)")
            self.config_button.setEnabled(False)
            return

        # Load enabled state
        enabled = self.settings.get("beets_enabled", False)
        self.beets_checkbox.setChecked(enabled)

        # Check if configured
        if not self.beets_manager.is_acoustid_configured():
            self.status_label.setText("(Not configured)")
        else:
            self.status_label.setText("(Configured)")

    def _update_status_label(self):
        """Update the status label based on current state."""
        if not self.beets_manager.is_available():
            self.status_label.setText("(Beets not installed)")
            return

        if self.beets_manager.is_acoustid_configured():
            self.status_label.setText("(Configured ✓)")
            self.status_label.setStyleSheet("color: #2ecc71; font-size: 9pt;")
        else:
            self.status_label.setText("(Not configured)")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 9pt;")

    def _on_checkbox_changed(self, state):
        """
        Handle checkbox state change.

        Args:
            state: Checkbox state (checked/unchecked)
        """
        enabled = (state == Qt.CheckState.Checked.value)

        # If enabling and not configured, show setup dialog
        if enabled and not self.beets_manager.is_acoustid_configured():
            if not self._show_setup_dialog():
                # User cancelled setup, uncheck the box
                self.beets_checkbox.setChecked(False)
                return

        # Save setting
        self.settings.set("beets_enabled", enabled)
        self.settings.set("beets_acoustid_configured", self.beets_manager.is_acoustid_configured())

        # Emit signal
        self.beets_enabled_changed.emit(enabled)

        self.logger.info(f"Beets tagging {'enabled' if enabled else 'disabled'}")

    def _show_setup_dialog(self) -> bool:
        """
        Show the AcoustID setup dialog.

        Returns:
            bool: True if setup completed successfully, False if cancelled
        """
        dialog = AcoustIDSetupDialog(self)
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            api_key = dialog.get_api_key()
            if api_key and self.beets_manager.set_acoustid_key(api_key):
                # Update status label
                self._update_status_label()

                # Save to settings (legacy)
                self.settings.set("beets_acoustid_configured", True)

                # Save to user profile
                self.user_profile.mark_acoustid_configured(True)
                self.user_profile.mark_beets_setup_completed()

                # Check if chromaprint was installed
                installer = ChromaprintInstaller()
                if installer.is_installed():
                    self.user_profile.mark_chromaprint_installed(True)

                QMessageBox.information(
                    self,
                    "Setup Complete",
                    "AcoustID API key has been saved securely. Music fingerprinting is now enabled."
                )
                return True
            else:
                QMessageBox.critical(
                    self,
                    "Setup Failed",
                    "Failed to save API key. Please try again."
                )
                return False
        else:
            return False

    def is_enabled(self) -> bool:
        """
        Check if beets tagging is enabled.

        Returns:
            bool: True if enabled and configured
        """
        return (
            self.beets_checkbox.isChecked() and
            self.beets_manager.is_acoustid_configured()
        )

    def set_format_visibility(self, file_format: str):
        """
        Show or hide the widget based on format selection.
        Only show for audio formats (hide for video).

        Args:
            file_format: The selected format ("audio" or "video")
        """
        if file_format == "audio":
            self.show()
            self.logger.info("BeetsOptionsWidget shown for audio format")
        else:
            self.hide()
            self.logger.info("BeetsOptionsWidget hidden for video format")
