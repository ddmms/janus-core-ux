"""Desktop entry and icon installation helper for Linux desktop integration."""

import os
import shutil
import subprocess
from pathlib import Path

def get_asset_path(filename: str) -> str:
    """Return path to an asset bundled in janus_ux/assets."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "assets", filename)

def install_desktop_entry() -> bool:
    """Install .desktop file and application icons to standard XDG directories."""
    home = Path.home()
    app_dir = home / ".local" / "share" / "applications"
    icon_scalable_dir = home / ".local" / "share" / "icons" / "hicolor" / "scalable" / "apps"
    icon_png_dir = home / ".local" / "share" / "icons" / "hicolor" / "256x256" / "apps"

    app_dir.mkdir(parents=True, exist_ok=True)
    icon_scalable_dir.mkdir(parents=True, exist_ok=True)
    icon_png_dir.mkdir(parents=True, exist_ok=True)

    svg_src = get_asset_path("icon.svg")
    png_src = get_asset_path("icon.png")
    desktop_src = get_asset_path("janus-core-ux.desktop")

    # 1. Copy icons
    if os.path.exists(svg_src):
        shutil.copy2(svg_src, icon_scalable_dir / "janus-core-ux.svg")
    if os.path.exists(png_src):
        shutil.copy2(png_src, icon_png_dir / "janus-core-ux.png")

    # 2. Prepare and copy .desktop file
    if os.path.exists(desktop_src):
        content = open(desktop_src, "r", encoding="utf-8").read()

        # Find executable path if possible
        which_bin = shutil.which("janus-core-ux")
        if which_bin:
            content = content.replace("Exec=janus-core-ux", f"Exec={which_bin}")

        target_desktop = app_dir / "janus-core-ux.desktop"
        with open(target_desktop, "w", encoding="utf-8") as f:
            f.write(content)

        # Make executable
        os.chmod(target_desktop, 0o755)

    # 3. Update desktop database if available
    try:
        subprocess.run(["update-desktop-database", str(app_dir)], check=False, capture_output=True)
    except Exception:
        pass

    return True
