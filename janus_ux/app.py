"""Main Application Window for Janus Core UX."""

import sys
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
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
from janus_ux.widgets.calculator_selector import CalculatorSelector
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

        action_desktop = QAction("&Install Desktop Shortcut", self)
        action_desktop.triggered.connect(self._install_desktop_shortcut)
        help_menu.addAction(action_desktop)

        help_menu.addSeparator()

        action_about = QAction("&About Janus-Core UX", self)
        action_about.triggered.connect(self._show_about)
        help_menu.addAction(action_about)

    def _setup_tabs(self):
        # Global CalculatorSelector shared across all calculation modes
        self.calc_selector = CalculatorSelector(
            self,
            title="⚙️ Global MLIP Potential & Target Environment (Applied to all calculation modes)"
        )

        self.tab_widget = QTabWidget(self)
        self.tab_widget.setDocumentMode(True)

        # Instantiate tabs sharing the single global calc_selector
        self.tab_geomopt = GeomOptTab(parent=self, calc_selector=self.calc_selector)
        self.tab_singlepoint = SinglePointTab(parent=self, calc_selector=self.calc_selector)
        self.tab_md = MDTab(parent=self, calc_selector=self.calc_selector)
        self.tab_phonons = PhononsTab(parent=self, calc_selector=self.calc_selector)
        self.tab_eos = EOSTab(parent=self, calc_selector=self.calc_selector)
        self.tab_elasticity = ElasticityTab(parent=self, calc_selector=self.calc_selector)
        self.tab_neb = NEBTab(parent=self, calc_selector=self.calc_selector)
        self.tab_descriptors = DescriptorsTab(parent=self, calc_selector=self.calc_selector)
        self.tab_environments = EnvironmentsTab(parent=self)

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

        # Connect environment update signal to the global CalculatorSelector
        self.tab_environments.environments_updated.connect(self._on_environments_updated)

        # Central container: Shared CalculatorSelector on top, tab widget below
        container = QWidget(self)
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(8, 6, 8, 6)
        c_layout.setSpacing(6)
        c_layout.addWidget(self.calc_selector)
        c_layout.addWidget(self.tab_widget)
        self.setCentralWidget(container)

    def _on_environments_updated(self):
        """Notify the shared CalculatorSelector to refresh its environment list."""
        if hasattr(self, "calc_selector"):
            self.calc_selector.reload_environments()

    def _setup_statusbar(self):
        status = QStatusBar(self)
        status.showMessage("Janus-Core UX Ready | Multi-Environment MLIP Support Active")
        self.setStatusBar(status)

    def _open_structure(self):
        current_tab = self.tab_widget.currentWidget()
        if hasattr(current_tab, "struct_input"):
            current_tab.struct_input.browse_file()
        elif hasattr(current_tab, "_browse_structure"):
            current_tab._browse_structure()

    def _install_desktop_shortcut(self):
        from janus_ux.core.desktop_integration import install_desktop_entry
        try:
            ok = install_desktop_entry()
            if ok:
                QMessageBox.information(
                    self,
                    "Desktop Shortcut Installed",
                    "Janus-Core UX desktop shortcut and application icon have been installed to your system applications menu (~/.local/share/applications/janus-core-ux.desktop)."
                )
            else:
                QMessageBox.warning(self, "Installation Failed", "Could not install desktop shortcut.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to install desktop shortcut: {e}")

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
