"""Desktop entry and icon installation helper for Linux desktop integration."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess


def get_asset_path(filename: str) -> Path:
    """Return path to an asset bundled in janus_ux/assets."""
    base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "assets" / filename


def install_desktop_entry() -> bool:
    """Install .desktop file and application icons to standard XDG directories."""
    home = Path.home()
    app_dir = home / ".local" / "share" / "applications"
    icon_scalable_dir = (
        home / ".local" / "share" / "icons" / "hicolor" / "scalable" / "apps"
    )
    icon_png_dir = home / ".local" / "share" / "icons" / "hicolor" / "256x256" / "apps"

    app_dir.mkdir(parents=True, exist_ok=True)
    icon_scalable_dir.mkdir(parents=True, exist_ok=True)
    icon_png_dir.mkdir(parents=True, exist_ok=True)

    svg_src = get_asset_path("icon.svg")
    png_src = get_asset_path("icon.png")
    desktop_src = get_asset_path("janus-ux.desktop")

    # 1. Copy icons (for both janus-ux and legacy janus-core-ux)
    if svg_src.exists():
        shutil.copy2(svg_src, icon_scalable_dir / "janus-ux.svg")
        shutil.copy2(svg_src, icon_scalable_dir / "janus-core-ux.svg")
    if png_src.exists():
        shutil.copy2(png_src, icon_png_dir / "janus-ux.png")
        shutil.copy2(png_src, icon_png_dir / "janus-core-ux.png")

    # 2. Prepare and copy .desktop file
    if desktop_src.exists():
        content = desktop_src.read_text(encoding="utf-8")

        # Find executable path if possible
        which_bin = shutil.which("janus-ux") or shutil.which("janus-core-ux")
        if which_bin:
            content = content.replace("Exec=janus-ux", f"Exec={which_bin}")

        target_desktop = app_dir / "janus-ux.desktop"
        target_desktop.write_text(content, encoding="utf-8")

        # Make executable
        target_desktop.chmod(0o755)

    # 3. Update desktop database if available
    try:
        subprocess.run(
            ["update-desktop-database", str(app_dir)], check=False, capture_output=True
        )
    except Exception:
        pass

    return True
