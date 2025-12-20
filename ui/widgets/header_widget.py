"""
Header widget for BatchRipTagger YT (v5.0).
Displays application logo and branded title.
"""

import logging
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QFont

from config.constants import APP_NAME, APP_LOGO_PATH, APP_FONT_PATH, COLOR_NEON_BLUE
from ui.styles import load_custom_font


class HeaderWidget(QWidget):
    """
    Header widget displaying logo and application title.
    Uses custom font and neon blue branding.
    """

    def __init__(self, parent=None):
        """
        Initialize the header widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self._custom_font_family = None
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        # Main horizontal layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(12)

        # Logo
        logo_label = QLabel()
        if APP_LOGO_PATH.exists():
            pixmap = QPixmap(str(APP_LOGO_PATH))
            # Scale to 92x92 while maintaining aspect ratio
            scaled_pixmap = pixmap.scaled(
                92, 92,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            logo_label.setPixmap(scaled_pixmap)
            logo_label.setFixedSize(92, 92)
            self.logger.info(f"Logo loaded from {APP_LOGO_PATH}")
        else:
            logo_label.setText("LOGO")
            logo_label.setStyleSheet(f"color: {COLOR_NEON_BLUE}; font-weight: bold;")
            self.logger.warning(f"Logo not found at {APP_LOGO_PATH}")

        layout.addWidget(logo_label)

        # Title with custom font
        title_label = QLabel(APP_NAME)
        title_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        # Load custom font
        self._custom_font_family = load_custom_font(APP_FONT_PATH)

        if self._custom_font_family:
            # Apply custom font
            custom_font = QFont(self._custom_font_family, 24)
            custom_font.setBold(True)
            title_label.setFont(custom_font)
            self.logger.info(f"Custom font loaded: {self._custom_font_family}")
        else:
            # Fallback to system font
            title_label.setStyleSheet("font-size: 24px; font-weight: bold;")
            self.logger.warning(f"Custom font not found at {APP_FONT_PATH}, using fallback")

        # Apply neon blue color
        title_label.setStyleSheet(f"color: {COLOR_NEON_BLUE}; font-size: 24px; font-weight: bold;")

        layout.addWidget(title_label)
        layout.addStretch()  # Push everything to the left

        self.logger.debug("Header widget initialized")
