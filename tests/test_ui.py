"""
Quick UI test script to verify the application works.
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from utils.logger import setup_logger
from ui.main_window import MainWindow


def test_ui():
    """Test that UI opens and basic functionality works."""
    print("=" * 60)
    print("TESTING YT-DLP EZ-UI")
    print("=" * 60)

    # Set up logging
    logger = setup_logger(console_output=True)
    logger.info("Starting UI test...")

    # Create application
    app = QApplication(sys.argv)

    # Create main window
    print("\n[OK] Creating main window...")
    window = MainWindow()

    # Check components exist
    print("[OK] Checking UI components...")
    assert hasattr(window, 'output_selector'), "Missing output_selector"
    assert hasattr(window, 'options_widget'), "Missing options_widget"
    assert hasattr(window, 'link_input'), "Missing link_input"
    assert hasattr(window, 'link_list'), "Missing link_list"
    assert hasattr(window, 'download_button'), "Missing download_button"
    print("[OK] All components present!")

    # Test queue manager
    print("\n[OK] Testing queue manager...")
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    window.queue_manager.add_url(test_url)
    assert window.queue_manager.get_count() == 1, "Failed to add URL to queue"
    print(f"[OK] Successfully added test URL: {test_url}")

    # Test link list refresh
    print("[OK] Testing link list refresh...")
    window.link_list.refresh()
    assert window.link_list.list_widget.count() == 1, "Link list not showing item"
    print("[OK] Link list displays correctly!")

    # Test clearing queue
    print("[OK] Testing queue clear...")
    window.queue_manager.clear()
    window.link_list.refresh()
    assert window.queue_manager.get_count() == 0, "Failed to clear queue"
    print("[OK] Queue cleared successfully!")

    # Show window briefly
    print("\n[OK] Showing window...")
    window.show()

    # Auto-close after 2 seconds
    QTimer.singleShot(2000, app.quit)

    print("\n" + "=" * 60)
    print("[SUCCESS] ALL TESTS PASSED!")
    print("The UI will close automatically in 2 seconds...")
    print("=" * 60 + "\n")

    # Run briefly
    app.exec()

    return True


if __name__ == "__main__":
    try:
        success = test_ui()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[FAILED] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
