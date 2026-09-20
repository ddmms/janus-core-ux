"""Phonons Tab for calculating phonon dispersions, density of states (DOS), and thermal properties."""

import os
import tempfile
from typing import Optional
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
import plotly.graph_objects as go

from janus_ux.core.presets import get_preset_structures
from janus_ux.core.runner import CalcRunner
from janus_ux.widgets.calculator_selector import CalculatorSelector
from janus_ux.widgets.chemiscope_widget import ChemiscopeWidget
from janus_ux.widgets.interactive_graph import InteractiveGraph
from janus_ux.widgets.structure_inspector import StructureInspector
from janus_ux.widgets.log_console import LogConsole

class PhononsTab(QWidget):
    """Tab for Phonon calculations and vibrational thermodynamics."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_atoms: Optional[Atoms] = None
        self.runner: Optional[CalcRunner] = None
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

        # Structure Selection
        struct_group = QGroupBox("Input Periodic Structure")
        sg_layout = QGridLayout(struct_group)
        sg_layout.addWidget(QLabel("Preset:"), 0, 0)
        self.combo_preset = QComboBox()
        self.combo_preset.addItem("-- Select Preset --")
        self.combo_preset.addItems([k for k, v in get_preset_structures().items() if v.pbc.any()])
        self.combo_preset.currentTextChanged.connect(self._on_preset_selected)
        sg_layout.addWidget(self.combo_preset, 0, 1)

        sg_layout.addWidget(QLabel("Or Custom File:"), 1, 0)
        file_box = QHBoxLayout()
        self.input_file = QLineEdit()
        self.input_file.setPlaceholderText("Path to relaxed crystal structure")
        file_box.addWidget(self.input_file)
        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.clicked.connect(self._browse_structure)
        file_box.addWidget(self.btn_browse)
        sg_layout.addLayout(file_box, 1, 1)

        left_layout.addWidget(struct_group)

        # Calculator
        self.calc_selector = CalculatorSelector(self)
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

        self.chk_thermal = QCheckBox("Calculate Thermal Properties (Cv, Entropy, Free Energy)")
        self.chk_thermal.setChecked(True)
        pg_layout.addWidget(self.chk_thermal, 3, 0, 1, 2)

        left_layout.addWidget(ph_group)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_run = QPushButton("Calculate Phonons")
        self.btn_run.setStyleSheet("background-color: #89b4fa; color: #11111b; font-weight: bold; padding: 10px;")
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

    def _on_preset_selected(self, name: str):
        presets = get_preset_structures()
        if name in presets:
            self.current_atoms = presets[name].copy()
            self.inspector.load_structure(self.current_atoms)
            self.chemiscope.load_atoms(self.current_atoms)
            self.input_file.clear()

    def _browse_structure(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Crystal Structure File", "",
            "Structure Files (*.cif *.xyz *.poscar *.extxyz);;All Files (*)"
        )
        if filepath:
            self.input_file.setText(filepath)
            try:
                atoms = ase.io.read(filepath)
                self.current_atoms = atoms
                self.inspector.load_structure(atoms)
                self.chemiscope.load_atoms(atoms)
                self.combo_preset.setCurrentIndex(0)
            except Exception as e:
                QMessageBox.critical(self, "Error Loading Structure", f"Could not read structure: {e}")

    def run_phonons(self):
        if self.current_atoms is None and not self.input_file.text().strip():
            QMessageBox.warning(self, "No Structure", "Please select a preset or browse an input structure file.")
            return

        struct_file = self.input_file.text().strip()
        if not struct_file or not os.path.exists(struct_file):
            struct_file = os.path.join(self.temp_dir, "ph_input.xyz")
            ase.io.write(struct_file, self.current_atoms)

        file_prefix = os.path.join(self.temp_dir, "phonons")

        sc_matrix = f"{self.sc_x.value()} {self.sc_y.value()} {self.sc_z.value()}"

        args = [
            "--struct", struct_file,
            "--file-prefix", file_prefix,
            "--supercell-matrix", str(self.sc_x.value()), str(self.sc_y.value()), str(self.sc_z.value()),
            "--displacement", str(self.spin_displacement.value()),
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
        self.runner = CalcRunner("phonons", args, cwd=self.temp_dir, python_path=python_path, parent=self)
        self.runner.log_line.connect(self.log_console.append_log)
        self.runner.finished_calculation.connect(self._on_phonons_finished)
        self.runner.start()

    def cancel_phonons(self):
        if self.runner and self.runner.isRunning():
            self.runner.cancel()
            self.btn_cancel.setEnabled(False)

    @Slot(bool, str, dict)
    def _on_phonons_finished(self, success: bool, msg: str, outputs: dict):
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        if success:
            self.log_console.append_log("[SUCCESS] Phonon calculation completed successfully.")
