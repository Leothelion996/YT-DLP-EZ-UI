"""
Link list widget for YT-DLP EZ-UI.
Displays the download queue with edit and delete options.
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem,
    QPushButton, QGroupBox, QMenu, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QColor, QBrush

from core.queue_manager import QueueManager
from config.settings import SettingsManager


class LinkListWidget(QWidget):
    """
    Widget for displaying and managing the download queue.
    Shows list of queued links with context menu for edit/delete.
    """

    item_removed = pyqtSignal(int)  # Emits index of removed item

    def __init__(self, queue_manager: QueueManager, settings: SettingsManager, parent=None):
        """
        Initialize the link list widget.

        Args:
            queue_manager: Queue manager instance
            settings: Settings manager instance
            parent: Parent widget
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)
        self.queue_manager = queue_manager
        self.settings = settings

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
        # Remove any borders that might obstruct text
        # User Changed padding and it should not be changed from 0px.
        self.list_widget.setStyleSheet("""
            QListWidget {
                border: none;
                outline: none;
            }
            QListWidget::item {
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
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
            list_item = QListWidgetItem()
            list_item.setData(Qt.ItemDataRole.UserRole, item.url)
            self.list_widget.addItem(list_item)

            # Create custom widget for the item
            item_widget = self._create_item_widget(item)
            list_item.setSizeHint(item_widget.sizeHint())
            self.list_widget.setItemWidget(list_item, item_widget)

        # Enable/disable clear button
        self.clear_button.setEnabled(count > 0)

        self.logger.info(f"List refreshed with {count} items")

    def _create_item_widget(self, item) -> QWidget:
        """
        Create a custom widget for a queue item.
        Playlists get an 'Album?' checkbox, videos just show text.
        Checkbox is only shown for playlists when file format is 'audio'.

        Args:
            item: QueueItem instance

        Returns:
            QWidget: Custom widget for the item
        """
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
            }
        """)

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(10)

        # Format the display text
        item_type = "[Playlist]" if item.is_playlist else "[Video]"
        text_label = QLabel(f"{item_type} {item.title}")
        text_label.setStyleSheet("color: #000000; background-color: transparent; border: none;")
        layout.addWidget(text_label)

        # Add stretch to push checkbox to the right
        layout.addStretch()

        # Add "Album?" checkbox only for playlists when file format is 'audio'
        file_format = self.settings.get("file_format", "video")
        if item.is_playlist and file_format == "audio":
            # Checkbox WITHOUT text
            album_checkbox = QCheckBox()
            album_checkbox.setChecked(item.is_album)
            album_checkbox.setToolTip("Mark this playlist as an album to normalize metadata")
            album_checkbox.setStyleSheet("""
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border: 2px solid #000000;
                    background-color: #FFFFFF;
                }
                QCheckBox::indicator:checked {
                    background-color: #4CAF50;
                    border: 2px solid #000000;
                    image: none;
                }
                QCheckBox::indicator:unchecked {
                    background-color: #FFFFFF;
                    border: 2px solid #000000;
                }
                QCheckBox::indicator:hover {
                    border: 2px solid #333333;
                }
            """)

            # Connect checkbox to update queue manager
            album_checkbox.stateChanged.connect(
                lambda state, url=item.url: self._on_album_checkbox_changed(url, state == 2)
            )

            layout.addWidget(album_checkbox)

            # Separate "Album?" label to the right of checkbox
            album_label = QLabel("Album?")
            album_label.setStyleSheet("color: #000000; background-color: transparent; border: none;")
            layout.addWidget(album_label)

        return widget

    def _on_album_checkbox_changed(self, url: str, is_checked: bool):
        """
        Handle album checkbox state change.

        Args:
            url: URL of the queue item
            is_checked: New checkbox state
        """
        self.queue_manager.set_album_status(url, is_checked)
        self.logger.info(f"Album status for {url}: {is_checked}")

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
                # Get the custom widget
                widget = self.list_widget.itemWidget(item)
                if widget:
                    # Set highlight background on the widget
                    widget.setStyleSheet("""
                        QWidget {
                            background-color: #cce8ff;
                            border: none;
                        }
                    """)

                    # Find the QLabel and make it bold with proper text color
                    for child in widget.findChildren(QLabel):
                        child.setStyleSheet("color: #000000; background-color: transparent; border: none;")
                        font = child.font()
                        font.setBold(True)
                        child.setFont(font)

                    # Find the QCheckBox and maintain its styling
                    for child in widget.findChildren(QCheckBox):
                        child.setStyleSheet("""
                            QCheckBox::indicator {
                                width: 18px;
                                height: 18px;
                                border: 2px solid #000000;
                                background-color: #FFFFFF;
                            }
                            QCheckBox::indicator:checked {
                                background-color: #4CAF50;
                                border: 2px solid #000000;
                                image: none;
                            }
                            QCheckBox::indicator:unchecked {
                                background-color: #FFFFFF;
                                border: 2px solid #000000;
                            }
                            QCheckBox::indicator:hover {
                                border: 2px solid #333333;
                            }
                        """)

                self.logger.info(f"Highlighted URL: {url}")
                break

    def clear_all_highlights(self):
        """
        Clear all highlights from the list (reset to default styling).
        """
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)

            # Get the custom widget
            widget = self.list_widget.itemWidget(item)
            if widget:
                # Reset background
                widget.setStyleSheet("""
                    QWidget {
                        background-color: transparent;
                        border: none;
                    }
                """)

                # Reset font and color to normal
                for child in widget.findChildren(QLabel):
                    child.setStyleSheet("color: #000000; background-color: transparent; border: none;")
                    font = child.font()
                    font.setBold(False)
                    child.setFont(font)

                # Reset checkbox styling
                for child in widget.findChildren(QCheckBox):
                    child.setStyleSheet("""
                        QCheckBox::indicator {
                            width: 18px;
                            height: 18px;
                            border: 2px solid #000000;
                            background-color: #FFFFFF;
                        }
                        QCheckBox::indicator:checked {
                            background-color: #4CAF50;
                            border: 2px solid #000000;
                            image: none;
                        }
                        QCheckBox::indicator:unchecked {
                            background-color: #FFFFFF;
                            border: 2px solid #000000;
                        }
                        QCheckBox::indicator:hover {
                            border: 2px solid #333333;
                        }
                    """)
