"""Supported MLIP architectures and default foundational models for STFC janus-core."""

from typing import Dict, List

SUPPORTED_ARCHITECTURES: List[str] = [
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

DEFAULT_MODELS: Dict[str, str] = {
    "mace_mp": "medium",
    "mace": "small",
    "sevennet": "7net-0",
    "chgnet": "0.3.0",
    "mace_off": "small",
    "nequip": "",
    "orb": "orb-v2",
    "mattersim": "mattersim-v1.0.0-1M",
    "grace": "GRACE-2L-O3",
    "fairchem": "eqV2_31M_omat_mp_salex",
}
