"""Single Point Calculation Tab for computing energies, forces, stresses, and Hessians."""  # noqa: E501

from __future__ import annotations

from pathlib import Path
import tempfile

from ase import Atoms
import numpy as np
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
import yaml

from janus_ux.core.parser import args_to_yaml_dict, read_trajectory
from janus_ux.core.runner import CalcRunner
from janus_ux.widgets.calculator_selector import CalculatorSelector
from janus_ux.widgets.chemiscope_widget import ChemiscopeWidget
from janus_ux.widgets.log_console import LogConsole
from janus_ux.widgets.structure_file_input import StructureFileInput
from janus_ux.widgets.structure_inspector import StructureInspector


class SinglePointTab(QWidget):
    """Tab for static Single Point calculations."""

    def __init__(self, parent=None, calc_selector: CalculatorSelector | None = None):
        super().__init__(parent)
        self.is_standalone = calc_selector is None
        self.calc_selector = calc_selector or CalculatorSelector(self)
        self.current_atoms: Atoms | None = None
        self.result_atoms: Atoms | None = None
        self.runner: CalcRunner | None = None
        self.working_dir: Path | None = None
        self._last_args: list[str] = []

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        splitter = QSplitter(Qt.Horizontal)

        # LEFT PANE: Controls & Properties
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.setSpacing(10)

        # Structure File Input
        self.struct_input = StructureFileInput("Input Structure File", parent=self)
        self.struct_input.structure_loaded.connect(self._on_structure_loaded)
        self.struct_input.structure_cleared.connect(self._on_structure_cleared)
        self.input_file = self.struct_input.input_file
        left_layout.addWidget(self.struct_input)

        # Calculator (only shown if standalone)
        if self.is_standalone:
            left_layout.addWidget(self.calc_selector)

        # Properties to Calculate
        props_group = QGroupBox("Calculated Properties")
        pg_layout = QGridLayout(props_group)
        self.chk_energy = QCheckBox("Potential Energy")
        self.chk_energy.setChecked(True)
        self.chk_energy.setEnabled(False)  # Always calculated
        pg_layout.addWidget(self.chk_energy, 0, 0)

        self.chk_forces = QCheckBox("Atomic Forces")
        self.chk_forces.setChecked(True)
        pg_layout.addWidget(self.chk_forces, 0, 1)

        self.chk_stress = QCheckBox("Stress Tensor")
        self.chk_stress.setChecked(True)
        pg_layout.addWidget(self.chk_stress, 1, 0)

        self.chk_hessian = QCheckBox("Hessian Matrix")
        self.chk_hessian.setChecked(False)
        pg_layout.addWidget(self.chk_hessian, 1, 1)

        left_layout.addWidget(props_group)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_run = QPushButton("Run Single Point")
        self.btn_run.setStyleSheet(
            "background-color: #89b4fa; color: #11111b; font-weight: bold; padding: 10px;"  # noqa: E501
        )
        self.btn_run.clicked.connect(self.run_singlepoint)
        btn_layout.addWidget(self.btn_run)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_singlepoint)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save_config = QPushButton("💾 Save Config…")
        self.btn_save_config.setEnabled(False)
        self.btn_save_config.setToolTip(
            "Save the YAML config used for the last run "
            "(re-usable with janus singlepoint --config)."
        )
        self.btn_save_config.clicked.connect(self._save_config)
        btn_layout.addWidget(self.btn_save_config)

        left_layout.addLayout(btn_layout)
        left_layout.addStretch()

        splitter.addWidget(left_widget)

        # RIGHT PANE: Results, 3D Chemiscope, Forces Table, Logs
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(4, 4, 4, 4)
        right_layout.setSpacing(6)

        # Tabbed displays
        self.views_tabs = QTabWidget()

        # Tab 1: Chemiscope 3D
        self.chemiscope = ChemiscopeWidget(self, default_mode="structure")
        self.views_tabs.addTab(self.chemiscope, "3D Atomic Structure")

        # Tab 2: Results & Forces Table
        results_widget = QWidget()
        rw_layout = QVBoxLayout(results_widget)
        rw_layout.setContentsMargins(4, 4, 4, 4)
        rw_layout.setSpacing(6)

        # Summary cards
        cards_layout = QGridLayout()
        self.lbl_energy = QLabel("Energy: - eV")
        self.lbl_energy.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #a6e3a1;"
        )
        cards_layout.addWidget(self.lbl_energy, 0, 0)

        self.lbl_energy_per_atom = QLabel("Energy / Atom: - eV")
        cards_layout.addWidget(self.lbl_energy_per_atom, 0, 1)

        self.lbl_max_force = QLabel("Max Force: - eV/Å")
        self.lbl_max_force.setStyleSheet("font-weight: bold; color: #fab387;")
        cards_layout.addWidget(self.lbl_max_force, 1, 0)

        self.lbl_pressure = QLabel("Pressure: - GPa")
        cards_layout.addWidget(self.lbl_pressure, 1, 1)

        rw_layout.addLayout(cards_layout)

        # Forces table
        self.forces_table = QTableWidget()
        self.forces_table.setColumnCount(5)
        self.forces_table.setHorizontalHeaderLabels(
            ["Atom", "Symbol", "Fx (eV/Å)", "Fy (eV/Å)", "Fz (eV/Å)"]
        )
        self.forces_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        rw_layout.addWidget(self.forces_table, stretch=1)

        self.views_tabs.addTab(results_widget, "Results & Forces")

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

    def set_working_dir(self, path: Path) -> None:
        """Set the working directory for janus output files."""
        self.working_dir = path

    def _get_run_dir(self) -> str:
        if self.working_dir is not None:
            self.working_dir.mkdir(parents=True, exist_ok=True)
            return str(self.working_dir)
        return tempfile.mkdtemp(prefix="janus_sp_")

    def run_singlepoint(self):
        """Run singlepoint."""
        struct_file = self.struct_input.get_filepath()
        if not struct_file or not Path(struct_file).exists():
            QMessageBox.warning(
                self,
                "No Structure File",
                "Please upload or select an input structure file before running single point calculation.",  # noqa: E501
            )
            return

        run_dir = self._get_run_dir()
        file_prefix = str(Path(run_dir) / "singlepoint")
        out_file = f"{file_prefix}-results.extxyz"

        # Build CLI arguments
        args = [
            "--struct",
            struct_file,
            "--file-prefix",
            file_prefix,
            "--out",
            out_file,
        ]
        args.extend(self.calc_selector.get_cli_args())

        properties = ["energy"]
        if self.chk_forces.isChecked():
            properties.append("forces")
        if self.chk_stress.isChecked():
            properties.append("stress")
        if self.chk_hessian.isChecked():
            properties.append("hessian")

        for prop in properties:
            args.extend(["--properties", prop])

        expected = {"out_file": out_file}

        self._last_args = list(args)
        self.btn_run.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_save_config.setEnabled(False)
        self.log_console.clear()
        self.log_console.append_log("[INFO] Starting single-point calculation...")

        python_path = self.calc_selector.get_selected_python()
        self.runner = CalcRunner(
            "singlepoint",
            args,
            cwd=run_dir,
            expected_output_files=expected,
            python_path=python_path,
            parent=self,
        )
        self.runner.log_line.connect(self.log_console.append_log)
        self.runner.finished_calculation.connect(self._on_singlepoint_finished)
        self.runner.start()

    def cancel_singlepoint(self):
        """Cancel singlepoint."""
        if self.runner and self.runner.isRunning():
            self.runner.cancel()
            self.btn_cancel.setEnabled(False)

    @Slot(bool, str, dict)
    def _on_singlepoint_finished(self, success: bool, msg: str, outputs: dict):
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)

        if not success:
            return

        self.btn_save_config.setEnabled(True)

        out_file = outputs.get("out_file")
        if out_file and Path(out_file).exists():
            atoms_list = read_trajectory(out_file)
            if atoms_list:
                self.result_atoms = atoms_list[-1]
                self._display_results(self.result_atoms)

    def _display_results(self, atoms: Atoms):
        # Update 3D Chemiscope
        self.chemiscope.load_atoms(atoms)
        self.inspector.load_structure(atoms)

        # Energy
        energy = atoms.info.get("energy", None)
        if energy is None and hasattr(atoms, "calc") and atoms.calc is not None:
            energy = atoms.calc.results.get("energy", None)
        if energy is None:
            for k, v in atoms.info.items():
                if "energy" in k.lower() and isinstance(v, int | float):
                    energy = v
                    break

        if energy is not None:
            self.lbl_energy.setText(f"Energy: {energy:.5f} eV")
            self.lbl_energy_per_atom.setText(
                f"Energy / Atom: {energy / len(atoms):.5f} eV/atom"
            )

        # Forces
        forces = None
        for key in ["forces", "mace_forces", "mace_mp_forces"]:
            if key in atoms.arrays:
                forces = atoms.arrays[key]
                break
        if forces is None and hasattr(atoms, "calc") and atoms.calc is not None:
            forces = atoms.calc.results.get("forces", None)
        if forces is None:
            for k, v in atoms.arrays.items():
                if "forces" in k.lower():
                    forces = v
                    break

        if forces is not None:
            max_f = np.linalg.norm(forces, axis=1).max()
            self.lbl_max_force.setText(f"Max Force: {max_f:.5f} eV/Å")

            symbols = atoms.get_chemical_symbols()
            self.forces_table.setRowCount(len(forces))
            for i, (sym, f) in enumerate(zip(symbols, forces, strict=False)):
                self.forces_table.setItem(i, 0, QTableWidgetItem(str(i)))
                self.forces_table.setItem(i, 1, QTableWidgetItem(sym))
                self.forces_table.setItem(i, 2, QTableWidgetItem(f"{f[0]:.5f}"))
                self.forces_table.setItem(i, 3, QTableWidgetItem(f"{f[1]:.5f}"))
                self.forces_table.setItem(i, 4, QTableWidgetItem(f"{f[2]:.5f}"))

        # Stress & Pressure
        stress = atoms.info.get("stress", None)
        if stress is None and hasattr(atoms, "calc") and atoms.calc is not None:
            stress = atoms.calc.results.get("stress", None)
        if stress is None:
            for k, v in atoms.info.items():
                if "stress" in k.lower():
                    stress = v
                    break

        if stress is not None:
            # Hydrostatic pressure P = -1/3 Tr(stress) in GPa (ASE units eV/Å³ -> GPa * 160.217)  # noqa: E501
            try:
                if len(stress) == 6:
                    trace = (stress[0] + stress[1] + stress[2]) / 3.0
                elif len(stress) == 9:
                    trace = (stress[0] + stress[4] + stress[8]) / 3.0
                else:
                    trace = 0.0
                p_gpa = -trace * 160.21766208
                self.lbl_pressure.setText(f"Pressure: {p_gpa:.3f} GPa")
            except Exception:
                pass

        self.views_tabs.setCurrentIndex(1)  # switch to Results tab
        self.log_console.append_log(
            "[SUCCESS] Single point calculation results loaded."
        )

    def _save_config(self) -> None:
        """Save the YAML config used for the last run."""
        save_dir = str(self.working_dir) if self.working_dir else str(Path.home())
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Janus Config File",
            str(Path(save_dir) / "janus_singlepoint_config.yaml"),
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
