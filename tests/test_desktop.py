"""Tests for desktop integration and assets."""

from __future__ import annotations

import os

from janus_ux.core.desktop_integration import get_asset_path, install_desktop_entry


def test_assets_exist():
    """Test Assets exist."""
    svg_path = get_asset_path("icon.svg")
    png_path = get_asset_path("icon.png")
    desktop_path = get_asset_path("janus-core-ux.desktop")

    assert os.path.exists(svg_path)
    assert os.path.exists(png_path)
    assert os.path.exists(desktop_path)


def test_install_desktop_entry():
    """Test Install desktop entry."""
    ok = install_desktop_entry()
    assert ok is True

    home = os.path.expanduser("~")
    target_desktop = os.path.join(
        home, ".local", "share", "applications", "janus-core-ux.desktop"
    )
    assert os.path.exists(target_desktop)
