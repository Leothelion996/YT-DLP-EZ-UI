"""
UI styling for YT-DLP EZ-UI.
Contains stylesheet definitions and theme constants for PyQt6.
"""

# Main application stylesheet
MAIN_STYLESHEET = """
QMainWindow {
    background-color: #f0f0f0;
}

QLabel {
    font-size: 12px;
    color: #3e3f40;
}

QLineEdit {
    padding: 8px;
    border: 1px solid #cccccc;
    border-radius: 4px;
    background-color: white;
    color: #000000;
    font-size: 12px;
}

QLineEdit:focus {
    border: 1px solid #0078d4;
}

QPushButton {
    padding: 8px 16px;
    background-color: #0078d4;
    color: white;
    border: none;
    border-radius: 4px;
    font-size: 12px;
    min-width: 80px;
}

QPushButton:hover {
    background-color: #106ebe;
}

QPushButton:pressed {
    background-color: #005a9e;
}

QPushButton:disabled {
    background-color: #cccccc;
    color: #666666;
}

QPushButton#addButton {
    min-width: 40px;
    padding: 8px;
    font-weight: bold;
    font-size: 14px;
}

QPushButton#clearButton {
    background-color: #d13438;
}

QPushButton#clearButton:hover {
    background-color: #b02a2e;
}

QComboBox {
    padding: 8px;
    border: 1px solid #cccccc;
    border-radius: 4px;
    background-color: white;
    color: #000000;
    font-size: 12px;
}

QComboBox:hover {
    border: 1px solid #0078d4;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #666666;
    margin-right: 5px;
}

QListWidget {
    border: 1px solid #cccccc;
    border-radius: 4px;
    background-color: white;
    padding: 4px;
    color: #000000;
}

QListWidget::item {
    padding: 8px;
    border-bottom: 1px solid #eeeeee;
    color: #000000;
}

QListWidget::item:hover {
    background-color: #e8f4ff;
}

QListWidget::item:selected {
    background-color: #cce8ff;
    color: #000000;
}

QProgressBar {
    border: 1px solid #cccccc;
    border-radius: 4px;
    text-align: center;
    background-color: white;
}

QProgressBar::chunk {
    background-color: #0078d4;
    border-radius: 3px;
}

QTextEdit {
    border: 1px solid #cccccc;
    border-radius: 4px;
    background-color: white;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 11px;
    padding: 8px;
}

QGroupBox {
    font-weight: bold;
    border: 1px solid #cccccc;
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 12px;
    color: #3e3f40;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
    color: #3e3f40;
}

QStatusBar {
    background-color: #f8f8f8;
    border-top: 1px solid #cccccc;
}

QMenu {
    background-color: white;
    border: 1px solid #cccccc;
}

QMenu::item {
    padding: 6px 20px;
}

QMenu::item:selected {
    background-color: #0078d4;
    color: white;
}

QMessageBox {
    background-color: #2d2d2d;
    color: #ffffff;
}

QMessageBox QLabel {
    color: #ffffff;
    font-size: 12px;
}

QMessageBox QPushButton {
    background-color: #0078d4;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    min-width: 80px;
}

QMessageBox QPushButton:hover {
    background-color: #106ebe;
}

QDialog {
    background-color: #2d2d2d;
    color: #ffffff;
}

QDialog QLabel {
    color: #ffffff;
    font-size: 12px;
}

QDialog QTextEdit {
    background-color: #1e1e1e;
    color: #ffffff;
    border: 1px solid #555555;
}

QDialog QPushButton {
    background-color: #0078d4;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    min-width: 80px;
}

QDialog QPushButton:hover {
    background-color: #106ebe;
}
"""

# Color constants
COLOR_PRIMARY = "#0078d4"
COLOR_PRIMARY_HOVER = "#106ebe"
COLOR_PRIMARY_PRESSED = "#005a9e"
COLOR_DANGER = "#d13438"
COLOR_DANGER_HOVER = "#b02a2e"
COLOR_SUCCESS = "#107c10"
COLOR_WARNING = "#ff8c00"
COLOR_BACKGROUND = "#f0f0f0"
COLOR_SURFACE = "#ffffff"
COLOR_BORDER = "#cccccc"
COLOR_TEXT = "#333333"
COLOR_TEXT_SECONDARY = "#666666"

# Font sizes
FONT_SIZE_SMALL = 11
FONT_SIZE_NORMAL = 12
FONT_SIZE_LARGE = 14
FONT_SIZE_TITLE = 16
