"""Tests for trajectory, properties, and stats parsing."""

import os
import tempfile
import numpy as np
import pytest
import ase.build
import ase.io

from janus_ux.core.parser import (
    read_trajectory,
    extract_trajectory_properties,
    parse_md_stats,
)

def test_read_trajectory(tmp_path):
    atoms1 = ase.build.bulk("Cu", "fcc", a=3.6, cubic=True)
    atoms2 = ase.build.bulk("Cu", "fcc", a=3.7, cubic=True)
    traj_path = str(tmp_path / "test_traj.xyz")
    ase.io.write(traj_path, [atoms1, atoms2])

    loaded = read_trajectory(traj_path)
    assert len(loaded) == 2
    assert np.isclose(loaded[0].cell.lengths()[0], 3.6)
    assert np.isclose(loaded[1].cell.lengths()[0], 3.7)

def test_extract_trajectory_properties():
    atoms = ase.build.bulk("Si", "diamond", a=5.43)
    atoms.info["energy"] = -12.4
    atoms.arrays["forces"] = np.zeros((len(atoms), 3))

    props = extract_trajectory_properties([atoms])
    assert "Step" in props
    assert "Energy" in props
    assert props["Energy"]["values"] == [-12.4]
    assert "Max Force" in props
    assert props["Max Force"]["values"] == [0.0]
    assert "Volume" in props

def test_parse_md_stats(tmp_path):
    stats_file = tmp_path / "stats.dat"
    content = """# Time(ps)   Step   Temp(K)   Epot(eV)   Ekin(eV)   Etot(eV)
0.000000      0   300.000   -10.5000   0.450000   -10.0500
0.002000      2   302.150   -10.4800   0.453000   -10.0270
0.004000      4   298.500   -10.5100   0.448000   -10.0620
"""
    stats_file.write_text(content)
    parsed = parse_md_stats(str(stats_file))

    assert "TempK" in parsed or "temp" in [k.lower() for k in parsed]
    assert len(list(parsed.values())[0]) == 3
