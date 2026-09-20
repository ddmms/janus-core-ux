"""Molecular Dynamics Tab with NVE/NVT/NPT ensembles, thermodynamic curves, and trajectory playback."""  # noqa: E501

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
    parse_md_stats,
    read_trajectory,
)
from janus_ux.core.runner import CalcRunner
from janus_ux.widgets.calculator_selector import CalculatorSelector
from janus_ux.widgets.chemiscope_widget import ChemiscopeWidget
from janus_ux.widgets.interactive_graph import InteractiveGraph
from janus_ux.widgets.log_console import LogConsole
from janus_ux.widgets.structure_file_input import StructureFileInput
from janus_ux.widgets.structure_inspector import StructureInspector


class MDTab(QWidget):
    """Tab for running Molecular Dynamics simulations and visualizing thermodynamic properties."""  # noqa: E501

    def __init__(self, parent=None, calc_selector: CalculatorSelector | None = None):
        super().__init__(parent)
        self.is_standalone = calc_selector is None
        self.calc_selector = calc_selector or CalculatorSelector(self)
        self.current_atoms: Atoms | None = None
        self.traj_atoms: list[Atoms] = []
        self.stats_data: dict = {}
        self.runner: CalcRunner | None = None
        self.working_dir: Path | None = None
        self._last_args: list[str] = []

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        splitter = QSplitter(Qt.Horizontal)

        # LEFT PANE: Controls & Parameters
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.setSpacing(8)

        # Structure File Input
        self.struct_input = StructureFileInput("Input Structure File", parent=self)
        self.struct_input.structure_loaded.connect(self._on_structure_loaded)
        self.struct_input.structure_cleared.connect(self._on_structure_cleared)
        self.input_file = self.struct_input.input_file
        left_layout.addWidget(self.struct_input)

        # Calculator (only shown if standalone)
        if self.is_standalone:
            left_layout.addWidget(self.calc_selector)

        # MD Settings Group
        md_group = QGroupBox("MD Parameters")
        mg_layout = QGridLayout(md_group)

        mg_layout.addWidget(QLabel("Ensemble:"), 0, 0)
        self.combo_ensemble = QComboBox()
        self.combo_ensemble.addItems(["nvt", "npt", "nve"])
        mg_layout.addWidget(self.combo_ensemble, 0, 1)

        mg_layout.addWidget(QLabel("Thermostat:"), 1, 0)
        self.combo_thermostat = QComboBox()
        self.combo_thermostat.addItems(["langevin", "nose-hoover", "berendsen"])
        mg_layout.addWidget(self.combo_thermostat, 1, 1)

        mg_layout.addWidget(QLabel("Temperature (K):"), 2, 0)
        self.spin_temp = QDoubleSpinBox()
        self.spin_temp.setRange(0.1, 5000.0)
        self.spin_temp.setValue(300.0)
        self.spin_temp.setSingleStep(25.0)
        mg_layout.addWidget(self.spin_temp, 2, 1)

        mg_layout.addWidget(QLabel("Time Step (fs):"), 3, 0)
        self.spin_timestep = QDoubleSpinBox()
        self.spin_timestep.setRange(0.1, 20.0)
        self.spin_timestep.setValue(1.0)
        self.spin_timestep.setSingleStep(0.5)
        mg_layout.addWidget(self.spin_timestep, 3, 1)

        mg_layout.addWidget(QLabel("Total Steps:"), 4, 0)
        self.spin_steps = QSpinBox()
        self.spin_steps.setRange(10, 1000000)
        self.spin_steps.setValue(1000)
        self.spin_steps.setSingleStep(500)
        mg_layout.addWidget(self.spin_steps, 4, 1)

        mg_layout.addWidget(QLabel("Traj Sampling (steps):"), 5, 0)
        self.spin_traj_every = QSpinBox()
        self.spin_traj_every.setRange(1, 10000)
        self.spin_traj_every.setValue(20)
        mg_layout.addWidget(self.spin_traj_every, 5, 1)

        left_layout.addWidget(md_group)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_run = QPushButton("Run Simulation")
        self.btn_run.setStyleSheet(
            "background-color: #89b4fa; color: #11111b; font-weight: bold; padding: 10px;"  # noqa: E501
        )
        self.btn_run.clicked.connect(self.run_md)
        btn_layout.addWidget(self.btn_run)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_md)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save_config = QPushButton("💾 Save Config…")
        self.btn_save_config.setEnabled(False)
        self.btn_save_config.setToolTip(
            "Save the YAML config used for the last run "
            "(re-usable with janus md --config)."
        )
        self.btn_save_config.clicked.connect(self._save_config)
        btn_layout.addWidget(self.btn_save_config)

        left_layout.addLayout(btn_layout)
        left_layout.addStretch()

        splitter.addWidget(left_widget)

        # RIGHT PANE: Visualizer, Graphs, Logs
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(4, 4, 4, 4)
        right_layout.setSpacing(6)

        self.views_tabs = QTabWidget()

        # Tab 1: Chemiscope Trajectory Player
        self.chemiscope = ChemiscopeWidget(self)
        self.views_tabs.addTab(self.chemiscope, "3D Trajectory (Chemiscope)")

        # Tab 2: Temperature & Energy Plots
        self.graph_temp = InteractiveGraph(self, title="Temperature vs Simulation Time")
        self.graph_temp.point_clicked.connect(self._on_time_point_clicked)
        self.views_tabs.addTab(
            self.graph_temp, "Temperature & Energy (Click to View Structure)"
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
    def _on_time_point_clicked(self, index: int):
        if self.traj_atoms and 0 <= index < len(self.traj_atoms):
            self.chemiscope.select_frame(index)
            self.inspector.load_structure(self.traj_atoms[index])

    def set_working_dir(self, path: Path) -> None:
        """Set the working directory for janus output files."""
        self.working_dir = path

    def _get_run_dir(self) -> str:
        if self.working_dir is not None:
            self.working_dir.mkdir(parents=True, exist_ok=True)
            return str(self.working_dir)
        return tempfile.mkdtemp(prefix="janus_md_")

    def run_md(self):
        """Run md."""
        struct_file = self.struct_input.get_filepath()
        if not struct_file or not Path(struct_file).exists():
            QMessageBox.warning(
                self,
                "No Structure File",
                "Please upload or select an input structure file before running molecular dynamics.",  # noqa: E501
            )
            return

        run_dir = self._get_run_dir()
        file_prefix = str(Path(run_dir) / "md")
        traj_file = f"{file_prefix}-traj.extxyz"
        stats_file = f"{file_prefix}-stats.dat"

        args = [
            "--struct",
            struct_file,
            "--file-prefix",
            file_prefix,
            "--ensemble",
            self.combo_ensemble.currentText(),
            "--temp",
            str(self.spin_temp.value()),
            "--timestep",
            str(self.spin_timestep.value()),
            "--steps",
            str(self.spin_steps.value()),
            "--traj-every",
            str(self.spin_traj_every.value()),
            "--traj-file",
            traj_file,
            "--stats-file",
            stats_file,
        ]
        args.extend(self.calc_selector.get_cli_args())

        expected = {
            "traj_file": traj_file,
            "stats_file": stats_file,
        }

        self._last_args = list(args)
        self.btn_run.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_save_config.setEnabled(False)
        self.log_console.clear()
        self.log_console.append_log("[INFO] Starting Molecular Dynamics simulation...")

        python_path = self.calc_selector.get_selected_python()
        self.runner = CalcRunner(
            "md",
            args,
            cwd=run_dir,
            expected_output_files=expected,
            python_path=python_path,
            parent=self,
        )
        self.runner.log_line.connect(self.log_console.append_log)
        self.runner.finished_calculation.connect(self._on_md_finished)
        self.runner.start()

    def cancel_md(self):
        """Cancel md."""
        if self.runner and self.runner.isRunning():
            self.runner.cancel()
            self.btn_cancel.setEnabled(False)

    @Slot(bool, str, dict)
    def _on_md_finished(self, success: bool, msg: str, outputs: dict):
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)

        if not success:
            return

        self.btn_save_config.setEnabled(True)

        traj_file = outputs.get("traj_file")
        stats_file = outputs.get("stats_file")

        if traj_file and Path(traj_file).exists():
            self.traj_atoms = read_trajectory(traj_file)
            if self.traj_atoms:
                props = extract_trajectory_properties(self.traj_atoms)
                self.chemiscope.load_trajectory(self.traj_atoms, properties=props)

        if stats_file and Path(stats_file).exists():
            self.stats_data = parse_md_stats(stats_file)
            if self.stats_data:
                time_fs = self.stats_data.get(
                    "Timeps",
                    self.stats_data.get("time", np.arange(len(self.traj_atoms))),
                )
                temp_k = self.stats_data.get("TempK", self.stats_data.get("temp", []))
                epot = self.stats_data.get("Epot", self.stats_data.get("epot", []))

                sec_y = None
                if len(epot) == len(time_fs):
                    sec_y = {
                        "name": "Potential Energy",
                        "values": list(epot),
                        "color": "#a6e3a1",
                        "label": "Epot (eV)",
                    }

                if len(temp_k) == len(time_fs):
                    self.graph_temp.plot_curve(
                        x=list(time_fs),
                        y=list(temp_k),
                        x_label="Time (ps / steps)",
                        y_label="Temperature (K)",
                        name="Temperature",
                        color="#fab387",
                        secondary_y=sec_y,
                    )
        self.log_console.append_log(
            "[SUCCESS] Molecular Dynamics trajectory and statistics rendered."
        )

    def _save_config(self) -> None:
        """Save the YAML config used for the last run."""
        save_dir = str(self.working_dir) if self.working_dir else str(Path.home())
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Janus Config File",
            str(Path(save_dir) / "janus_md_config.yaml"),
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
