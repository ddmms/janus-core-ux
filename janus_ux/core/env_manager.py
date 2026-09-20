"""Environment Manager for multi-MLIP environments support."""

import os
import sys
import json
import subprocess
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field

# Known MLIP models and their required Python packages
MODEL_PACKAGE_MAP = {
    "mace": {
        "name": "MACE (Atomic Cluster Expansion)",
        "package": "mace-torch",
        "import_name": "mace",
        "architectures": ["mace", "mace_mp", "mace_off", "mace_omol", "mace_polar"],
    },
    "sevennet": {
        "name": "SevenNet (Equivariant GNN)",
        "package": "sevenn",
        "import_name": "sevenn",
        "architectures": ["sevennet"],
    },
    "chgnet": {
        "name": "CHGNet (Crystal Hamiltonian Graph)",
        "package": "chgnet",
        "import_name": "chgnet",
        "architectures": ["chgnet"],
    },
    "fairchem": {
        "name": "FairChem (Open Catalyst Project)",
        "package": "fairchem-core",
        "import_name": "fairchem.core",
        "architectures": ["fairchem"],
    },
    "nequip": {
        "name": "NequIP / Allegro",
        "package": "nequip",
        "import_name": "nequip",
        "architectures": ["nequip"],
    },
    "orb": {
        "name": "ORB Models",
        "package": "orb-models",
        "import_name": "orb_models",
        "architectures": ["orb"],
    },
    "mattersim": {
        "name": "MatterSim",
        "package": "mattersim",
        "import_name": "mattersim",
        "architectures": ["mattersim"],
    },
}

@dataclass
class EnvConfig:
    name: str
    python_path: str
    bin_path: str = ""
    is_default: bool = False
    python_version: str = ""
    has_janus_core: bool = False
    installed_packages: Dict[str, bool] = field(default_factory=dict)
    supported_architectures: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EnvConfig":
        return cls(**d)

class EnvironmentManager:
    """Manages separate Python / Conda / Micromamba environments for incompatible MLIP potentials."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(EnvironmentManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self.config_dir = os.path.expanduser("~/.config/janus_ux")
        os.makedirs(self.config_dir, exist_ok=True)
        self.config_file = os.path.join(self.config_dir, "environments.json")

        self.environments: Dict[str, EnvConfig] = {}
        self.load_or_discover()

    def load_or_discover(self):
        """Load configured environments from file or perform auto-discovery."""
        loaded = self._load_from_file()
        if not loaded:
            self.auto_discover()
            self.save_to_file()

    def _load_from_file(self) -> bool:
        if not os.path.exists(self.config_file):
            return False
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.environments.clear()
            for item in data.get("environments", []):
                cfg = EnvConfig.from_dict(item)
                if os.path.exists(cfg.python_path):
                    self.environments[cfg.name] = cfg
            return len(self.environments) > 0
        except Exception as e:
            print(f"Error loading environments from {self.config_file}: {e}")
            return False

    def save_to_file(self):
        """Save current environments configuration to JSON."""
        try:
            data = {
                "environments": [env.to_dict() for env in self.environments.values()]
            }
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving environments configuration: {e}")

    def probe_environment(self, python_path: str) -> Dict[str, Any]:
        """Inspect a Python executable to check Python version, janus-core, and installed MLIP packages."""
        if not os.path.exists(python_path):
            return {
                "version": "Unknown",
                "has_janus": False,
                "packages": {},
                "architectures": [],
            }

        code = """
import sys, importlib.util, json

res = {
    "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    "has_janus": importlib.util.find_spec("janus_core") is not None,
    "packages": {}
}

probes = {
    "mace": "mace",
    "sevenn": "sevenn",
    "chgnet": "chgnet",
    "fairchem": "fairchem.core",
    "nequip": "nequip",
    "orb": "orb_models",
    "mattersim": "mattersim"
}

for k, mod in probes.items():
    try:
        res["packages"][k] = importlib.util.find_spec(mod) is not None
    except Exception:
        res["packages"][k] = False

print(json.dumps(res))
"""
        try:
            proc = subprocess.run([python_path, "-c", code], capture_output=True, text=True, timeout=10)
            if proc.returncode == 0:
                data = json.loads(proc.stdout.strip())
                archs = []
                for model_key, meta in MODEL_PACKAGE_MAP.items():
                    probe_key = "mace" if model_key == "mace" else ("sevenn" if model_key == "sevennet" else model_key)
                    if data["packages"].get(probe_key, False):
                        archs.extend(meta["architectures"])
                return {
                    "version": data["version"],
                    "has_janus": data["has_janus"],
                    "packages": data["packages"],
                    "architectures": archs,
                }
        except Exception as e:
            print(f"Error probing {python_path}: {e}")

        return {
            "version": "Unknown",
            "has_janus": False,
            "packages": {},
            "architectures": [],
        }

    def auto_discover(self):
        """Auto-detect micromamba, conda, and virtual environments on the system."""
        found_paths = []

        # 1. Active / current python
        current_py = sys.executable
        found_paths.append(("Current Python", current_py))

        # 2. Micromamba envs
        try:
            res = subprocess.run(["micromamba", "env", "list", "--json"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                for env_path in data.get("envs", []):
                    py_path = os.path.join(env_path, "bin", "python")
                    if os.path.exists(py_path):
                        env_name = os.path.basename(env_path)
                        found_paths.append((f"micromamba: {env_name}", py_path))
        except Exception:
            pass

        # 3. Standard /opt/micromamba/envs check
        if os.path.exists("/opt/micromamba/envs"):
            try:
                for entry in os.listdir("/opt/micromamba/envs"):
                    py_path = os.path.join("/opt/micromamba/envs", entry, "bin", "python")
                    if os.path.exists(py_path):
                        found_paths.append((f"micromamba: {entry}", py_path))
            except Exception:
                pass

        # De-duplicate by python_path
        seen_paths = set()
        for name, py_path in found_paths:
            norm_path = os.path.realpath(py_path)
            if norm_path in seen_paths:
                continue
            seen_paths.add(norm_path)

            probe = self.probe_environment(py_path)
            bin_dir = os.path.dirname(py_path)

            # Set 'janus' as default if found
            is_default = ("janus" in name.lower() and "bin/python" in py_path) or len(self.environments) == 0

            cfg = EnvConfig(
                name=name,
                python_path=py_path,
                bin_path=bin_dir,
                is_default=is_default,
                python_version=probe["version"],
                has_janus_core=probe["has_janus"],
                installed_packages=probe["packages"],
                supported_architectures=probe["architectures"],
            )
            self.environments[name] = cfg

        # Ensure at least one default
        if self.environments and not any(e.is_default for e in self.environments.values()):
            list(self.environments.values())[0].is_default = True

    def add_environment(self, name: str, python_path: str) -> EnvConfig:
        """Register a new environment."""
        probe = self.probe_environment(python_path)
        bin_dir = os.path.dirname(python_path)
        is_first = len(self.environments) == 0

        cfg = EnvConfig(
            name=name,
            python_path=python_path,
            bin_path=bin_dir,
            is_default=is_first,
            python_version=probe["version"],
            has_janus_core=probe["has_janus"],
            installed_packages=probe["packages"],
            supported_architectures=probe["architectures"],
        )
        self.environments[name] = cfg
        self.save_to_file()
        return cfg

    def remove_environment(self, name: str):
        if name in self.environments:
            was_default = self.environments[name].is_default
            del self.environments[name]
            if was_default and self.environments:
                list(self.environments.values())[0].is_default = True
            self.save_to_file()

    def set_default_environment(self, name: str):
        if name in self.environments:
            for k, env in self.environments.items():
                env.is_default = (k == name)
            self.save_to_file()

    def get_default_environment(self) -> Optional[EnvConfig]:
        for env in self.environments.values():
            if env.is_default:
                return env
        if self.environments:
            return list(self.environments.values())[0]
        return None

    def get_environment(self, name: str) -> Optional[EnvConfig]:
        return self.environments.get(name)

    def get_environments_for_arch(self, arch: str) -> List[EnvConfig]:
        """Find environments that contain the package for a specific MLIP architecture."""
        matching = []
        for env in self.environments.values():
            if arch in env.supported_architectures:
                matching.append(env)
        return matching
