"""Tests for CalcRunner background worker."""

from __future__ import annotations

from janus_ux.core.runner import CalcRunner


def test_calc_runner_init():
    """Test Calc runner init."""
    runner = CalcRunner(
        "geomopt",
        ["--steps", "50"],
        cwd="/tmp",
        python_path="/opt/micromamba/envs/janus/bin/python",
    )
    assert runner.command == "geomopt"
    assert runner.args == ["--steps", "50"]
    assert runner.python_path == "/opt/micromamba/envs/janus/bin/python"
    assert not runner._is_cancelled


def test_calc_runner_cancellation():
    """Test Calc runner cancellation."""
    runner = CalcRunner("md", ["--steps", "1000"])
    runner.cancel()
    assert runner._is_cancelled
