"""Tests for EnvironmentManager and EnvironmentsTab."""

from __future__ import annotations

from pathlib import Path
import sys

from PySide6.QtWidgets import QApplication
import pytest

from janus_ux.core.env_manager import MODEL_PACKAGE_MAP, EnvironmentManager
from janus_ux.tabs.tab_environments import EnvironmentsTab


@pytest.fixture(scope="session")
def qapp():
    """Provide qapp fixture."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_env_manager_discovery():
    """Test Env manager discovery."""
    mgr = EnvironmentManager()
    assert len(mgr.environments) > 0

    # Current python or janus should be found
    default_env = mgr.get_default_environment()
    assert default_env is not None
    assert Path(default_env.python_path).exists()


def test_env_manager_probe():
    """Test Env manager probe."""
    mgr = EnvironmentManager()
    current_py = sys.executable
    probe = mgr.probe_environment(current_py)

    assert "version" in probe
    assert "has_janus" in probe
    assert "packages" in probe
    assert "architectures" in probe


def test_environments_tab_ui(qapp):
    """Test Environments tab ui."""
    tab = EnvironmentsTab()
    assert tab.table_envs.rowCount() > 0
    assert tab.table_models.rowCount() == len(MODEL_PACKAGE_MAP)
