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
from janus_ux.core.presets import SUPPORTED_ARCHITECTURES, DEFAULT_MODELS
from janus_ux.core.env_manager import EnvironmentManager, EnvConfig, MODEL_PACKAGE_MAP

class CalculatorSelector(QGroupBox):
    """Configuration panel for MLIP Architecture, Model weights, Device, and Target Environment."""

    def __init__(self, parent=None, title="MLIP Potential & Environment"):
        super().__init__(title, parent)
        self.env_mgr = EnvironmentManager()
        self._setup_ui()

    def _setup_ui(self):
        grid = QGridLayout(self)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        # 0. Environment Selection
        grid.addWidget(QLabel("Execution Environment:"), 0, 0)
        self.combo_env = QComboBox()
        self.combo_env.setToolTip("Select the micromamba / conda / venv environment containing the desired MLIP model")
        self.combo_env.currentTextChanged.connect(self._on_env_changed)
        grid.addWidget(self.combo_env, 0, 1, 1, 2)

        self.lbl_env_status = QLabel("● Probing")
        self.lbl_env_status.setStyleSheet("color: #a6adc8; font-size: 11px;")
        grid.addWidget(self.lbl_env_status, 0, 3)

        # 1. Architecture
        grid.addWidget(QLabel("Architecture:"), 1, 0)
        self.combo_arch = QComboBox()
        self.combo_arch.addItems(SUPPORTED_ARCHITECTURES)
        self.combo_arch.currentTextChanged.connect(self._on_arch_changed)
        grid.addWidget(self.combo_arch, 1, 1)

        # 2. Device
        grid.addWidget(QLabel("Compute Device:"), 1, 2)
        self.combo_device = QComboBox()
        self.combo_device.addItems(["cpu", "cuda", "mps", "xpu"])
        grid.addWidget(self.combo_device, 1, 3)

        # 3. Model weights / preset
        grid.addWidget(QLabel("Model Path / Name:"), 2, 0)
        model_layout = QHBoxLayout()
        model_layout.setContentsMargins(0, 0, 0, 0)
        self.input_model = QLineEdit()
        self.input_model.setPlaceholderText("Leave empty for default foundational model")
        model_layout.addWidget(self.input_model)

        self.btn_browse_model = QPushButton("Browse...")
        self.btn_browse_model.clicked.connect(self._browse_model)
        model_layout.addWidget(self.btn_browse_model)
        grid.addLayout(model_layout, 2, 1, 1, 3)

        # 4. Options: Dispersion & Emissions Tracker
        options_layout = QHBoxLayout()
        self.chk_dispersion = QCheckBox("Empirical Dispersion (D3)")
        options_layout.addWidget(self.chk_dispersion)

        self.chk_tracker = QCheckBox("Track Carbon Emissions (CodeCarbon)")
        self.chk_tracker.setChecked(False)  # User rule: default no-tracker
        self.chk_tracker.setToolTip("Track emissions with CodeCarbon (disabled by default to prevent overhead)")
        options_layout.addWidget(self.chk_tracker)
        options_layout.addStretch()

        grid.addLayout(options_layout, 3, 0, 1, 4)

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
