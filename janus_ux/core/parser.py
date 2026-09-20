"""Parsers for Janus Core outputs, trajectories, and statistics."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ase import Atoms
import ase.io
import numpy as np


def read_trajectory(filepath: str | Path) -> list[Atoms]:
    """Read all frames from an ASE-compatible structure or trajectory file."""
    p = Path(filepath)
    if not p.exists():
        return []
    try:
        return ase.io.read(str(p), index=":")
    except Exception as e:
        print(f"Error reading trajectory from {filepath}: {e}")
        try:
            return [ase.io.read(str(p))]
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


def args_to_yaml_dict(args: list[str]) -> dict:
    """Convert a flat CLI args list into a YAML-compatible dict for janus --config.

    Pairs of ``--key value`` become ``{key: value}``; bare boolean flags
    (``--flag`` with no following value or a following ``--...``) become
    ``{flag: true}``.  Leading ``--`` is stripped and hyphens are replaced
    with underscores to match janus config expectations.

    Parameters
    ----------
    args
        List of CLI arguments, e.g. ``['--arch', 'mace_mp', '--write-traj']``.

    Returns
    -------
    dict
        Config dict suitable for ``yaml.dump``.
    """
    config: dict = {}
    i = 0
    while i < len(args):
        token = args[i]
        if token.startswith("--"):
            key = token[2:].replace("-", "_")
            # Check if next token is a value or another flag (or end of list)
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                value: str | bool | int | float = args[i + 1]
                try:
                    value = int(value)
                except ValueError:
                    try:
                        value = float(value)
                    except ValueError:
                        if isinstance(value, str):
                            if (
                                (value.startswith("{") and value.endswith("}"))
                                or (value.startswith("[") and value.endswith("]"))
                            ):
                                try:
                                    import ast

                                    parsed_val = ast.literal_eval(value)
                                    if isinstance(parsed_val, (dict, list)):
                                        value = parsed_val
                                except Exception:
                                    pass
                            elif value.lower() == "true":
                                value = True
                            elif value.lower() == "false":
                                value = False
                config[key] = value
                i += 2
            else:
                # Boolean flag
                config[key] = True
                i += 1
        else:
            i += 1
    return config


def parse_md_stats(stats_path: str | Path) -> dict[str, np.ndarray]:
    """Parse thermodynamic statistics from an MD stats file."""
    p = Path(stats_path)
    if not p.exists():
        return {}

    try:
        data = np.genfromtxt(str(p), names=True)
        if data.size == 0:
            return {}
        result = {}
        for name in data.dtype.names:
            result[name] = np.atleast_1d(data[name])
        return result
    except Exception as e:
        print(f"Error parsing MD stats from {stats_path}: {e}")
        return {}
