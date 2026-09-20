"""Environments & MLIP Configuration Tab for managing multi-environment potentials."""

import os
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
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFileDialog,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal, Slot

from janus_ux.core.env_manager import EnvironmentManager, EnvConfig, MODEL_PACKAGE_MAP
from janus_ux.core.installer import PackageInstaller
from janus_ux.widgets.log_console import LogConsole

class EnvironmentsTab(QWidget):
    """Configuration tab to manage multiple environments and install selected MLIP models."""

    environments_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.env_mgr = EnvironmentManager()
        self.current_installer: Optional[PackageInstaller] = None
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        splitter = QSplitter(Qt.Horizontal)

        # LEFT PANE: Environments List & Actions
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.setSpacing(8)

        env_group = QGroupBox("Configured Environments")
        eg_layout = QVBoxLayout(env_group)

        self.table_envs = QTableWidget()
        self.table_envs.setColumnCount(4)
        self.table_envs.setHorizontalHeaderLabels(["Name", "Python", "Models", "Default"])
        self.table_envs.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_envs.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_envs.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_envs.itemSelectionChanged.connect(self._on_env_selected)
        eg_layout.addWidget(self.table_envs)

        # Action Buttons
        btn_bar = QHBoxLayout()
        self.btn_scan = QPushButton("🔍 Scan System")
        self.btn_scan.setToolTip("Auto-detect micromamba, conda, and virtual environments")
        self.btn_scan.clicked.connect(self.scan_environments)
        btn_bar.addWidget(self.btn_scan)

        self.btn_add = QPushButton("➕ Add Python...")
        self.btn_add.setToolTip("Browse for a python executable in a custom environment")
        self.btn_add.clicked.connect(self.add_custom_env)
        btn_bar.addWidget(self.btn_add)

        self.btn_default = QPushButton("⭐ Set Default")
        self.btn_default.clicked.connect(self.set_selected_as_default)
        btn_bar.addWidget(self.btn_default)

        self.btn_remove = QPushButton("🗑️ Remove")
        self.btn_remove.clicked.connect(self.remove_selected_env)
        btn_bar.addWidget(self.btn_remove)

        eg_layout.addLayout(btn_bar)
        left_layout.addWidget(env_group)

        splitter.addWidget(left_widget)

        # RIGHT PANE: Selected Environment Details & MLIP Models Manager
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(4, 4, 4, 4)
        right_layout.setSpacing(8)

        # Env Summary Card
        details_group = QGroupBox("Selected Environment Details")
        dg_layout = QGridLayout(details_group)

        self.lbl_selected_name = QLabel("Environment: None")
        self.lbl_selected_name.setStyleSheet("font-size: 14px; font-weight: bold; color: #89b4fa;")
        dg_layout.addWidget(self.lbl_selected_name, 0, 0, 1, 2)

        self.lbl_py_path = QLabel("Path: -")
        self.lbl_py_path.setStyleSheet("color: #a6adc8; font-family: monospace;")
        dg_layout.addWidget(self.lbl_py_path, 1, 0, 1, 2)

        self.lbl_janus_status = QLabel("Janus-Core: Probing...")
        dg_layout.addWidget(self.lbl_janus_status, 2, 0)

        self.btn_install_janus = QPushButton("Install janus-core in this env")
        self.btn_install_janus.setStyleSheet("background-color: #313244; padding: 4px 10px;")
        self.btn_install_janus.clicked.connect(lambda: self.install_model_package("janus-core"))
        dg_layout.addWidget(self.btn_install_janus, 2, 1)

        right_layout.addWidget(details_group)

        # MLIP Models Catalog Table
        models_group = QGroupBox("MLIP Potential Packages (Install via UV)")
        mg_layout = QVBoxLayout(models_group)

        self.table_models = QTableWidget()
        self.table_models.setColumnCount(4)
        self.table_models.setHorizontalHeaderLabels(["Model / Architecture", "PyPI Package", "Status", "Action"])
        self.table_models.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_models.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_models.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_models.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        mg_layout.addWidget(self.table_models)

        # Custom package installer bar
        custom_layout = QHBoxLayout()
        self.input_custom_pkg = QLineEdit()
        self.input_custom_pkg.setPlaceholderText("Or enter custom package to install via uv (e.g. torch-geometric, sevenn)...")
        custom_layout.addWidget(self.input_custom_pkg)

        self.btn_install_custom = QPushButton("Install into Env")
        self.btn_install_custom.setStyleSheet("background-color: #89b4fa; color: #11111b; font-weight: bold;")
        self.btn_install_custom.clicked.connect(self._install_custom_package)
        custom_layout.addWidget(self.btn_install_custom)
        mg_layout.addLayout(custom_layout)

        right_layout.addWidget(models_group, stretch=2)

        # Live Installation Log
        self.log_console = LogConsole(self)
        self.log_console.setMaximumHeight(160)
        right_layout.addWidget(self.log_console, stretch=1)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        main_layout.addWidget(splitter)

        self.populate_environments_table()

    def populate_environments_table(self):
        """Populate table with configured environments."""
        envs = list(self.env_mgr.environments.values())
        self.table_envs.setRowCount(len(envs))

        for row, env in enumerate(envs):
            # Name
            name_item = QTableWidgetItem(env.name)
            name_item.setData(Qt.UserRole, env.name)
            self.table_envs.setItem(row, 0, name_item)

            # Python version
            self.table_envs.setItem(row, 1, QTableWidgetItem(env.python_version or "Unknown"))

            # Supported models
            models_str = ", ".join(env.supported_architectures) if env.supported_architectures else "None"
            self.table_envs.setItem(row, 2, QTableWidgetItem(models_str))

            # Default
            def_str = "⭐ Yes" if env.is_default else ""
            def_item = QTableWidgetItem(def_str)
            def_item.setTextAlignment(Qt.AlignCenter)
            self.table_envs.setItem(row, 3, def_item)

        if envs and self.table_envs.currentRow() < 0:
            self.table_envs.selectRow(0)

    def _get_selected_env_name(self) -> Optional[str]:
        selected_rows = self.table_envs.selectionModel().selectedRows()
        if not selected_rows:
            return None
        row = selected_rows[0].row()
        item = self.table_envs.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _on_env_selected(self):
        env_name = self._get_selected_env_name()
        if not env_name:
            return
        env = self.env_mgr.get_environment(env_name)
        if not env:
            return

        self.lbl_selected_name.setText(f"Environment: {env.name}")
        self.lbl_py_path.setText(f"Python: {env.python_path}")

        janus_status = "✅ Installed" if env.has_janus_core else "❌ Not Installed"
        color = "#a6e3a1" if env.has_janus_core else "#f38ba8"
        self.lbl_janus_status.setText(f"Janus-Core: <span style='color:{color}; font-weight:bold;'>{janus_status}</span>")

        # Populate MLIP Models Table
        self.table_models.setRowCount(len(MODEL_PACKAGE_MAP))
        for row, (key, meta) in enumerate(MODEL_PACKAGE_MAP.items()):
            # Name
            self.table_models.setItem(row, 0, QTableWidgetItem(meta["name"]))

            # Package
            pkg_name = meta["package"]
            self.table_models.setItem(row, 1, QTableWidgetItem(pkg_name))

            # Installed status
            is_installed = any(arch in env.supported_architectures for arch in meta["architectures"])
            status_str = "✅ Installed" if is_installed else "❌ Not Installed"
            status_item = QTableWidgetItem(status_str)
            status_item.setTextAlignment(Qt.AlignCenter)
            if is_installed:
                status_item.setForeground(Qt.green)
            self.table_models.setItem(row, 2, status_item)

            # Action button
            btn_action = QPushButton("Reinstall" if is_installed else "Install via UV")
            btn_action.setStyleSheet("padding: 3px 8px; font-size: 11px;")
            btn_action.clicked.connect(lambda checked=False, p=pkg_name: self.install_model_package(p))
            self.table_models.setCellWidget(row, 3, btn_action)

    def scan_environments(self):
        """Re-scan system for micromamba, conda, and virtual environments."""
        self.log_console.append_log("[INFO] Scanning system for Python and micromamba environments...")
        self.env_mgr.auto_discover()
        self.env_mgr.save_to_file()
        self.populate_environments_table()
        self.environments_updated.emit()
        self.log_console.append_log(f"[SUCCESS] Discovered {len(self.env_mgr.environments)} environments.")

    def add_custom_env(self):
        """Select a custom Python binary."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Python Executable", "", "Python Binary (python*);;All Files (*)"
        )
        if filepath and os.path.exists(filepath):
            name = os.path.basename(os.path.dirname(os.path.dirname(filepath)))
            name = f"custom: {name}"
            self.env_mgr.add_environment(name, filepath)
            self.populate_environments_table()
            self.environments_updated.emit()
            self.log_console.append_log(f"[SUCCESS] Added custom environment: {name} ({filepath})")

    def set_selected_as_default(self):
        env_name = self._get_selected_env_name()
        if env_name:
            self.env_mgr.set_default_environment(env_name)
            self.populate_environments_table()
            self.environments_updated.emit()
            self.log_console.append_log(f"[SUCCESS] Set {env_name} as default environment.")

    def remove_selected_env(self):
        env_name = self._get_selected_env_name()
        if env_name:
            reply = QMessageBox.question(
                self, "Remove Environment", f"Remove environment configuration for '{env_name}'?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.env_mgr.remove_environment(env_name)
                self.populate_environments_table()
                self.environments_updated.emit()
                self.log_console.append_log(f"[INFO] Removed environment {env_name}.")

    def install_model_package(self, package_name: str):
        """Install a package into the currently selected environment using uv."""
        env_name = self._get_selected_env_name()
        if not env_name:
            QMessageBox.warning(self, "No Selection", "Please select an environment from the table first.")
            return

        env = self.env_mgr.get_environment(env_name)
        if not env:
            return

        self.log_console.append_log(f"[INFO] Starting uv pip install for {package_name} into {env.name}...")
        self.current_installer = PackageInstaller(env.python_path, [package_name], parent=self)
        self.current_installer.log_line.connect(self.log_console.append_log)
        self.current_installer.finished_install.connect(lambda ok, msg: self._on_install_completed(env.python_path, ok, msg))
        self.current_installer.start()

    def _install_custom_package(self):
        pkg = self.input_custom_pkg.text().strip()
        if pkg:
            self.install_model_package(pkg)

    @Slot(str, bool, str)
    def _on_install_completed(self, python_path: str, ok: bool, msg: str):
        if ok:
            # Re-probe environment
            env_name = self._get_selected_env_name()
            if env_name:
                probe = self.env_mgr.probe_environment(python_path)
                env = self.env_mgr.get_environment(env_name)
                if env:
                    env.has_janus_core = probe["has_janus"]
                    env.supported_architectures = probe["architectures"]
                    env.installed_packages = probe["packages"]
                    self.env_mgr.save_to_file()

            self._on_env_selected()
            self.environments_updated.emit()
            self.log_console.append_log("[SUCCESS] Environment probed and updated.")
