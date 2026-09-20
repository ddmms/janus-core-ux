"""CLI Entrypoint for launching Janus Core UX."""

import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from janus_ux.app import MainWindow

def main():
    """Launch the Janus Core desktop UX."""
    # Enable high DPI scaling
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    app.setApplicationName("Janus-Core UX")
    app.setOrganizationName("STFC")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
