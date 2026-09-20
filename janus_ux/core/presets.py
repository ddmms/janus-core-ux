"""Preset benchmark structures and calculators for quick testing."""

from typing import Dict, List
import ase.build
from ase import Atoms

def get_preset_structures() -> Dict[str, Atoms]:
    """Return a dictionary of built-in atomic structures for testing and demonstration."""
    structures = {}

    # 1. Silicon Diamond
    si = ase.build.bulk("Si", "diamond", a=5.43)
    si.info["name"] = "Silicon (Diamond)"
    structures["Silicon (Diamond)"] = si

    # 2. Copper FCC
    cu = ase.build.bulk("Cu", "fcc", a=3.61)
    cu.info["name"] = "Copper (FCC)"
    structures["Copper (FCC)"] = cu

    # 3. Water Molecule
    h2o = ase.build.molecule("H2O")
    h2o.center(vacuum=5.0)
    h2o.info["name"] = "Water (H2O)"
    structures["Water (H2O)"] = h2o

    # 4. Strontium Titanate Perovskite (SrTiO3)
    try:
        srtio3 = ase.build.bulk("SrTiO3", "perovskite", a=3.905)
        srtio3.info["name"] = "SrTiO3 Perovskite"
        structures["SrTiO3 Perovskite"] = srtio3
    except Exception:
        pass

    # 5. Graphene 2D monolayer
    try:
        graphene = ase.build.graphene(a=2.46, size=(2, 2, 1), vacuum=10.0)
        graphene.info["name"] = "Graphene monolayer"
        structures["Graphene"] = graphene
    except Exception:
        pass

    # 6. Gold FCC 2x2x2 Supercell
    au = ase.build.bulk("Au", "fcc", a=4.08) * (2, 2, 2)
    au.info["name"] = "Gold (FCC 2x2x2)"
    structures["Gold (2x2x2)"] = au

    return structures

SUPPORTED_ARCHITECTURES = [
    "mace_mp",
    "mace",
    "sevennet",
    "chgnet",
    "mace_off",
    "nequip",
    "orb",
    "mattersim",
    "grace",
    "fairchem",
]

DEFAULT_MODELS = {
    "mace_mp": "small",
    "sevennet": "7net-0",
    "chgnet": "default",
    "mace_off": "small",
}
