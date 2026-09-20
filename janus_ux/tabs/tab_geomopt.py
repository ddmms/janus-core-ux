"""Geometry Optimization Tab with interactive convergence curves and linked 3D Chemiscope viewer."""

import os
import tempfile
from typing import Optional, List
import numpy as np
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QSplitter,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QDoubleSpinBox,
    QSpinBox,
    QCheckBox,
    QFileDialog,
    QMessageBox,
    QTabWidget,
)
from PySide6.QtCore import Qt, Slot
from ase import Atoms
import ase.io

from janus_ux.core.runner import CalcRunner
from janus_ux.core.parser import read_trajectory, extract_trajectory_properties
from janus_ux.widgets.calculator_selector import CalculatorSelector
from janus_ux.widgets.chemiscope_widget import ChemiscopeWidget
from janus_ux.widgets.interactive_graph import InteractiveGraph
from janus_ux.widgets.structure_inspector import StructureInspector
from janus_ux.widgets.structure_file_input import StructureFileInput
from janus_ux.widgets.log_console import LogConsole

class GeomOptTab(QWidget):
    """Tab for Geometry Optimization and Cell Relaxation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_atoms: Optional[Atoms] = None
        self.traj_atoms: List[Atoms] = []
        self.runner: Optional[CalcRunner] = None
        self.temp_dir = tempfile.mkdtemp(prefix="janus_geomopt_")

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Left / Right Splitter
        splitter = QSplitter(Qt.Horizontal)

        # LEFT PANE: Controls & Parameters
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

        # Calculator Group
        self.calc_selector = CalculatorSelector(self)
        left_layout.addWidget(self.calc_selector)

        # Optimization Parameters Group
        opt_group = QGroupBox("Optimization Settings")
        og_layout = QGridLayout(opt_group)

        og_layout.addWidget(QLabel("Optimizer:"), 0, 0)
        self.combo_optimizer = QComboBox()
        self.combo_optimizer.addItems(["LBFGS", "BFGS", "FIRE"])
        og_layout.addWidget(self.combo_optimizer, 0, 1)

        og_layout.addWidget(QLabel("Target fmax (eV/Å):"), 1, 0)
        self.spin_fmax = QDoubleSpinBox()
        self.spin_fmax.setRange(0.0001, 1.0)
        self.spin_fmax.setValue(0.05)
        self.spin_fmax.setDecimals(4)
        self.spin_fmax.setSingleStep(0.01)
        og_layout.addWidget(self.spin_fmax, 1, 1)

        og_layout.addWidget(QLabel("Max Steps:"), 2, 0)
        self.spin_steps = QSpinBox()
        self.spin_steps.setRange(1, 10000)
        self.spin_steps.setValue(150)
        self.spin_steps.setSingleStep(25)
        og_layout.addWidget(self.spin_steps, 2, 1)

        # Cell Optimization & Filter (User rule: prefer FrechetCellFilter)
        og_layout.addWidget(QLabel("Cell Relaxation:"), 3, 0)
        self.combo_cell_opt = QComboBox()
        self.combo_cell_opt.addItems([
            "Positions Only (Fixed Cell)",
            "Optimize Cell Fully (Vectors + Angles)",
            "Optimize Cell Lengths Only",
        ])
        og_layout.addWidget(self.combo_cell_opt, 3, 1)

        og_layout.addWidget(QLabel("Cell Filter:"), 4, 0)
        self.combo_filter = QComboBox()
        self.combo_filter.addItems(["FrechetCellFilter", "ExpCellFilter", "UnitCellFilter"])
        self.combo_filter.setToolTip("FrechetCellFilter provides stable metric convergence for crystal optimizations.")
        og_layout.addWidget(self.combo_filter, 4, 1)

        self.chk_symmetrize = QCheckBox("Refine Spacegroup Symmetry")
        self.chk_symmetrize.setChecked(False)
        og_layout.addWidget(self.chk_symmetrize, 5, 0, 1, 2)

        self.chk_write_traj = QCheckBox("Save Full Trajectory")
        self.chk_write_traj.setChecked(True)
        og_layout.addWidget(self.chk_write_traj, 6, 0, 1, 2)

        left_layout.addWidget(opt_group)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_run = QPushButton("Run Optimization")
        self.btn_run.setProperty("class", "primary")
        self.btn_run.setStyleSheet("background-color: #89b4fa; color: #11111b; font-weight: bold; padding: 10px;")
        self.btn_run.clicked.connect(self.run_optimization)
        btn_layout.addWidget(self.btn_run)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_optimization)
        btn_layout.addWidget(self.btn_cancel)

        left_layout.addLayout(btn_layout)
        left_layout.addStretch()

        splitter.addWidget(left_widget)

        # RIGHT PANE: Visualizer, Graph, Inspector, and Logs
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(4, 4, 4, 4)
        right_layout.setSpacing(6)

        # Tabs for Visualization
        self.views_tabs = QTabWidget()

        # Tab 1: Chemiscope 3D & Linked Map
        self.chemiscope = ChemiscopeWidget(self)
        self.views_tabs.addTab(self.chemiscope, "3D Structure & Chemiscope Map")

        # Tab 2: Interactive Convergence Graph
        self.graph = InteractiveGraph(self, title="Optimization Convergence Curve")
        self.graph.point_clicked.connect(self._on_graph_point_clicked)
        self.views_tabs.addTab(self.graph, "Convergence Graph (Click to View Structure)")

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
        """Helper to load a structure file programmatically."""
        return self.struct_input.load_file(filepath)

    def _browse_structure(self):
        self.struct_input.browse_file()

    @Slot(int)
    def _on_graph_point_clicked(self, index: int):
        """When user clicks a point on the convergence plot, update Chemiscope to that structure."""
        if self.traj_atoms and 0 <= index < len(self.traj_atoms):
            self.chemiscope.select_frame(index)
            self.inspector.load_structure(self.traj_atoms[index])
            self.log_console.append_log(f"[INFO] Selected optimization step {index}")

    def run_optimization(self):
        """Prepare and run geometry optimization in background."""
        struct_file = self.struct_input.get_filepath()
        if not struct_file or not os.path.exists(struct_file):
            QMessageBox.warning(
                self,
                "No Structure File",
                "Please upload or select an input structure file before running geometry optimization."
            )
            return

        file_prefix = os.path.join(self.temp_dir, "geomopt")

        # Build CLI arguments
        args = ["--struct", struct_file, "--file-prefix", file_prefix]
        args.extend(self.calc_selector.get_cli_args())
        args.extend(["--fmax", str(self.spin_fmax.value())])
        args.extend(["--steps", str(self.spin_steps.value())])

        # Cell opt
        cell_opt_mode = self.combo_cell_opt.currentIndex()
        if cell_opt_mode == 1:
            args.append("--opt-cell-fully")
            args.extend(["--filter", self.combo_filter.currentText()])
        elif cell_opt_mode == 2:
            args.append("--opt-cell-lengths")
            args.extend(["--filter", self.combo_filter.currentText()])

        if self.chk_symmetrize.isChecked():
            args.append("--symmetrize")

        if self.chk_write_traj.isChecked():
            args.append("--write-traj")

        out_opt_file = f"{file_prefix}-opt.xyz"
        out_traj_file = f"{file_prefix}-opt-traj.xyz"

        expected = {
            "opt_file": out_opt_file,
            "traj_file": out_traj_file,
        }

        self.btn_run.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.log_console.clear()
        self.log_console.append_log("[INFO] Starting geometry optimization...")

        python_path = self.calc_selector.get_selected_python()
        self.runner = CalcRunner(
            "geomopt",
            args,
            cwd=self.temp_dir,
            expected_output_files=expected,
            python_path=python_path,
            parent=self,
        )
        self.runner.log_line.connect(self.log_console.append_log)
        self.runner.finished_calculation.connect(self._on_optimization_finished)
        self.runner.start()

    def cancel_optimization(self):
        if self.runner and self.runner.isRunning():
            self.runner.cancel()
            self.btn_cancel.setEnabled(False)

    @Slot(bool, str, dict)
    def _on_optimization_finished(self, success: bool, msg: str, outputs: dict):
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)

        if not success:
            return

        traj_file = outputs.get("traj_file")
        opt_file = outputs.get("opt_file")

        # Load trajectory
        if traj_file and os.path.exists(traj_file):
            self.traj_atoms = read_trajectory(traj_file)
        elif opt_file and os.path.exists(opt_file):
            self.traj_atoms = read_trajectory(opt_file)

        if self.traj_atoms:
            props = extract_trajectory_properties(self.traj_atoms)
            steps = list(range(len(self.traj_atoms)))
            energies = props.get("Energy", {}).get("values", [])
            max_forces = props.get("Max Force", {}).get("values", [])

            # Load into Chemiscope
            self.chemiscope.load_trajectory(self.traj_atoms, properties=props)

            # Load into Interactive Graph
            if energies:
                sec_y = {
                    "name": "Max Force",
                    "values": max_forces,
                    "color": "#f38ba8",
                    "label": "Max Force (eV/Å)",
                } if max_forces else None

                self.graph.plot_curve(
                    x=steps,
                    y=energies,
                    x_label="Optimization Step",
                    y_label="Energy (eV)",
                    name="Potential Energy",
                    color="#89b4fa",
                    secondary_y=sec_y,
                )

            # Update inspector with final structure
            self.inspector.load_structure(self.traj_atoms[-1])
            self.log_console.append_log(f"[SUCCESS] Loaded {len(self.traj_atoms)} frames from optimization trajectory.")
