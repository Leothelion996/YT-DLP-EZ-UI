"""
YT-DLP EZ-UI - YouTube Downloader with Easy-to-Use Interface
Main application entry point.
"""

import sys
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from utils.logger import setup_logger
from config.constants import APP_NAME
from ui.main_window import MainWindow


def main():
    """Main application entry point."""
    # Set up logging
    logger = setup_logger(console_output=True)
    logger.info(f"Starting {APP_NAME}...")

    try:
        # Enable high DPI support
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

        # Create application
        app = QApplication(sys.argv)
        app.setApplicationName(APP_NAME)

        # Create and show main window
        window = MainWindow()
        window.show()

        logger.info("Application started successfully")

        # Start event loop
        sys.exit(app.exec())

    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
