"""Tests for trajectory, properties, and stats parsing."""

from __future__ import annotations

import ase.build
import ase.io
import numpy as np

from janus_ux.core.parser import (
    args_to_yaml_dict,
    extract_trajectory_properties,
    parse_md_stats,
    read_trajectory,
)


def test_read_trajectory(tmp_path):
    """Test Read trajectory."""
    atoms1 = ase.build.bulk("Cu", "fcc", a=3.6, cubic=True)
    atoms2 = ase.build.bulk("Cu", "fcc", a=3.7, cubic=True)
    traj_path = str(tmp_path / "test_traj.xyz")
    ase.io.write(traj_path, [atoms1, atoms2])

    loaded = read_trajectory(traj_path)
    assert len(loaded) == 2
    assert np.isclose(loaded[0].cell.lengths()[0], 3.6)
    assert np.isclose(loaded[1].cell.lengths()[0], 3.7)


def test_extract_trajectory_properties():
    """Test Extract trajectory properties."""
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
    """Test Parse md stats."""
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


def test_args_to_yaml_dict_calc_kwargs():
    """Test args_to_yaml_dict properly converts calc_kwargs dict string to dict."""
    args = [
        "--arch",
        "mace_mp",
        "--device",
        "cpu",
        "--calc-kwargs",
        "{'dispersion': True, 'head': 'mpa0'}",
        "--no-tracker",
    ]
    cfg = args_to_yaml_dict(args)
    assert cfg["arch"] == "mace_mp"
    assert cfg["device"] == "cpu"
    assert isinstance(cfg["calc_kwargs"], dict)
    assert cfg["calc_kwargs"]["dispersion"] is True
    assert cfg["calc_kwargs"]["head"] == "mpa0"
    assert cfg["no_tracker"] is True
