"""
Link list widget for YT-DLP EZ-UI.
Displays the download queue with edit and delete options.
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem,
    QPushButton, QGroupBox, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QColor, QBrush

from core.queue_manager import QueueManager


class LinkListWidget(QWidget):
    """
    Widget for displaying and managing the download queue.
    Shows list of queued links with context menu for edit/delete.
    """

    item_removed = pyqtSignal(int)  # Emits index of removed item

    def __init__(self, queue_manager: QueueManager, parent=None):
        """
        Initialize the link list widget.

        Args:
            queue_manager: Queue manager instance
            parent: Parent widget
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)
        self.queue_manager = queue_manager

        self._init_ui()
        self._connect_signals()
        self.refresh()

    def _init_ui(self):
        """Initialize the user interface."""
        # Group box
        group_box = QGroupBox("Download Queue")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(group_box)

        # Inner layout
        layout = QVBoxLayout(group_box)

        # Queue info row
        info_layout = QHBoxLayout()
        self.queue_count_label = QLabel("Queue: 0 items")
        info_layout.addWidget(self.queue_count_label)

        info_layout.addStretch()

        # Clear all button
        self.clear_button = QPushButton("Clear All")
        self.clear_button.setObjectName("clearButton")
        self.clear_button.setToolTip("Remove all links from queue")
        info_layout.addWidget(self.clear_button)

        layout.addLayout(info_layout)

        # List widget
        self.list_widget = QListWidget()
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setMinimumHeight(150)
        # Disable user selection - highlighting is automatic only
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        layout.addWidget(self.list_widget)

    def _connect_signals(self):
        """Connect signals and slots."""
        self.clear_button.clicked.connect(self._on_clear_clicked)
        self.list_widget.customContextMenuRequested.connect(self._on_context_menu)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)

    def refresh(self):
        """Refresh the list display from queue manager."""
        self.list_widget.clear()

        items = self.queue_manager.get_all_items()
        count = len(items)

        # Update count label
        self.queue_count_label.setText(f"Queue: {count} item{'s' if count != 1 else ''}")

        # Add items to list
        for item in items:
            display_text = self._format_item_text(item)
            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.ItemDataRole.UserRole, item.url)
            self.list_widget.addItem(list_item)

        # Enable/disable clear button
        self.clear_button.setEnabled(count > 0)

        self.logger.info(f"List refreshed with {count} items")

    def _format_item_text(self, item) -> str:
        """
        Format queue item for display.

        Args:
            item: QueueItem instance

        Returns:
            str: Formatted display text
        """
        item_type = "[Playlist]" if item.is_playlist else "[Video]"
        return f"{item_type} {item.title}"

    def _on_clear_clicked(self):
        """Handle clear all button click."""
        self.queue_manager.clear()
        self.refresh()
        self.logger.info("Queue cleared by user")

    def _on_context_menu(self, position):
        """
        Handle right-click context menu.

        Args:
            position: Click position
        """
        item = self.list_widget.itemAt(position)
        if not item:
            return

        # Create context menu
        menu = QMenu(self)

        # Delete action
        delete_action = menu.addAction("Delete")

        # Show menu and handle action
        action = menu.exec(QCursor.pos())

        if action == delete_action:
            self._delete_item(item)

    def _on_item_double_clicked(self, item: QListWidgetItem):
        """
        Handle item double-click (alternative to right-click delete).

        Args:
            item: The clicked list item
        """
        # Show context menu on double-click as well
        menu = QMenu(self)
        delete_action = menu.addAction("Delete")
        action = menu.exec(QCursor.pos())

        if action == delete_action:
            self._delete_item(item)

    def _delete_item(self, item: QListWidgetItem):
        """
        Delete an item from the queue.

        Args:
            item: List widget item to delete
        """
        url = item.data(Qt.ItemDataRole.UserRole)
        if self.queue_manager.remove_url(url):
            self.refresh()
            self.logger.info(f"Item deleted: {url}")

    def get_selected_index(self) -> int:
        """
        Get the index of the currently selected item.

        Returns:
            int: Selected index, or -1 if none selected
        """
        row = self.list_widget.currentRow()
        return row if row >= 0 else -1

    def highlight_url(self, url: str):
        """
        Highlight the item with the specified URL (auto-highlight for current download).

        Args:
            url: The URL to highlight
        """
        # First, clear all highlights
        self.clear_all_highlights()

        # Find and highlight the matching item
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item_url = item.data(Qt.ItemDataRole.UserRole)

            if item_url == url:
                # Set highlight colors
                item.setBackground(QBrush(QColor("#cce8ff")))  # Light blue background
                item.setForeground(QBrush(QColor("#000000")))  # Black text

                # Make text bold
                font = item.font()
                font.setBold(True)
                item.setFont(font)

                self.logger.info(f"Highlighted URL: {url}")
                break

    def clear_all_highlights(self):
        """
        Clear all highlights from the list (reset to default styling).
        """
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)

            # Reset to default colors
            item.setBackground(QBrush(QColor("#ffffff")))  # White background
            item.setForeground(QBrush(QColor("#000000")))  # Black text

            # Reset font to normal
            font = item.font()
            font.setBold(False)
            item.setFont(font)
