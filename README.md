# Janus-Core Desktop UX

A desktop graphical user interface for **STFC `janus-core`** built with **Qt6** and **PySide6**.

![Janus UX](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt6-blue.svg)
![Python](https://img.shields.io/badge/Python-3.12-brightgreen.svg)
![MLIP](https://img.shields.io/badge/MLIP-MACE%20%7C%20SevenNet%20%7C%20CHGNet-orange.svg)
![Visualization](https://img.shields.io/badge/3D%20Visualizer-Chemiscope-purple.svg)

---

## Features

- **Dedicated Tabs for All Janus-Core Calculations**:
  - ⚙️ **MLIP Environments & Potentials Setup**: Manage multiple micromamba/conda/virtual environments with incompatible dependencies. Auto-detect installed models (MACE, SevenNet, CHGNet, FairChem, NequIP, ORB, MatterSim), install/upgrade potentials directly via `uv`, and choose target execution environments per calculation.
  - ⚡ **Geometry Optimization**: Atomic coordinate relaxation and crystal unit cell optimization (`FrechetCellFilter`, `ExpCellFilter`), convergence curves, and trajectory playback.
  - 🎯 **Single Point**: Potential energy, atomic forces, stress tensor, and Hessian matrix.
  - 🌊 **Molecular Dynamics**: NVE, NVT, and NPT ensembles with Langevin or Nosé-Hoover thermostats, temperature ramping, thermodynamic curves (T, Epot, Pressure vs Time), and trajectory player.
  - 🎵 **Phonons**: Supercell generation, finite displacement, phonon band structures, DOS/PDOS, and vibrational heat capacity / entropy curves.
  - 📈 **Equation of State (EOS)**: Birch-Murnaghan, Murnaghan, and Vinet E(V) curve fitting, bulk modulus $B_0$, and interactive strained cell inspector.
  - 💎 **Elasticity**: Full $6 \times 6$ elastic stiffness matrix $C_{ij}$, compliance matrix $S_{ij}$, and Voigt-Reuss-Hill bulk, shear, and Young's moduli.
  - ⛰️ **NEB Reaction Pathways**: Climbing-image Nudged Elastic Band (CI-NEB) for transition state search and activation energy barriers $\Delta E^\ddagger$.
  - 🧬 **MLIP Descriptors**: Atomic and system-level MLIP representations and invariants.

- **Chemiscope 3D Atomistic Visualizer**:
  - Embedded via `QWebEngineView` using local offline Chemiscope JavaScript libraries.
  - Interactive camera rotation, zoom, panning, unit cell boundary toggling, atomic bonds, and measurement tools.
  - Trajectory playback and frame scrubber.

- **Interactive 2D/3D Linked Graphs with Point Picking**:
  - Click any point on a geometry optimization convergence curve, EOS $E(V)$ curve, or NEB reaction path to **immediately update the 3D Chemiscope visualizer to that specific structure/frame**.

- **Asynchronous Background Execution**:
  - Calculations run in background `QThread` workers without freezing the interface.
  - Live colorized terminal log streaming with search filtering.
  - Cancel button for long simulations.

---

## Installation & Environment

Install from PyPI or editable source using `uv`:

```bash
# Install with uv
uv pip install -e . --python /opt/micromamba/envs/janus/bin/python

# Or install desktop shortcut and system icon
janus-ux --install-desktop
```

---

## Launching the Application

Run directly from the command line using the installed entry point:

```bash
janus-ux
```

*(Legacy `janus-core-ux` is also supported as an alias)*

You can also launch it directly from your Linux system desktop application launcher (GNOME, KDE Plasma, XFCE).

---

## Desktop Shortcut & Icon

To register the desktop application shortcut and system icon to `~/.local/share/applications` and `~/.local/share/icons`:

- Run CLI flag: `janus-ux --install-desktop`
- Or from inside the GUI: Navigate to **Help -> Install Desktop Shortcut**.

---

## Running Tests

Run the test suite with `uv` and `pytest`:

```bash
uv run --no-project --python /opt/micromamba/envs/janus/bin/python -m pytest tests/
```
