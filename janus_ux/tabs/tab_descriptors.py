"""Descriptors Tab for calculating and visualizing MLIP atomic and structural representations."""

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
    QCheckBox,
    QFileDialog,
    QMessageBox,
    QTabWidget,
)
from PySide6.QtCore import Qt, Slot
from ase import Atoms
import ase.io

from janus_ux.core.presets import get_preset_structures
from janus_ux.core.runner import CalcRunner
from janus_ux.widgets.calculator_selector import CalculatorSelector
from janus_ux.widgets.chemiscope_widget import ChemiscopeWidget
from janus_ux.widgets.structure_inspector import StructureInspector
from janus_ux.widgets.log_console import LogConsole

class DescriptorsTab(QWidget):
    """Tab for calculating MLIP descriptors."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_atoms: Optional[Atoms] = None
        self.runner: Optional[CalcRunner] = None
        self.temp_dir = tempfile.mkdtemp(prefix="janus_desc_")

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
        struct_group = QGroupBox("Input Structure")
        sg_layout = QGridLayout(struct_group)
        sg_layout.addWidget(QLabel("Preset:"), 0, 0)
        self.combo_preset = QComboBox()
        self.combo_preset.addItem("-- Select Preset --")
        self.combo_preset.addItems(list(get_preset_structures().keys()))
        self.combo_preset.currentTextChanged.connect(self._on_preset_selected)
        sg_layout.addWidget(self.combo_preset, 0, 1)

        sg_layout.addWidget(QLabel("Or Custom File:"), 1, 0)
        file_box = QHBoxLayout()
        self.input_file = QLineEdit()
        self.input_file.setPlaceholderText("Path to structure (.xyz, .cif, etc.)")
        file_box.addWidget(self.input_file)
        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.clicked.connect(self._browse_structure)
        file_box.addWidget(self.btn_browse)
        sg_layout.addLayout(file_box, 1, 1)

        left_layout.addWidget(struct_group)

        # Calculator
        self.calc_selector = CalculatorSelector(self)
        left_layout.addWidget(self.calc_selector)

        # Descriptor Options
        desc_group = QGroupBox("Descriptor Settings")
        dg_layout = QVBoxLayout(desc_group)

        self.chk_invariants = QCheckBox("Invariants Only")
        self.chk_invariants.setChecked(True)
        dg_layout.addWidget(self.chk_invariants)

        self.chk_per_atom = QCheckBox("Calculate Per-Atom Descriptors")
        self.chk_per_atom.setChecked(True)
        dg_layout.addWidget(self.chk_per_atom)

        self.chk_per_element = QCheckBox("Calculate Mean Per-Element Descriptors")
        self.chk_per_element.setChecked(False)
        dg_layout.addWidget(self.chk_per_element)

        left_layout.addWidget(desc_group)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_run = QPushButton("Compute Descriptors")
        self.btn_run.setStyleSheet("background-color: #89b4fa; color: #11111b; font-weight: bold; padding: 10px;")
        self.btn_run.clicked.connect(self.run_descriptors)
        btn_layout.addWidget(self.btn_run)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_descriptors)
        btn_layout.addWidget(self.btn_cancel)

        left_layout.addLayout(btn_layout)
        left_layout.addStretch()

        splitter.addWidget(left_widget)

        # RIGHT PANE: Visualizer & Logs
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(4, 4, 4, 4)
        right_layout.setSpacing(6)

        self.views_tabs = QTabWidget()

        # Tab 1: Chemiscope 3D
        self.chemiscope = ChemiscopeWidget(self, default_mode="structure")
        self.views_tabs.addTab(self.chemiscope, "3D Structure (Chemiscope)")

        # Tab 2: Structure Inspector
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
            self, "Select Structure File", "", "Structure Files (*.xyz *.cif *.poscar *.extxyz);;All Files (*)"
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

    def run_descriptors(self):
        if self.current_atoms is None and not self.input_file.text().strip():
            QMessageBox.warning(self, "No Structure", "Please select a preset or browse an input structure file.")
            return

        struct_file = self.input_file.text().strip()
        if not struct_file or not os.path.exists(struct_file):
            struct_file = os.path.join(self.temp_dir, "desc_input.xyz")
            ase.io.write(struct_file, self.current_atoms)

        file_prefix = os.path.join(self.temp_dir, "desc")
        out_file = f"{file_prefix}-desc.extxyz"

        args = [
            "--struct", struct_file,
            "--file-prefix", file_prefix,
            "--out", out_file,
        ]
        if self.chk_invariants.isChecked():
            args.append("--invariants-only")
        else:
            args.append("--no-invariants-only")

        if self.chk_per_atom.isChecked():
            args.append("--calc-per-atom")
        if self.chk_per_element.isChecked():
            args.append("--calc-per-element")

        args.extend(self.calc_selector.get_cli_args())

        expected = {"out_file": out_file}

        self.btn_run.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.log_console.clear()
        self.log_console.append_log("[INFO] Calculating MLIP descriptors...")

        python_path = self.calc_selector.get_selected_python()
        self.runner = CalcRunner(
            "descriptors",
            args,
            cwd=self.temp_dir,
            expected_output_files=expected,
            python_path=python_path,
            parent=self,
        )
        self.runner.log_line.connect(self.log_console.append_log)
        self.runner.finished_calculation.connect(self._on_descriptors_finished)
        self.runner.start()

    def cancel_descriptors(self):
        if self.runner and self.runner.isRunning():
            self.runner.cancel()
            self.btn_cancel.setEnabled(False)

    @Slot(bool, str, dict)
    def _on_descriptors_finished(self, success: bool, msg: str, outputs: dict):
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        if success:
            self.log_console.append_log("[SUCCESS] MLIP descriptors calculated and saved.")
