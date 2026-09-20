"""Tests for Chemiscope dataset formatting and widget functionality."""

from __future__ import annotations

import ase.build
from PySide6.QtWidgets import QApplication
import pytest

from janus_ux.core.parser import extract_trajectory_properties
from janus_ux.widgets.chemiscope_widget import ChemiscopeWidget


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_extract_properties():
    atoms1 = ase.build.bulk("Si", "diamond", a=5.43)
    atoms1.info["energy"] = -10.5
    atoms2 = atoms1.copy()
    atoms2.info["energy"] = -10.2

    traj = [atoms1, atoms2]
    props = extract_trajectory_properties(traj)

    assert "Step" in props
    assert props["Step"]["values"] == [0, 1]
    assert "Energy" in props
    assert props["Energy"]["values"] == [-10.5, -10.2]
    assert "Volume" in props


def test_chemiscope_widget_init(qapp):
    widget = ChemiscopeWidget()
    assert widget.web_view is not None

    atoms = ase.build.bulk("Cu", "fcc", a=3.61)
    widget.load_atoms(atoms)
    assert len(widget.current_structures) == 1
