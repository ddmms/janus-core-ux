"""Tests for StructureInspector widget."""

from __future__ import annotations

import ase.build
from PySide6.QtWidgets import QApplication
import pytest

from janus_ux.widgets.structure_inspector import StructureInspector


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_structure_inspector_load(qapp):
    inspector = StructureInspector()
    atoms = ase.build.bulk("Si", "diamond", a=5.43)
    inspector.load_structure(atoms)

    assert "Si2" in inspector.lbl_formula.text()
    assert inspector.table.rowCount() == 2


def test_structure_inspector_filter(qapp):
    inspector = StructureInspector()
    atoms = ase.build.molecule("H2O")
    inspector.load_structure(atoms)
    assert inspector.table.rowCount() == 3

    inspector.input_filter.setText("O")
    assert inspector.table.rowCount() == 1

    inspector.input_filter.setText("H")
    assert inspector.table.rowCount() == 2
