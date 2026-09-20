"""Elasticity Tab for calculating the 6x6 stiffness tensor C_ij, compliance, and elastic moduli."""  # noqa: E501

from __future__ import annotations

from pathlib import Path
import tempfile

import yaml

from ase import Atoms
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from janus_ux.core.parser import args_to_yaml_dict, read_trajectory
from janus_ux.core.runner import CalcRunner
from janus_ux.widgets.calculator_selector import CalculatorSelector
from janus_ux.widgets.chemiscope_widget import ChemiscopeWidget
from janus_ux.widgets.log_console import LogConsole
from janus_ux.widgets.structure_file_input import StructureFileInput
from janus_ux.widgets.structure_inspector import StructureInspector


class ElasticityTab(QWidget):
    """Tab for full 6x6 elasticity stiffness matrix and moduli calculation."""

    def __init__(self, parent=None, calc_selector: CalculatorSelector | None = None):
        super().__init__(parent)
        self.is_standalone = calc_selector is None
        self.calc_selector = calc_selector or CalculatorSelector(self)
        self.current_atoms: Atoms | None = None
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

        # Elasticity Settings
        elast_group = QGroupBox("Strain Settings")
        eg_layout = QGridLayout(elast_group)

        eg_layout.addWidget(QLabel("Strain Magnitude:"), 0, 0)
        self.spin_strain = QDoubleSpinBox()
        self.spin_strain.setRange(0.001, 0.1)
        self.spin_strain.setValue(0.01)
        self.spin_strain.setDecimals(4)
        self.spin_strain.setSingleStep(0.002)
        eg_layout.addWidget(self.spin_strain, 0, 1)

        eg_layout.addWidget(QLabel("Number of Points:"), 1, 0)
        self.spin_npoints = QSpinBox()
        self.spin_npoints.setRange(3, 21)
        self.spin_npoints.setValue(5)
        eg_layout.addWidget(self.spin_npoints, 1, 1)

        left_layout.addWidget(elast_group)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_run = QPushButton("Calculate Elasticity")
        self.btn_run.setStyleSheet(
            "background-color: #89b4fa; color: #11111b; font-weight: bold; padding: 10px;"  # noqa: E501
        )
        self.btn_run.clicked.connect(self.run_elasticity)
        btn_layout.addWidget(self.btn_run)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_elasticity)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save_config = QPushButton("💾 Save Config…")
        self.btn_save_config.setEnabled(False)
        self.btn_save_config.setToolTip(
            "Save the YAML config used for the last run (re-usable with janus elasticity --config)."
        )
        self.btn_save_config.clicked.connect(self._save_config)
        btn_layout.addWidget(self.btn_save_config)

        left_layout.addLayout(btn_layout)
        left_layout.addStretch()

        splitter.addWidget(left_widget)

        # RIGHT PANE: Stiffness Matrix C_ij, Moduli, Chemiscope, Logs
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(4, 4, 4, 4)
        right_layout.setSpacing(6)

        self.views_tabs = QTabWidget()

        # Tab 1: Elastic Moduli & C_ij Matrix
        results_widget = QWidget()
        rw_layout = QVBoxLayout(results_widget)
        rw_layout.setContentsMargins(4, 4, 4, 4)
        rw_layout.setSpacing(8)

        # Moduli Summary Cards
        moduli_group = QGroupBox("Mechanical Moduli (Voigt-Reuss-Hill)")
        mg_layout = QGridLayout(moduli_group)
        self.lbl_bulk = QLabel("Bulk Modulus (VRH): - GPa")
        self.lbl_bulk.setStyleSheet("font-weight: bold; color: #a6e3a1;")
        mg_layout.addWidget(self.lbl_bulk, 0, 0)

        self.lbl_shear = QLabel("Shear Modulus (VRH): - GPa")
        self.lbl_shear.setStyleSheet("font-weight: bold; color: #89b4fa;")
        mg_layout.addWidget(self.lbl_shear, 0, 1)

        self.lbl_young = QLabel("Young's Modulus: - GPa")
        self.lbl_young.setStyleSheet("font-weight: bold; color: #b4befe;")
        mg_layout.addWidget(self.lbl_young, 1, 0)

        self.lbl_poisson = QLabel("Poisson's Ratio (ν): -")
        self.lbl_poisson.setStyleSheet("font-weight: bold; color: #fab387;")
        mg_layout.addWidget(self.lbl_poisson, 1, 1)

        rw_layout.addWidget(moduli_group)

        # 6x6 C_ij Matrix Table
        matrix_group = QGroupBox("Elastic Stiffness Tensor C_ij (GPa)")
        m_layout = QVBoxLayout(matrix_group)
        self.table_cij = QTableWidget(6, 6)
        headers = ["C_1j", "C_2j", "C_3j", "C_4j", "C_5j", "C_6j"]
        self.table_cij.setHorizontalHeaderLabels(headers)
        self.table_cij.setVerticalHeaderLabels(
            ["C_i1", "C_i2", "C_i3", "C_i4", "C_i5", "C_i6"]
        )
        self.table_cij.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        m_layout.addWidget(self.table_cij)
        rw_layout.addWidget(matrix_group, stretch=1)

        self.views_tabs.addTab(results_widget, "Elastic Stiffness & Moduli")

        # Tab 2: Chemiscope 3D
        self.chemiscope = ChemiscopeWidget(self, default_mode="structure")
        self.views_tabs.addTab(self.chemiscope, "3D Crystal Structure")

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
        return tempfile.mkdtemp(prefix="janus_elast_")

    def run_elasticity(self):
        """Run elasticity."""
        struct_file = self.struct_input.get_filepath()
        if not struct_file or not Path(struct_file).exists():
            QMessageBox.warning(
                self,
                "No Structure File",
                "Please upload or select an input periodic crystal file before running elasticity calculations.",  # noqa: E501
            )
            return

        run_dir = self._get_run_dir()
        file_prefix = str(Path(run_dir) / "elasticity")
        tensor_file = f"{file_prefix}-elastic_tensor.dat"

        args = [
            "--struct",
            struct_file,
            "--file-prefix",
            file_prefix,
            "--shear-magnitude",
            str(self.spin_strain.value()),
            "--normal-magnitude",
            str(self.spin_strain.value()),
            "--n-strains",
            str(self.spin_npoints.value()),
            "--write-structures",
        ]
        args.extend(self.calc_selector.get_cli_args())

        expected = {"tensor_file": tensor_file}

        self._last_args = list(args)
        self.btn_run.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_save_config.setEnabled(False)
        self.log_console.clear()
        self.log_console.append_log(
            "[INFO] Calculating Elastic Stiffness Tensor C_ij..."
        )

        python_path = self.calc_selector.get_selected_python()
        self.runner = CalcRunner(
            "elasticity",
            args,
            cwd=run_dir,
            expected_output_files=expected,
            python_path=python_path,
            parent=self,
        )
        self.runner.log_line.connect(self._parse_live_log)
        self.runner.finished_calculation.connect(self._on_elasticity_finished)
        self.runner.start()

    def _parse_live_log(self, text: str):
        self.log_console.append_log(text)

    def cancel_elasticity(self):
        """Cancel elasticity."""
        if self.runner and self.runner.isRunning():
            self.runner.cancel()
            self.btn_cancel.setEnabled(False)

    @Slot(bool, str, dict)
    def _on_elasticity_finished(self, success: bool, msg: str, outputs: dict):
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        if not success:
            return

        self.btn_save_config.setEnabled(True)

        run_dir = self._get_run_dir()
        file_prefix = str(Path(run_dir) / "elasticity")
        tensor_file = outputs.get("tensor_file") or f"{file_prefix}-elastic_tensor.dat"
        if Path(tensor_file).exists():
            try:
                with open(tensor_file) as f:
                    lines = [
                        line.strip()
                        for line in f
                        if line.strip() and not line.startswith("#")
                    ]
                    if lines:
                        vals = [float(x) for x in lines[0].split()]
                        if len(vals) >= 9:
                            b_vrh = vals[2]
                            s_vrh = vals[5]
                            young = vals[6]
                            poisson = vals[8]
                            self.lbl_bulk.setText(f"Bulk Modulus: {b_vrh:.2f} GPa")
                            self.lbl_shear.setText(f"Shear Modulus: {s_vrh:.2f} GPa")
                            self.lbl_young.setText(f"Young's Modulus: {young:.2f} GPa")
                            self.lbl_poisson.setText(f"Poisson's Ratio: {poisson:.3f}")

                        if len(vals) >= 45:
                            cij_vals = vals[9:45]
                            from PySide6.QtWidgets import QTableWidgetItem

                            for r in range(6):
                                for c in range(6):
                                    v = cij_vals[r * 6 + c]
                                    self.table_cij.setItem(
                                        r, c, QTableWidgetItem(f"{v:.2f}")
                                    )
            except Exception as e:
                self.log_console.append_log(f"[WARN] Failed parsing tensor file: {e}")

        # If structures were generated, load into Chemiscope
        gen_file = f"{file_prefix}-elasticity-generated.extxyz"
        if Path(gen_file).exists():
            atoms_list = read_trajectory(gen_file)
            if atoms_list:
                self.chemiscope.load_trajectory(atoms_list)

        self.log_console.append_log("[SUCCESS] Elasticity calculation complete.")

    def _save_config(self) -> None:
        """Save the YAML config used for the last run."""
        save_dir = str(self.working_dir) if self.working_dir else str(Path.home())
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Janus Config File",
            str(Path(save_dir) / "janus_elasticity_config.yaml"),
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
