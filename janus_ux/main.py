"""CLI Entrypoint for launching Janus Core UX."""

from __future__ import annotations

import os
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from janus_ux.app import MainWindow
from janus_ux.core.desktop_integration import get_asset_path, install_desktop_entry


def main():
    """Launch the Janus Core desktop UX or handle CLI options."""
    if "--install-desktop" in sys.argv:
        success = install_desktop_entry()
        if success:
            print(
                "Desktop icon and .desktop shortcut installed successfully to ~/.local/share/applications!"  # noqa: E501
            )
            sys.exit(0)
        else:
            print("Failed to install desktop shortcut.")
            sys.exit(1)

    # Enable high DPI scaling
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    app.setApplicationName("Janus-Core UX")
    app.setOrganizationName("STFC")

    # Set Application Icon
    icon_path = get_asset_path("icon.png")
    if not os.path.exists(icon_path):
        icon_path = get_asset_path("icon.svg")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
