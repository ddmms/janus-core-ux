"""Main Application Window for Janus Core UX."""

import sys
from PySide6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QMenuBar,
    QMenu,
    QStatusBar,
    QMessageBox,
    QFileDialog,
)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Qt

from janus_ux.theme import DARK_STYLESHEET
from janus_ux.tabs import (
    SinglePointTab,
    GeomOptTab,
    MDTab,
    PhononsTab,
    EOSTab,
    ElasticityTab,
    NEBTab,
    DescriptorsTab,
    EnvironmentsTab,
)
from janus_ux.core.presets import get_preset_structures

class MainWindow(QMainWindow):
    """Main window hosting all Janus-Core calculation tabs and environment management."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Janus-Core UX | Multi-MLIP Simulation Suite")
        self.resize(1380, 890)
        self.setMinimumSize(1000, 680)

        # Apply global theme
        self.setStyleSheet(DARK_STYLESHEET)

        self._setup_menus()
        self._setup_tabs()
        self._setup_statusbar()

    def _setup_menus(self):
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("&File")

        action_open = QAction("&Open Structure...", self)
        action_open.setShortcut("Ctrl+O")
        action_open.triggered.connect(self._open_structure)
        file_menu.addAction(action_open)

        file_menu.addSeparator()

        action_exit = QAction("E&xit", self)
        action_exit.setShortcut("Ctrl+Q")
        action_exit.triggered.connect(self.close)
        file_menu.addAction(action_exit)

        # Presets Menu
        presets_menu = menubar.addMenu("&Presets")
        for preset_name in get_preset_structures().keys():
            action = QAction(preset_name, self)
            action.triggered.connect(lambda checked=False, name=preset_name: self._load_preset(name))
            presets_menu.addAction(action)

        # Calculations Menu
        calc_menu = menubar.addMenu("&Calculations")
        options = [
            ("Geometry Optimization", 0),
            ("Single Point Calculation", 1),
            ("Molecular Dynamics", 2),
            ("Phonons & Band Structure", 3),
            ("Equation of State (EOS)", 4),
            ("Elasticity Stiffness Tensor", 5),
            ("Nudged Elastic Band (NEB)", 6),
            ("MLIP Descriptors", 7),
            ("Environments & MLIP Setup", 8),
        ]
        for name, idx in options:
            act = QAction(name, self)
            act.triggered.connect(lambda checked=False, i=idx: self.tab_widget.setCurrentIndex(i))
            calc_menu.addAction(act)

        # Help Menu
        help_menu = menubar.addMenu("&Help")
        action_about = QAction("&About Janus-Core UX", self)
        action_about.triggered.connect(self._show_about)
        help_menu.addAction(action_about)

    def _setup_tabs(self):
        self.tab_widget = QTabWidget(self)
        self.tab_widget.setDocumentMode(True)

        # Instantiate tabs
        self.tab_geomopt = GeomOptTab(self)
        self.tab_singlepoint = SinglePointTab(self)
        self.tab_md = MDTab(self)
        self.tab_phonons = PhononsTab(self)
        self.tab_eos = EOSTab(self)
        self.tab_elasticity = ElasticityTab(self)
        self.tab_neb = NEBTab(self)
        self.tab_descriptors = DescriptorsTab(self)
        self.tab_environments = EnvironmentsTab(self)

        # Add tabs
        self.tab_widget.addTab(self.tab_geomopt, "⚡ Geometry Optimization")
        self.tab_widget.addTab(self.tab_singlepoint, "🎯 Single Point")
        self.tab_widget.addTab(self.tab_md, "🌊 Molecular Dynamics")
        self.tab_widget.addTab(self.tab_phonons, "🎵 Phonons")
        self.tab_widget.addTab(self.tab_eos, "📈 Equation of State")
        self.tab_widget.addTab(self.tab_elasticity, "💎 Elasticity")
        self.tab_widget.addTab(self.tab_neb, "⛰️ NEB Pathways")
        self.tab_widget.addTab(self.tab_descriptors, "🧬 Descriptors")
        self.tab_widget.addTab(self.tab_environments, "⚙️ MLIP Environments")

        # Connect environment update signal to all CalculatorSelector instances
        self.tab_environments.environments_updated.connect(self._on_environments_updated)

        self.setCentralWidget(self.tab_widget)

    def _on_environments_updated(self):
        """Notify all calculation tabs to refresh their environment lists."""
        for tab in [
            self.tab_geomopt,
            self.tab_singlepoint,
            self.tab_md,
            self.tab_phonons,
            self.tab_eos,
            self.tab_elasticity,
            self.tab_neb,
            self.tab_descriptors,
        ]:
            if hasattr(tab, "calc_selector"):
                tab.calc_selector.reload_environments()

    def _setup_statusbar(self):
        status = QStatusBar(self)
        status.showMessage("Janus-Core UX Ready | Multi-Environment MLIP Support Active")
        self.setStatusBar(status)

    def _open_structure(self):
        current_tab = self.tab_widget.currentWidget()
        if hasattr(current_tab, "_browse_structure"):
            current_tab._browse_structure()

    def _load_preset(self, name: str):
        current_tab = self.tab_widget.currentWidget()
        if hasattr(current_tab, "combo_preset"):
            idx = current_tab.combo_preset.findText(name)
            if idx >= 0:
                current_tab.combo_preset.setCurrentIndex(idx)
            elif hasattr(current_tab, "_on_preset_selected"):
                current_tab._on_preset_selected(name)

    def _show_about(self):
        QMessageBox.about(
            self,
            "About Janus-Core UX",
            "<h3>Janus-Core Desktop UX</h3>"
            "<p>A graphical user interface for <b>STFC janus-core</b> built with <b>Qt6 & PySide6</b>.</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Multi-MLIP Environments Configuration & Model installer via UV</li>"
            "<li>Chemiscope 3D atomistic structure and trajectory visualization</li>"
            "<li>Interactive 2D/3D linked graphs with point-to-structure picking</li>"
            "<li>Dedicated tabs for Geometry Optimization, Single Point, MD, Phonons, EOS, Elasticity, NEB, and Descriptors</li>"
            "<li>Support for MACE, SevenNet, CHGNet, FairChem, NequIP, ORB, and MatterSim</li>"
            "</ul>"
        )
