"""Headless / Display verification script.

Renders MainWindow and saves a screenshot.
"""

from __future__ import annotations

from pathlib import Path
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from janus_ux.app import MainWindow


def run_verification():
    """Render main window and capture screenshot."""
    app = QApplication.instance() or QApplication(sys.argv)
    win = MainWindow()
    win.resize(1380, 890)
    win.show()

    # Show main window with tabs
    win.tab_widget.setCurrentIndex(0)

    def capture_and_quit():
        pixmap = win.grab()
        out_path = Path(__file__).resolve().parent / "app_screenshot.png"
        pixmap.save(str(out_path), "PNG")
        print(f"Screenshot saved to: {out_path}")
        print("Environments tab rendered successfully!")
        app.quit()

    QTimer.singleShot(1500, capture_and_quit)
    app.exec()


if __name__ == "__main__":
    run_verification()
