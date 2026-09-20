"""Parsers for Janus Core outputs, trajectories, and statistics."""

from __future__ import annotations

import os
from typing import Any

from ase import Atoms
import ase.io
import numpy as np


def read_trajectory(filepath: str) -> list[Atoms]:
    """Read all frames from an ASE-compatible structure or trajectory file."""
    if not os.path.exists(filepath):
        return []
    try:
        return ase.io.read(filepath, index=":")
    except Exception as e:
        print(f"Error reading trajectory from {filepath}: {e}")
        try:
            return [ase.io.read(filepath)]
        except Exception:
            return []


def extract_trajectory_properties(traj: list[Atoms]) -> dict[str, dict[str, Any]]:
    """Extract standard properties (energy, forces, volume, step) for Chemiscope and plotting."""  # noqa: E501
    if not traj:
        return {}

    steps = list(range(len(traj)))
    energies = []
    max_forces = []
    volumes = []

    for _, atoms in enumerate(traj):
        # Potential energy
        e = None
        if "energy" in atoms.info:
            e = atoms.info["energy"]
        elif atoms.calc is not None:
            try:
                e = atoms.get_potential_energy()
            except Exception:
                pass
        energies.append(float(e) if e is not None else float("nan"))

        # Forces
        f_max = None
        if "forces" in atoms.arrays:
            f_max = np.linalg.norm(atoms.arrays["forces"], axis=1).max()
        elif atoms.calc is not None:
            try:
                f_max = np.linalg.norm(atoms.get_forces(), axis=1).max()
            except Exception:
                pass
        max_forces.append(float(f_max) if f_max is not None else float("nan"))

        # Volume
        try:
            vol = atoms.get_volume()
        except Exception:
            vol = float("nan")
        volumes.append(float(vol))

    props = {
        "Step": {
            "target": "structure",
            "values": steps,
            "units": "",
            "description": "Simulation or optimization step",
        }
    }

    if not all(np.isnan(energies)):
        props["Energy"] = {
            "target": "structure",
            "values": energies,
            "units": "eV",
            "description": "Potential energy",
        }

    if not all(np.isnan(max_forces)):
        props["Max Force"] = {
            "target": "structure",
            "values": max_forces,
            "units": "eV/Å",
            "description": "Maximum atomic force component",
        }

    if not all(np.isnan(volumes)):
        props["Volume"] = {
            "target": "structure",
            "values": volumes,
            "units": "Å³",
            "description": "Unit cell volume",
        }

    return props


def parse_md_stats(stats_path: str) -> dict[str, np.ndarray]:
    """Parse thermodynamic statistics from an MD stats file."""
    if not os.path.exists(stats_path):
        return {}

    try:
        data = np.genfromtxt(stats_path, names=True)
        if data.size == 0:
            return {}
        result = {}
        for name in data.dtype.names:
            result[name] = np.atleast_1d(data[name])
        return result
    except Exception as e:
        print(f"Error parsing MD stats from {stats_path}: {e}")
        return {}
