"""Tests for presets and default structures."""

import pytest
from janus_ux.core.presets import get_preset_structures, SUPPORTED_ARCHITECTURES

def test_preset_structures():
    presets = get_preset_structures()
    assert "Silicon (Diamond)" in presets
    assert "Copper (FCC)" in presets
    assert "Water (H2O)" in presets

    si = presets["Silicon (Diamond)"]
    assert len(si) == 2
    assert si.pbc.all()

    cu = presets["Copper (FCC)"]
    assert len(cu) == 1
    assert cu.pbc.all()

def test_supported_architectures():
    assert "mace_mp" in SUPPORTED_ARCHITECTURES
    assert "sevennet" in SUPPORTED_ARCHITECTURES
    assert "chgnet" in SUPPORTED_ARCHITECTURES
