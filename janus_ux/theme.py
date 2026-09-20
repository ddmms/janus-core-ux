"""Modern dark styling and CSS tokens for Janus Core UX."""

DARK_STYLESHEET = """
/* Global Window & Font */
QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
    selection-background-color: #89b4fa;
    selection-color: #11111b;
}

QMainWindow, QDialog {
    background-color: #181825;
}

/* ToolBar & MenuBar */
QMenuBar {
    background-color: #181825;
    color: #cdd6f4;
    border-bottom: 1px solid #313244;
    padding: 2px 4px;
}
QMenuBar::item {
    background: transparent;
    padding: 6px 10px;
    border-radius: 4px;
}
QMenuBar::item:selected {
    background-color: #313244;
}

QMenu {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item {
    padding: 6px 20px;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: #45475a;
    color: #cdd6f4;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #313244;
    background-color: #181825;
    border-radius: 8px;
    top: -1px;
}
QTabBar::tab {
    background-color: #181825;
    color: #a6adc8;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    border: 1px solid transparent;
    font-weight: 500;
}
QTabBar::tab:hover {
    background-color: #252538;
    color: #cdd6f4;
}
QTabBar::tab:selected {
    background-color: #1e1e2e;
    color: #89b4fa;
    border: 1px solid #313244;
    border-bottom: 2px solid #89b4fa;
    font-weight: bold;
}

/* Group Boxes & Frames */
QGroupBox {
    border: 1px solid #313244;
    border-radius: 8px;
    margin-top: 18px;
    padding: 12px 8px 8px 8px;
    background-color: #1e1e2e;
    font-weight: 600;
    color: #b4befe;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    background-color: #1e1e2e;
}

QFrame.card {
    background-color: #1e1e2e;
    border: 1px solid #313244;
    border-radius: 8px;
    padding: 10px;
}

/* Inputs & Form Controls */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 22px;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #89b4fa;
    background-color: #1b1b2a;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #45475a;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}
QComboBox QAbstractItemView {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #45475a;
    selection-background-color: #45475a;
}

/* Buttons */
QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 500;
    min-height: 20px;
}
QPushButton:hover {
    background-color: #45475a;
    border-color: #585b70;
}
QPushButton:pressed {
    background-color: #585b70;
}
QPushButton:disabled {
    background-color: #181825;
    color: #585b70;
    border-color: #313244;
}

QPushButton.primary {
    background-color: #89b4fa;
    color: #11111b;
    border: 1px solid #89b4fa;
    font-weight: 600;
}
QPushButton.primary:hover {
    background-color: #b4befe;
    border-color: #b4befe;
}
QPushButton.primary:pressed {
    background-color: #74c7ec;
}

QPushButton.success {
    background-color: #a6e3a1;
    color: #11111b;
    border: 1px solid #a6e3a1;
    font-weight: 600;
}
QPushButton.success:hover {
    background-color: #94e2d5;
}

QPushButton.danger {
    background-color: #f38ba8;
    color: #11111b;
    border: 1px solid #f38ba8;
    font-weight: 600;
}
QPushButton.danger:hover {
    background-color: #eba0ac;
}

/* Checkboxes */
QCheckBox {
    spacing: 8px;
    color: #cdd6f4;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #45475a;
    background-color: #181825;
}
QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background-color: #181825;
    width: 10px;
    border-radius: 5px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background-color: #45475a;
    min-height: 25px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background-color: #585b70;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    border: none;
    background-color: #181825;
    height: 10px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background-color: #45475a;
    min-width: 25px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #585b70;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Tables & Lists */
QTableWidget, QTreeWidget, QListWidget {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 6px;
    gridline-color: #313244;
    color: #cdd6f4;
}
QHeaderView::section {
    background-color: #1e1e2e;
    color: #b4befe;
    padding: 6px 8px;
    border: none;
    border-right: 1px solid #313244;
    border-bottom: 1px solid #313244;
    font-weight: 600;
}

/* Splitter */
QSplitter::handle {
    background-color: #313244;
}
QSplitter::handle:hover {
    background-color: #89b4fa;
}
QSplitter::handle:horizontal {
    width: 3px;
}
QSplitter::handle:vertical {
    height: 3px;
}

/* Status Bar */
QStatusBar {
    background-color: #11111b;
    border-top: 1px solid #313244;
    color: #a6adc8;
}

/* Tooltips */
QToolTip {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 8px;
}
"""
