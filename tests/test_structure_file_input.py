"""Tests for StructureFileInput and MLIP model architectures."""

import pytest
from ase import Atoms
import ase.io
from janus_ux.core.models import SUPPORTED_ARCHITECTURES, DEFAULT_MODELS
from janus_ux.widgets.structure_file_input import StructureFileInput

def test_supported_architectures():
    assert "mace_mp" in SUPPORTED_ARCHITECTURES
    assert "sevennet" in SUPPORTED_ARCHITECTURES
    assert "chgnet" in SUPPORTED_ARCHITECTURES
    assert "fairchem" in SUPPORTED_ARCHITECTURES
    assert len(SUPPORTED_ARCHITECTURES) >= 8

def test_default_models():
    assert "mace_mp" in DEFAULT_MODELS
    assert DEFAULT_MODELS["sevennet"] == "7net-0"

def test_structure_file_input(qapp, tmp_path):
    struct_widget = StructureFileInput("Test Structure", require_periodic=True)
    assert struct_widget.get_atoms() is None
    assert struct_widget.get_filepath() == ""

    # Create dummy structure
    atoms = Atoms("Si2", positions=[[0, 0, 0], [1.36, 1.36, 1.36]], cell=[5.43, 5.43, 5.43], pbc=True)
    test_file = tmp_path / "si.xyz"
    ase.io.write(str(test_file), atoms)

    loaded_signals = []
    struct_widget.structure_loaded.connect(lambda at, path: loaded_signals.append((at, path)))

    ok = struct_widget.load_file(str(test_file))
    assert ok is True
    assert struct_widget.get_atoms() is not None
    assert len(struct_widget.get_atoms()) == 2
    assert struct_widget.get_filepath() == str(test_file)
    assert len(loaded_signals) == 1

    # Clear
    struct_widget.clear()
    assert struct_widget.get_atoms() is None
    assert struct_widget.get_filepath() == ""
