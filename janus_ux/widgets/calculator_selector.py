"""MLIP Calculator selection, device configuration, and execution environment selector."""  # noqa: E501

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
)

from janus_ux.core.env_manager import EnvConfig, EnvironmentManager
from janus_ux.core.models import DEFAULT_MODELS, SUPPORTED_ARCHITECTURES


class CalculatorSelector(QGroupBox):
    """Configuration panel for MLIP Architecture, Model weights, Device, and Target Environment."""  # noqa: E501

    selection_changed = Signal()

    def __init__(
        self,
        parent=None,
        title="⚙️ Global MLIP Potential & Target Environment (Applied to all calculation modes)",  # noqa: E501
    ):
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
        self.combo_env.setToolTip(
            "Select the environment containing the desired MLIP model"
        )
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
        self.combo_device.currentTextChanged.connect(
            lambda: self.selection_changed.emit()
        )
        grid.addWidget(self.combo_device, 0, 5)

        # Row 1: Model weights / path and Options
        grid.addWidget(QLabel("Model Path / Name:"), 1, 0)
        model_layout = QHBoxLayout()
        model_layout.setContentsMargins(0, 0, 0, 0)
        self.input_model = QLineEdit()
        self.input_model.setPlaceholderText(
            "Leave empty for default foundational model"
        )
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
        self.chk_tracker.setToolTip(
            "Track emissions with CodeCarbon (disabled by default to prevent overhead)"
        )
        self.chk_tracker.toggled.connect(lambda: self.selection_changed.emit())
        options_layout.addWidget(self.chk_tracker)
        grid.addLayout(options_layout, 1, 4, 1, 2)

        # Row 2: Model Head and Extra Calc-Kwargs
        grid.addWidget(QLabel("Model Head:"), 2, 0)
        self.input_head = QLineEdit()
        self.input_head.setPlaceholderText("Optional calculator head (e.g. mpa0)")
        self.input_head.setToolTip(
            "Task head for multi-head models (passed via calc-kwargs)"
        )
        self.input_head.textChanged.connect(lambda: self.selection_changed.emit())
        grid.addWidget(self.input_head, 2, 1)

        grid.addWidget(QLabel("Extra Calc-Kwargs:"), 2, 2)
        self.input_calc_kwargs = QLineEdit()
        self.input_calc_kwargs.setPlaceholderText(
            "e.g. {'default_dtype': 'float32'}"
        )
        self.input_calc_kwargs.setToolTip(
            "Additional keyword arguments for calculator (passed via calc-kwargs as dict)"
        )
        self.input_calc_kwargs.textChanged.connect(
            lambda: self.selection_changed.emit()
        )
        grid.addWidget(self.input_calc_kwargs, 2, 3, 1, 3)

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
            self,
            "Select MLIP Model Weights",
            "",
            "Model Files (*.model *.pt *.pth *.pt.tar);;All Files (*)",
        )
        if filename:
            self.input_model.setText(filename)

    def get_selected_env(self) -> EnvConfig | None:
        """Return the EnvConfig object for the currently selected environment."""
        env_name = self.combo_env.currentData()
        if env_name:
            return self.env_mgr.get_environment(env_name)
        return self.env_mgr.get_default_environment()

    def get_selected_python(self) -> str | None:
        """Return python path of the selected environment."""
        env = self.get_selected_env()
        return env.python_path if env else None

    def get_calc_kwargs_dict(self) -> dict:
        """Return calculator keyword arguments as a python dict for --calc-kwargs."""
        kwargs: dict = {}
        if self.chk_dispersion.isChecked():
            kwargs["dispersion"] = True

        if hasattr(self, "input_head"):
            head = self.input_head.text().strip()
            if head:
                kwargs["head"] = head

        if hasattr(self, "input_calc_kwargs"):
            extra_text = self.input_calc_kwargs.text().strip()
            if extra_text:
                try:
                    import ast

                    val = ast.literal_eval(extra_text)
                    if isinstance(val, dict):
                        kwargs.update(val)
                except Exception:
                    pass

        return kwargs

    def get_cli_args(self) -> list[str]:
        """Generate CLI flags for janus command line execution."""
        args = [
            "--arch",
            self.combo_arch.currentText(),
            "--device",
            self.combo_device.currentText(),
        ]

        model = self.input_model.text().strip()
        if model:
            args.extend(["--model", model])

        calc_kwargs = self.get_calc_kwargs_dict()
        if calc_kwargs:
            args.extend(["--calc-kwargs", str(calc_kwargs)])

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
        calc_kwargs = self.get_calc_kwargs_dict()
        if calc_kwargs:
            res["calc_kwargs"] = calc_kwargs
        return res
