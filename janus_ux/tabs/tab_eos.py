"""Equation of State (EOS) Tab for computing E(V) curves, Bulk modulus, and strained cells."""  # noqa: E501

from __future__ import annotations

from pathlib import Path
import tempfile

from ase import Atoms
import numpy as np
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
import yaml

from janus_ux.core.parser import (
    args_to_yaml_dict,
    extract_trajectory_properties,
    read_trajectory,
)
from janus_ux.core.runner import CalcRunner
from janus_ux.widgets.calculator_selector import CalculatorSelector
from janus_ux.widgets.chemiscope_widget import ChemiscopeWidget
from janus_ux.widgets.interactive_graph import InteractiveGraph
from janus_ux.widgets.log_console import LogConsole
from janus_ux.widgets.structure_file_input import StructureFileInput
from janus_ux.widgets.structure_inspector import StructureInspector


class EOSTab(QWidget):
    """Tab for Equation of State calculations."""

    def __init__(self, parent=None, calc_selector: CalculatorSelector | None = None):
        super().__init__(parent)
        self.is_standalone = calc_selector is None
        self.calc_selector = calc_selector or CalculatorSelector(self)
        self.current_atoms: Atoms | None = None
        self.strained_atoms: list[Atoms] = []
        self.runner: CalcRunner | None = None
        self.working_dir: Path | None = None
        self._last_args: list[str] = []

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        splitter = QSplitter(Qt.Horizontal)

        # LEFT PANE: Controls
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.setSpacing(8)

        # Structure File Input
        self.struct_input = StructureFileInput(
            "Input Periodic Crystal File", require_periodic=True, parent=self
        )
        self.struct_input.structure_loaded.connect(self._on_structure_loaded)
        self.struct_input.structure_cleared.connect(self._on_structure_cleared)
        self.input_file = self.struct_input.input_file
        left_layout.addWidget(self.struct_input)

        # Calculator (only shown if standalone)
        if self.is_standalone:
            left_layout.addWidget(self.calc_selector)

        # EOS Parameters Group
        eos_group = QGroupBox("Equation of State Settings")
        eg_layout = QGridLayout(eos_group)

        eg_layout.addWidget(QLabel("Min Strain:"), 0, 0)
        self.spin_min_strain = QDoubleSpinBox()
        self.spin_min_strain.setRange(-0.3, 0.0)
        self.spin_min_strain.setValue(-0.05)
        self.spin_min_strain.setSingleStep(0.01)
        eg_layout.addWidget(self.spin_min_strain, 0, 1)

        eg_layout.addWidget(QLabel("Max Strain:"), 1, 0)
        self.spin_max_strain = QDoubleSpinBox()
        self.spin_max_strain.setRange(0.0, 0.3)
        self.spin_max_strain.setValue(0.05)
        self.spin_max_strain.setSingleStep(0.01)
        eg_layout.addWidget(self.spin_max_strain, 1, 1)

        eg_layout.addWidget(QLabel("Number of Points:"), 2, 0)
        self.spin_npoints = QSpinBox()
        self.spin_npoints.setRange(5, 50)
        self.spin_npoints.setValue(9)
        eg_layout.addWidget(self.spin_npoints, 2, 1)

        eg_layout.addWidget(QLabel("EOS Equation:"), 3, 0)
        self.combo_eos_type = QComboBox()
        self.combo_eos_type.addItems(["birchmurnaghan", "murnaghan", "vinet"])
        eg_layout.addWidget(self.combo_eos_type, 3, 1)

        left_layout.addWidget(eos_group)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_run = QPushButton("Calculate EOS")
        self.btn_run.setStyleSheet(
            "background-color: #89b4fa; color: #11111b; font-weight: bold; padding: 10px;"  # noqa: E501
        )
        self.btn_run.clicked.connect(self.run_eos)
        btn_layout.addWidget(self.btn_run)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_eos)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save_config = QPushButton("💾 Save Config…")
        self.btn_save_config.setEnabled(False)
        self.btn_save_config.setToolTip(
            "Save the YAML config used for the last run "
            "(re-usable with janus eos --config)."
        )
        self.btn_save_config.clicked.connect(self._save_config)
        btn_layout.addWidget(self.btn_save_config)

        left_layout.addLayout(btn_layout)
        left_layout.addStretch()

        splitter.addWidget(left_widget)

        # RIGHT PANE: Results, E(V) Graph, Chemiscope, Logs
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(4, 4, 4, 4)
        right_layout.setSpacing(6)

        self.views_tabs = QTabWidget()

        # Tab 1: Chemiscope 3D Strained Structure
        self.chemiscope = ChemiscopeWidget(self)
        self.views_tabs.addTab(self.chemiscope, "3D Strained Structure (Chemiscope)")

        # Tab 2: Interactive E(V) Graph
        self.graph_eos = InteractiveGraph(self, title="Energy vs Volume E(V) Curve")
        self.graph_eos.point_clicked.connect(self._on_volume_point_clicked)
        self.views_tabs.addTab(
            self.graph_eos, "E(V) Equation of State Curve (Click to View Structure)"
        )

        # Tab 3: Structure Inspector
        self.inspector = StructureInspector(self)
        self.views_tabs.addTab(self.inspector, "Crystallography & Coordinates")

        right_layout.addWidget(self.views_tabs, stretch=3)

        # Bottom Log Console
        self.log_console = LogConsole(self)
        self.log_console.setMaximumHeight(180)
        right_layout.addWidget(self.log_console, stretch=1)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        main_layout.addWidget(splitter)

    def _on_structure_loaded(self, atoms: Atoms, filepath: str):
        self.current_atoms = atoms
        self.inspector.load_structure(atoms)
        self.chemiscope.load_atoms(atoms)

    def _on_structure_cleared(self):
        self.current_atoms = None

    def load_structure_file(self, filepath: str) -> bool:
        """Load a structure file programmatically."""
        return self.struct_input.load_file(filepath)

    def _browse_structure(self):
        self.struct_input.browse_file()

    @Slot(int)
    def _on_volume_point_clicked(self, index: int):
        if self.strained_atoms and 0 <= index < len(self.strained_atoms):
            self.chemiscope.select_frame(index)
            self.inspector.load_structure(self.strained_atoms[index])
            self.log_console.append_log(
                f"[INFO] Selected strained volume frame {index}"
            )

    def set_working_dir(self, path: Path) -> None:
        """Set the working directory for janus output files."""
        self.working_dir = path

    def _get_run_dir(self) -> str:
        if self.working_dir is not None:
            self.working_dir.mkdir(parents=True, exist_ok=True)
            return str(self.working_dir)
        return tempfile.mkdtemp(prefix="janus_eos_")

    def run_eos(self):
        """Run eos."""
        struct_file = self.struct_input.get_filepath()
        if not struct_file or not Path(struct_file).exists():
            QMessageBox.warning(
                self,
                "No Structure File",
                "Please upload or select an input periodic crystal file before running Equation of State calculations.",  # noqa: E501
            )
            return

        run_dir = self._get_run_dir()
        file_prefix = str(Path(run_dir) / "eos")
        out_traj_file = f"{file_prefix}-generated.extxyz"
        raw_dat = f"{file_prefix}-eos-raw.dat"
        fit_dat = f"{file_prefix}-eos-fit.dat"

        # Determine min/max volume scale factor
        min_v = self.spin_min_strain.value()
        max_v = self.spin_max_strain.value()
        if min_v < 0:
            min_v = round(1.0 + min_v, 4)
        if max_v < 0.5:
            max_v = round(1.0 + max_v, 4)

        args = [
            "--struct",
            struct_file,
            "--file-prefix",
            file_prefix,
            "--min-volume",
            str(min_v),
            "--max-volume",
            str(max_v),
            "--n-volumes",
            str(self.spin_npoints.value()),
            "--eos-type",
            self.combo_eos_type.currentText(),
            "--write-structures",
        ]
        args.extend(self.calc_selector.get_cli_args())

        expected = {
            "traj_file": out_traj_file,
            "raw_dat": raw_dat,
            "fit_dat": fit_dat,
        }

        self._last_args = list(args)
        self.btn_run.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_save_config.setEnabled(False)
        self.log_console.clear()
        self.log_console.append_log("[INFO] Calculating Equation of State (EOS)...")

        python_path = self.calc_selector.get_selected_python()
        self.runner = CalcRunner(
            "eos",
            args,
            cwd=run_dir,
            expected_output_files=expected,
            python_path=python_path,
            parent=self,
        )
        self.runner.log_line.connect(self.log_console.append_log)
        self.runner.finished_calculation.connect(self._on_eos_finished)
        self.runner.start()

    def cancel_eos(self):
        """Cancel eos."""
        if self.runner and self.runner.isRunning():
            self.runner.cancel()
            self.btn_cancel.setEnabled(False)

    @Slot(bool, str, dict)
    def _on_eos_finished(self, success: bool, msg: str, outputs: dict):
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)

        if not success:
            return

        self.btn_save_config.setEnabled(True)

        run_dir = self._get_run_dir()
        file_prefix = str(Path(run_dir) / "eos")
        candidates = [
            outputs.get("traj_file"),
            f"{file_prefix}-generated.extxyz",
            f"{file_prefix}-eos.xyz",
        ]
        found_traj = next((f for f in candidates if f and Path(f).exists()), None)

        if found_traj:
            self.strained_atoms = read_trajectory(found_traj)
            if self.strained_atoms:
                props = extract_trajectory_properties(self.strained_atoms)
                vols = props.get("Volume", {}).get("values", [])
                energies = props.get("Energy", {}).get("values", [])

                # Load into Chemiscope
                settings = {
                    "map": {"x": {"property": "Volume"}, "y": {"property": "Energy"}},
                    "structure": [{"unitCell": True, "bonds": True}],
                }
                self.chemiscope.load_trajectory(
                    self.strained_atoms, properties=props, settings=settings
                )

                # Plot E(V) curve
                if vols and energies:
                    # Sort by volume
                    sorted_indices = np.argsort(vols)
                    vols_sorted = [vols[i] for i in sorted_indices]
                    energies_sorted = [energies[i] for i in sorted_indices]

                    self.graph_eos.plot_curve(
                        x=vols_sorted,
                        y=energies_sorted,
                        x_label="Unit Cell Volume (Å³)",
                        y_label="Energy (eV)",
                        name="E(V) Strain Points",
                        color="#89b4fa",
                    )
                self.log_console.append_log(
                    f"[SUCCESS] Calculated EOS across {len(self.strained_atoms)} strained unit cells."  # noqa: E501
                )

        # Also display fit results if available
        fit_dat = outputs.get("fit_dat") or f"{file_prefix}-eos-fit.dat"
        if Path(fit_dat).exists():
            try:
                with open(fit_dat) as f:
                    lines = [
                        line.strip()
                        for line in f
                        if line.strip() and not line.startswith("#")
                    ]
                    if lines:
                        parts = lines[0].split()
                        if len(parts) >= 3:
                            b0, e0, v0 = (
                                float(parts[0]),
                                float(parts[1]),
                                float(parts[2]),
                            )
                            self.log_console.append_log(
                                f"[EOS FIT] B0: {b0:.2f} GPa | E0: {e0:.4f} eV | V0: {v0:.2f} Å³"  # noqa: E501
                            )
            except Exception:
                pass

    def _save_config(self) -> None:
        """Save the YAML config used for the last run."""
        save_dir = str(self.working_dir) if self.working_dir else str(Path.home())
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Janus Config File",
            str(Path(save_dir) / "janus_eos_config.yaml"),
            "YAML Config Files (*.yaml *.yml);;All Files (*)",
        )
        if not path:
            return
        config = args_to_yaml_dict(self._last_args)
        try:
            with open(path, "w", encoding="utf-8") as fh:
                yaml.dump(config, fh, default_flow_style=False, sort_keys=False)
            self.log_console.append_log(f"[INFO] Config saved to: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save config:\n{e}")
