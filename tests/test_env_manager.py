"""Tests for EnvironmentManager and EnvironmentsTab."""

import os
import sys
import pytest
from PySide6.QtWidgets import QApplication
from janus_ux.core.env_manager import EnvironmentManager, EnvConfig, MODEL_PACKAGE_MAP
from janus_ux.tabs.tab_environments import EnvironmentsTab

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

def test_env_manager_discovery():
    mgr = EnvironmentManager()
    assert len(mgr.environments) > 0

    # Current python or janus should be found
    default_env = mgr.get_default_environment()
    assert default_env is not None
    assert os.path.exists(default_env.python_path)

def test_env_manager_probe():
    mgr = EnvironmentManager()
    current_py = sys.executable
    probe = mgr.probe_environment(current_py)

    assert "version" in probe
    assert "has_janus" in probe
    assert "packages" in probe
    assert "architectures" in probe

def test_environments_tab_ui(qapp):
    tab = EnvironmentsTab()
    assert tab.table_envs.rowCount() > 0
    assert tab.table_models.rowCount() == len(MODEL_PACKAGE_MAP)
