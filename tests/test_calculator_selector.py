"""Tests for CalculatorSelector widget."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication
import pytest

from janus_ux.widgets.calculator_selector import CalculatorSelector


@pytest.fixture(scope="session")
def qapp():
    """Provide qapp fixture."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_calculator_selector_defaults(qapp):
    """Test Calculator selector defaults."""
    selector = CalculatorSelector()
    args = selector.get_cli_args()

    assert "--arch" in args
    assert "mace_mp" in args
    assert "--device" in args
    assert "cpu" in args
    assert "--no-tracker" in args  # Default per user rule


def test_calculator_selector_custom(qapp):
    """Test Calculator selector custom."""
    import ast

    selector = CalculatorSelector()
    selector.combo_arch.setCurrentText("sevennet")
    selector.combo_device.setCurrentText("cuda")
    selector.chk_dispersion.setChecked(True)
    selector.chk_tracker.setChecked(True)

    args = selector.get_cli_args()
    assert args[args.index("--arch") + 1] == "sevennet"
    assert args[args.index("--device") + 1] == "cuda"
    assert "--dispersion" not in args
    assert "--calc-kwargs" in args
    kw_dict = ast.literal_eval(args[args.index("--calc-kwargs") + 1])
    assert kw_dict["dispersion"] is True
    assert "--tracker" in args


def test_calculator_selector_calc_kwargs(qapp):
    """Test Calculator selector head and extra calc-kwargs."""
    import ast

    selector = CalculatorSelector()
    selector.chk_dispersion.setChecked(True)
    selector.input_head.setText("mpa0")
    selector.input_calc_kwargs.setText("{'default_dtype': 'float32'}")

    args = selector.get_cli_args()
    assert "--dispersion" not in args
    assert "--head" not in args
    assert "--calc-kwargs" in args

    kw_dict = ast.literal_eval(args[args.index("--calc-kwargs") + 1])
    assert kw_dict["dispersion"] is True
    assert kw_dict["head"] == "mpa0"
    assert kw_dict["default_dtype"] == "float32"

    # Also verify get_calc_kwargs() dict
    res = selector.get_calc_kwargs()
    assert res["calc_kwargs"]["dispersion"] is True
    assert res["calc_kwargs"]["head"] == "mpa0"
    assert res["calc_kwargs"]["default_dtype"] == "float32"
