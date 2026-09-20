"""Phonons Tab for calculating phonon dispersions, density of states (DOS), and thermal properties."""  # noqa: E501

from __future__ import annotations

import os
import tempfile

from ase import Atoms
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
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

from janus_ux.core.runner import CalcRunner
from janus_ux.widgets.calculator_selector import CalculatorSelector
from janus_ux.widgets.chemiscope_widget import ChemiscopeWidget
from janus_ux.widgets.interactive_graph import InteractiveGraph
from janus_ux.widgets.log_console import LogConsole
from janus_ux.widgets.structure_file_input import StructureFileInput
from janus_ux.widgets.structure_inspector import StructureInspector


class PhononsTab(QWidget):
    """Tab for Phonon calculations and vibrational thermodynamics."""

    def __init__(self, parent=None, calc_selector: CalculatorSelector | None = None):
        super().__init__(parent)
        self.is_standalone = calc_selector is None
        self.calc_selector = calc_selector or CalculatorSelector(self)
        self.current_atoms: Atoms | None = None
        self.runner: CalcRunner | None = None
        self.temp_dir = tempfile.mkdtemp(prefix="janus_phonons_")

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
            "Input Periodic Structure File", require_periodic=True, parent=self
        )
        self.struct_input.structure_loaded.connect(self._on_structure_loaded)
        self.struct_input.structure_cleared.connect(self._on_structure_cleared)
        self.input_file = self.struct_input.input_file
        left_layout.addWidget(self.struct_input)

        # Calculator (only shown if standalone)
        if self.is_standalone:
            left_layout.addWidget(self.calc_selector)

        # Phonons Settings
        ph_group = QGroupBox("Phonon & Supercell Settings")
        pg_layout = QGridLayout(ph_group)

        pg_layout.addWidget(QLabel("Supercell:"), 0, 0)
        sc_layout = QHBoxLayout()
        self.sc_x = QSpinBox()
        self.sc_x.setRange(1, 10)
        self.sc_x.setValue(2)
        self.sc_y = QSpinBox()
        self.sc_y.setRange(1, 10)
        self.sc_y.setValue(2)
        self.sc_z = QSpinBox()
        self.sc_z.setRange(1, 10)
        self.sc_z.setValue(2)
        sc_layout.addWidget(self.sc_x)
        sc_layout.addWidget(self.sc_y)
        sc_layout.addWidget(self.sc_z)
        pg_layout.addLayout(sc_layout, 0, 1)

        pg_layout.addWidget(QLabel("Displacement (Å):"), 1, 0)
        self.spin_displacement = QDoubleSpinBox()
        self.spin_displacement.setRange(0.001, 0.1)
        self.spin_displacement.setValue(0.01)
        self.spin_displacement.setDecimals(3)
        pg_layout.addWidget(self.spin_displacement, 1, 1)

        self.chk_dos = QCheckBox("Calculate Density of States (DOS)")
        self.chk_dos.setChecked(True)
        pg_layout.addWidget(self.chk_dos, 2, 0, 1, 2)

        self.chk_thermal = QCheckBox(
            "Calculate Thermal Properties (Cv, Entropy, Free Energy)"
        )
        self.chk_thermal.setChecked(True)
        pg_layout.addWidget(self.chk_thermal, 3, 0, 1, 2)

        left_layout.addWidget(ph_group)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_run = QPushButton("Calculate Phonons")
        self.btn_run.setStyleSheet(
            "background-color: #89b4fa; color: #11111b; font-weight: bold; padding: 10px;"  # noqa: E501
        )
        self.btn_run.clicked.connect(self.run_phonons)
        btn_layout.addWidget(self.btn_run)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_phonons)
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

        # Tab 1: Chemiscope 3D
        self.chemiscope = ChemiscopeWidget(self, default_mode="structure")
        self.views_tabs.addTab(self.chemiscope, "3D Crystal Structure (Chemiscope)")

        # Tab 2: Phonon Dispersion & DOS Graph
        self.graph_phonon = InteractiveGraph(self, title="Phonon Band Structure & DOS")
        self.views_tabs.addTab(self.graph_phonon, "Phonon Dispersion / DOS")

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

    def run_phonons(self):
        """Run phonons."""
        struct_file = self.struct_input.get_filepath()
        if not struct_file or not os.path.exists(struct_file):
            QMessageBox.warning(
                self,
                "No Structure File",
                "Please upload or select an input periodic crystal file before running phonon calculations.",  # noqa: E501
            )
            return

        file_prefix = os.path.join(self.temp_dir, "phonons")

        sc_matrix = f"{self.sc_x.value()} {self.sc_y.value()} {self.sc_z.value()}"

        args = [
            "--struct",
            struct_file,
            "--file-prefix",
            file_prefix,
            "--supercell",
            sc_matrix,
            "--displacement",
            str(self.spin_displacement.value()),
        ]
        if self.chk_dos.isChecked():
            args.append("--dos")
        if self.chk_thermal.isChecked():
            args.append("--thermal")

        args.extend(self.calc_selector.get_cli_args())

        self.btn_run.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.log_console.clear()
        self.log_console.append_log("[INFO] Calculating Phonons and force constants...")

        python_path = self.calc_selector.get_selected_python()
        self.runner = CalcRunner(
            "phonons", args, cwd=self.temp_dir, python_path=python_path, parent=self
        )
        self.runner.log_line.connect(self.log_console.append_log)
        self.runner.finished_calculation.connect(self._on_phonons_finished)
        self.runner.start()

    def cancel_phonons(self):
        """Cancel phonons."""
        if self.runner and self.runner.isRunning():
            self.runner.cancel()
            self.btn_cancel.setEnabled(False)

    @Slot(bool, str, dict)
    def _on_phonons_finished(self, success: bool, msg: str, outputs: dict):
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        if success:
            self.log_console.append_log(
                "[SUCCESS] Phonon calculation completed successfully."
            )
