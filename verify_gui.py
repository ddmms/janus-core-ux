"""Headless / Display verification script that renders MainWindow and saves a screenshot."""

import os
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from janus_ux.app import MainWindow

def run_verification():
    app = QApplication.instance() or QApplication(sys.argv)
    win = MainWindow()
    win.resize(1380, 890)
    win.show()

    # Switch to Environments tab
    win.tab_widget.setCurrentIndex(8)

    def capture_and_quit():
        pixmap = win.grab()
        out_path = os.path.join(os.path.dirname(__file__), "app_screenshot.png")
        pixmap.save(out_path, "PNG")
        print(f"Screenshot saved to: {out_path}")
        print("Environments tab rendered successfully!")
        app.quit()

    QTimer.singleShot(1500, capture_and_quit)
    app.exec()

if __name__ == "__main__":
    run_verification()
