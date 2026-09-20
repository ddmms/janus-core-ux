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
    selector = CalculatorSelector()
    selector.combo_arch.setCurrentText("sevennet")
    selector.combo_device.setCurrentText("cuda")
    selector.chk_dispersion.setChecked(True)
    selector.chk_tracker.setChecked(True)

    args = selector.get_cli_args()
    assert args[args.index("--arch") + 1] == "sevennet"
    assert args[args.index("--device") + 1] == "cuda"
    assert "--dispersion" in args
    assert "--tracker" in args
