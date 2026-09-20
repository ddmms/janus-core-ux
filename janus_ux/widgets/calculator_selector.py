"""MLIP Calculator selection, device configuration, and execution environment selector."""

from typing import List, Optional
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QComboBox,
    QLineEdit,
    QCheckBox,
    QPushButton,
    QFileDialog,
)
from PySide6.QtCore import Signal
from janus_ux.core.models import SUPPORTED_ARCHITECTURES, DEFAULT_MODELS
from janus_ux.core.env_manager import EnvironmentManager, EnvConfig, MODEL_PACKAGE_MAP

class CalculatorSelector(QGroupBox):
    """Configuration panel for MLIP Architecture, Model weights, Device, and Target Environment."""

    selection_changed = Signal()

    def __init__(self, parent=None, title="⚙️ Global MLIP Potential & Target Environment (Applied to all calculation modes)"):
        super().__init__(title, parent)
        self.env_mgr = EnvironmentManager()
        self._setup_ui()

    def _setup_ui(self):
        grid = QGridLayout(self)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)
        grid.setContentsMargins(12, 10, 12, 10)

        # Row 0: Environment, Architecture, Device
        grid.addWidget(QLabel("Execution Environment:"), 0, 0)
        env_box = QHBoxLayout()
        env_box.setSpacing(6)
        self.combo_env = QComboBox()
        self.combo_env.setToolTip("Select the environment containing the desired MLIP model")
        self.combo_env.currentTextChanged.connect(self._on_env_changed)
        env_box.addWidget(self.combo_env)

        self.lbl_env_status = QLabel("● Probing")
        self.lbl_env_status.setStyleSheet("color: #a6adc8; font-size: 11px;")
        env_box.addWidget(self.lbl_env_status)
        grid.addLayout(env_box, 0, 1)

        grid.addWidget(QLabel("MLIP Architecture:"), 0, 2)
        self.combo_arch = QComboBox()
        self.combo_arch.addItems(SUPPORTED_ARCHITECTURES)
        self.combo_arch.currentTextChanged.connect(self._on_arch_changed)
        grid.addWidget(self.combo_arch, 0, 3)

        grid.addWidget(QLabel("Compute Device:"), 0, 4)
        self.combo_device = QComboBox()
        self.combo_device.addItems(["cpu", "cuda", "mps", "xpu"])
        self.combo_device.currentTextChanged.connect(lambda: self.selection_changed.emit())
        grid.addWidget(self.combo_device, 0, 5)

        # Row 1: Model weights / path and Options
        grid.addWidget(QLabel("Model Path / Name:"), 1, 0)
        model_layout = QHBoxLayout()
        model_layout.setContentsMargins(0, 0, 0, 0)
        self.input_model = QLineEdit()
        self.input_model.setPlaceholderText("Leave empty for default foundational model")
        self.input_model.textChanged.connect(lambda: self.selection_changed.emit())
        model_layout.addWidget(self.input_model)

        self.btn_browse_model = QPushButton("Browse...")
        self.btn_browse_model.clicked.connect(self._browse_model)
        model_layout.addWidget(self.btn_browse_model)
        grid.addLayout(model_layout, 1, 1, 1, 3)

        options_layout = QHBoxLayout()
        options_layout.setSpacing(14)
        self.chk_dispersion = QCheckBox("Dispersion (D3)")
        self.chk_dispersion.toggled.connect(lambda: self.selection_changed.emit())
        options_layout.addWidget(self.chk_dispersion)

        self.chk_tracker = QCheckBox("Track Carbon")
        self.chk_tracker.setChecked(False)  # User rule: default no-tracker
        self.chk_tracker.setToolTip("Track emissions with CodeCarbon (disabled by default to prevent overhead)")
        self.chk_tracker.toggled.connect(lambda: self.selection_changed.emit())
        options_layout.addWidget(self.chk_tracker)
        grid.addLayout(options_layout, 1, 4, 1, 2)

        self.reload_environments()

    def reload_environments(self):
        """Refresh environment items from EnvironmentManager."""
        self.combo_env.blockSignals(True)
        self.combo_env.clear()

        envs = list(self.env_mgr.environments.values())
        default_idx = 0
        for i, env in enumerate(envs):
            label = f"{env.name} (Python {env.python_version})"
            self.combo_env.addItem(label, env.name)
            if env.is_default:
                default_idx = i

        if envs:
            self.combo_env.setCurrentIndex(default_idx)

        self.combo_env.blockSignals(False)
        self._update_env_status()

    def _on_env_changed(self):
        self._update_env_status()
        self.selection_changed.emit()

    def _on_arch_changed(self, arch: str):
        default_model = DEFAULT_MODELS.get(arch, "")
        if default_model:
            self.input_model.setPlaceholderText(f"Default: {default_model}")
        else:
            self.input_model.setPlaceholderText("Optional path to custom model file")

        # Auto-recommend environment if current env does not support this arch
        env = self.get_selected_env()
        if env and arch not in env.supported_architectures:
            matching_envs = self.env_mgr.get_environments_for_arch(arch)
            if matching_envs:
                # Switch to first matching environment
                for i in range(self.combo_env.count()):
                    if self.combo_env.itemData(i) == matching_envs[0].name:
                        self.combo_env.setCurrentIndex(i)
                        break

        self._update_env_status()
        self.selection_changed.emit()

    def _update_env_status(self):
        env = self.get_selected_env()
        arch = self.combo_arch.currentText()

        if not env:
            self.lbl_env_status.setText("❌ No environment")
            self.lbl_env_status.setStyleSheet("color: #f38ba8; font-size: 11px;")
            return

        if arch in env.supported_architectures:
            self.lbl_env_status.setText(f"✅ {arch} available")
            self.lbl_env_status.setStyleSheet("color: #a6e3a1; font-size: 11px;")
        else:
            self.lbl_env_status.setText(f"⚠️ {arch} not in env")
            self.lbl_env_status.setStyleSheet("color: #fab387; font-size: 11px;")

    def _browse_model(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select MLIP Model Weights", "", "Model Files (*.model *.pt *.pth *.pt.tar);;All Files (*)"
        )
        if filename:
            self.input_model.setText(filename)

    def get_selected_env(self) -> Optional[EnvConfig]:
        """Return the EnvConfig object for the currently selected environment."""
        env_name = self.combo_env.currentData()
        if env_name:
            return self.env_mgr.get_environment(env_name)
        return self.env_mgr.get_default_environment()

    def get_selected_python(self) -> Optional[str]:
        """Return python path of the selected environment."""
        env = self.get_selected_env()
        return env.python_path if env else None

    def get_cli_args(self) -> List[str]:
        """Generate CLI flags for janus command line execution."""
        args = [
            "--arch", self.combo_arch.currentText(),
            "--device", self.combo_device.currentText(),
        ]

        model = self.input_model.text().strip()
        if model:
            args.extend(["--model", model])

        if self.chk_dispersion.isChecked():
            args.append("--dispersion")

        if self.chk_tracker.isChecked():
            args.append("--tracker")
        else:
            args.append("--no-tracker")

        return args

    def get_calc_kwargs(self) -> dict:
        """Return calculator parameters as a python dict."""
        res = {
            "arch": self.combo_arch.currentText(),
            "device": self.combo_device.currentText(),
        }
        model = self.input_model.text().strip()
        if model:
            res["model"] = model
        if self.chk_dispersion.isChecked():
            res["dispersion"] = True
        return res
