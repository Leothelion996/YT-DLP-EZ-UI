"""
Log viewer widget for YT-DLP EZ-UI.
Displays real-time download logs and yt-dlp output in a terminal-style view.
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QLabel
)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QTextCursor


class LogViewer(QWidget):
    """
    Collapsible log viewer widget.
    Shows real-time download progress and yt-dlp output.
    """

    def __init__(self, parent=None):
        """
        Initialize the log viewer.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)

        self._init_ui()
        self.hide()  # Hidden by default

    def _init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 8, 0, 0)
        main_layout.setSpacing(4)

        # Header label
        header_label = QLabel("Download Details:")
        header_label.setStyleSheet("color: #3e3f40; font-weight: bold;")
        main_layout.addWidget(header_label)

        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(150)
        self.log_text.setMaximumHeight(300)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        main_layout.addWidget(self.log_text)

    @pyqtSlot(str)
    def append_log(self, message: str):
        """
        Append a message to the log viewer.

        Args:
            message: Log message to append
        """
        # Append message
        self.log_text.append(message)

        # Auto-scroll to bottom
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)

    @pyqtSlot()
    def clear_log(self):
        """Clear all log messages."""
        self.log_text.clear()
        self.logger.info("Log viewer cleared")

    def show_viewer(self):
        """Show the log viewer."""
        self.show()
        self.logger.info("Log viewer shown")

    def hide_viewer(self):
        """Hide the log viewer."""
        self.hide()
        self.logger.info("Log viewer hidden")

    def toggle_visibility(self, visible: bool):
        """
        Toggle log viewer visibility.

        Args:
            visible: True to show, False to hide
        """
        if visible:
            self.show_viewer()
        else:
            self.hide_viewer()
