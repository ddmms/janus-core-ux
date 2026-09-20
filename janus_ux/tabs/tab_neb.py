"""Nudged Elastic Band (NEB) Tab for transition state search and activation energy barriers."""  # noqa: E501

from __future__ import annotations

import os
import tempfile

from ase import Atoms
import ase.io
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from janus_ux.core.parser import extract_trajectory_properties, read_trajectory
from janus_ux.core.runner import CalcRunner
from janus_ux.widgets.calculator_selector import CalculatorSelector
from janus_ux.widgets.chemiscope_widget import ChemiscopeWidget
from janus_ux.widgets.interactive_graph import InteractiveGraph
from janus_ux.widgets.log_console import LogConsole
from janus_ux.widgets.structure_inspector import StructureInspector


class NEBTab(QWidget):
    """Tab for CI-NEB minimum energy path calculations and reaction barrier determination."""  # noqa: E501

    def __init__(self, parent=None, calc_selector: CalculatorSelector | None = None):
        super().__init__(parent)
        self.is_standalone = calc_selector is None
        self.calc_selector = calc_selector or CalculatorSelector(self)
        self.init_atoms: Atoms | None = None
        self.final_atoms: Atoms | None = None
        self.neb_images: list[Atoms] = []
        self.runner: CalcRunner | None = None
        self.temp_dir = tempfile.mkdtemp(prefix="janus_neb_")

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

        # Reactant & Product Files
        struct_group = QGroupBox("End-Point Structures")
        sg_layout = QGridLayout(struct_group)

        sg_layout.addWidget(QLabel("Initial (Reactant):"), 0, 0)
        init_box = QHBoxLayout()
        self.input_init = QLineEdit()
        self.input_init.setPlaceholderText("Path to initial structure")
        init_box.addWidget(self.input_init)
        self.btn_browse_init = QPushButton("Browse...")
        self.btn_browse_init.clicked.connect(self._browse_init)
        init_box.addWidget(self.btn_browse_init)
        sg_layout.addLayout(init_box, 0, 1)

        sg_layout.addWidget(QLabel("Final (Product):"), 1, 0)
        final_box = QHBoxLayout()
        self.input_final = QLineEdit()
        self.input_final.setPlaceholderText("Path to final structure")
        final_box.addWidget(self.input_final)
        self.btn_browse_final = QPushButton("Browse...")
        self.btn_browse_final.clicked.connect(self._browse_final)
        final_box.addWidget(self.btn_browse_final)
        sg_layout.addLayout(final_box, 1, 1)

        left_layout.addWidget(struct_group)

        # Calculator (only shown if standalone)
        if self.is_standalone:
            left_layout.addWidget(self.calc_selector)

        # NEB Parameters
        neb_group = QGroupBox("NEB Settings")
        ng_layout = QGridLayout(neb_group)

        ng_layout.addWidget(QLabel("Intermediate Images:"), 0, 0)
        self.spin_images = QSpinBox()
        self.spin_images.setRange(1, 30)
        self.spin_images.setValue(5)
        ng_layout.addWidget(self.spin_images, 0, 1)

        ng_layout.addWidget(QLabel("Optimizer:"), 1, 0)
        self.combo_optimizer = QComboBox()
        self.combo_optimizer.addItems(["FIRE", "MDMin", "LBFGS"])
        ng_layout.addWidget(self.combo_optimizer, 1, 1)

        ng_layout.addWidget(QLabel("Target fmax (eV/Å):"), 2, 0)
        self.spin_fmax = QDoubleSpinBox()
        self.spin_fmax.setRange(0.001, 1.0)
        self.spin_fmax.setValue(0.05)
        self.spin_fmax.setDecimals(3)
        ng_layout.addWidget(self.spin_fmax, 2, 1)

        ng_layout.addWidget(QLabel("Max Steps:"), 3, 0)
        self.spin_steps = QSpinBox()
        self.spin_steps.setRange(10, 5000)
        self.spin_steps.setValue(200)
        ng_layout.addWidget(self.spin_steps, 3, 1)

        self.chk_climb = QCheckBox("Climbing Image (CI-NEB)")
        self.chk_climb.setChecked(True)
        self.chk_climb.setToolTip(
            "Climbing image forces the highest energy replica to converge to the exact saddle point."  # noqa: E501
        )
        ng_layout.addWidget(self.chk_climb, 4, 0, 1, 2)

        left_layout.addWidget(neb_group)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_run = QPushButton("Run NEB Simulation")
        self.btn_run.setStyleSheet(
            "background-color: #89b4fa; color: #11111b; font-weight: bold; padding: 10px;"  # noqa: E501
        )
        self.btn_run.clicked.connect(self.run_neb)
        btn_layout.addWidget(self.btn_run)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_neb)
        btn_layout.addWidget(self.btn_cancel)

        left_layout.addLayout(btn_layout)
        left_layout.addStretch()

        splitter.addWidget(left_widget)

        # RIGHT PANE: Results, Visualizers, Logs
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(4, 4, 4, 4)
        right_layout.setSpacing(6)

        self.views_tabs = QTabWidget()

        # Tab 1: Chemiscope 3D Reaction Pathway
        self.chemiscope = ChemiscopeWidget(self)
        self.views_tabs.addTab(self.chemiscope, "3D Reaction Pathway (Chemiscope)")

        # Tab 2: Interactive MEP Curve
        self.graph_neb = InteractiveGraph(self, title="Minimum Energy Path (MEP)")
        self.graph_neb.point_clicked.connect(self._on_neb_point_clicked)
        self.views_tabs.addTab(
            self.graph_neb,
            "Energy Profile Along Reaction Coordinate (Click to View Image)",
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

    def _browse_init(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select Initial Structure File",
            "",
            "Structure Files (*.xyz *.cif *.poscar *.extxyz);;All Files (*)",
        )
        if filepath:
            self.input_init.setText(filepath)
            try:
                atoms = ase.io.read(filepath)
                self.init_atoms = atoms
                self.chemiscope.load_atoms(atoms)
                self.inspector.load_structure(atoms)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed reading structure: {e}")

    def _browse_final(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select Final Structure File",
            "",
            "Structure Files (*.xyz *.cif *.poscar *.extxyz);;All Files (*)",
        )
        if filepath:
            self.input_final.setText(filepath)
            try:
                self.final_atoms = ase.io.read(filepath)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed reading structure: {e}")

    @Slot(int)
    def _on_neb_point_clicked(self, index: int):
        if self.neb_images and 0 <= index < len(self.neb_images):
            self.chemiscope.select_frame(index)
            self.inspector.load_structure(self.neb_images[index])
            self.log_console.append_log(f"[INFO] Selected NEB image replica {index}")

    def run_neb(self):
        """Run neb."""
        init_file = self.input_init.text().strip()
        final_file = self.input_final.text().strip()
        if (
            not init_file
            or not os.path.exists(init_file)
            or not final_file
            or not os.path.exists(final_file)
        ):
            QMessageBox.warning(
                self,
                "Input Required",
                "Please specify valid initial and final structure files.",
            )
            return

        file_prefix = os.path.join(self.temp_dir, "neb")
        out_band = f"{file_prefix}-neb-band.extxyz"
        results_file = f"{file_prefix}-neb-results.dat"

        args = [
            "--init-struct",
            init_file,
            "--final-struct",
            final_file,
            "--file-prefix",
            file_prefix,
            "--n-images",
            str(self.spin_images.value()),
            "--fmax",
            str(self.spin_fmax.value()),
            "--steps",
            str(self.spin_steps.value()),
            "--write-band",
        ]
        if self.chk_climb.isChecked():
            args.extend(["--neb-kwargs", "{'climb': True}"])

        args.extend(self.calc_selector.get_cli_args())

        expected = {
            "band_file": out_band,
            "results_file": results_file,
        }

        self.btn_run.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.log_console.clear()
        self.log_console.append_log("[INFO] Running Nudged Elastic Band (NEB)...")

        python_path = self.calc_selector.get_selected_python()
        self.runner = CalcRunner(
            "neb",
            args,
            cwd=self.temp_dir,
            expected_output_files=expected,
            python_path=python_path,
            parent=self,
        )
        self.runner.log_line.connect(self.log_console.append_log)
        self.runner.finished_calculation.connect(self._on_neb_finished)
        self.runner.start()

    def cancel_neb(self):
        """Cancel neb."""
        if self.runner and self.runner.isRunning():
            self.runner.cancel()
            self.btn_cancel.setEnabled(False)

    @Slot(bool, str, dict)
    def _on_neb_finished(self, success: bool, msg: str, outputs: dict):
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)

        if not success:
            return

        file_prefix = os.path.join(self.temp_dir, "neb")
        candidates = [
            outputs.get("band_file"),
            f"{file_prefix}-neb-band.extxyz",
            f"{file_prefix}-neb-traj.xyz",
        ]
        found_band = next((f for f in candidates if f and os.path.exists(f)), None)

        if found_band:
            self.neb_images = read_trajectory(found_band)
            if self.neb_images:
                props = extract_trajectory_properties(self.neb_images)
                energies = props.get("Energy", {}).get("values", [])
                if energies:
                    # Normalize energy relative to reactant (E - E0)
                    e0 = energies[0]
                    rel_energies = [e - e0 for e in energies]
                    images_idx = list(range(len(self.neb_images)))

                    self.chemiscope.load_trajectory(self.neb_images, properties=props)
                    self.graph_neb.plot_curve(
                        x=images_idx,
                        y=rel_energies,
                        x_label="NEB Image Replica (0: Reactant, -1: Product)",
                        y_label="Relative Energy ΔE (eV)",
                        name="NEB Profile",
                        color="#f38ba8",
                    )
                    barrier = max(rel_energies)
                    self.log_console.append_log(
                        f"[SUCCESS] NEB calculation converged! Activation Energy Barrier: {barrier:.4f} eV"  # noqa: E501
                    )

        # Parse barrier results from results dat file
        results_file = outputs.get("results_file") or f"{file_prefix}-neb-results.dat"
        if os.path.exists(results_file):
            try:
                with open(results_file) as f:
                    lines = [
                        line.strip()
                        for line in f
                        if line.strip() and not line.startswith("#")
                    ]
                    if lines:
                        parts = lines[0].split()
                        if len(parts) >= 3:
                            barr, delta_e, max_f = (
                                float(parts[0]),
                                float(parts[1]),
                                float(parts[2]),
                            )
                            self.log_console.append_log(
                                f"[NEB RESULT] Activation Barrier: {barr:.4f} eV | ΔE: {delta_e:.4f} eV | Max Force: {max_f:.4f} eV/Å"  # noqa: E501
                            )
            except Exception:
                pass
