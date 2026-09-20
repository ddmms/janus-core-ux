"""Tests for desktop integration and assets."""

from __future__ import annotations

from pathlib import Path

from janus_ux.core.desktop_integration import get_asset_path, install_desktop_entry


def test_assets_exist():
    """Test Assets exist."""
    svg_path = get_asset_path("icon.svg")
    png_path = get_asset_path("icon.png")
    desktop_path = get_asset_path("janus-ux.desktop")

    assert svg_path.exists()
    assert png_path.exists()
    assert desktop_path.exists()


def test_install_desktop_entry():
    """Test Install desktop entry."""
    ok = install_desktop_entry()
    assert ok is True

    target_desktop = (
        Path.home() / ".local" / "share" / "applications" / "janus-ux.desktop"
    )
    assert target_desktop.exists()
