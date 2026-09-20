"""Tests for Janus Core UX CLI with argparse and typer."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from janus_ux import __version__
from janus_ux.cli import app, build_argparser


def test_argparse_build_and_defaults():
    """Test building argparse parser and default arguments."""
    parser = build_argparser()
    args = parser.parse_args([])

    assert args.structure is None
    assert args.tab is None
    assert args.arch is None
    assert args.model is None
    assert args.device is None
    assert args.install_desktop is False


def test_argparse_custom_arguments(tmp_path):
    """Test parsing custom arguments with argparse."""
    test_struct = tmp_path / "test.cif"
    test_struct.write_text("dummy", encoding="utf-8")

    parser = build_argparser()
    args = parser.parse_args(
        [
            str(test_struct),
            "--tab",
            "geomopt",
            "--arch",
            "mace_mp",
            "--model",
            "medium-0b3",
            "--device",
            "cpu",
            "--install-desktop",
        ]
    )

    assert isinstance(args.structure, Path)
    assert args.structure == test_struct
    assert args.tab == "geomopt"
    assert args.arch == "mace_mp"
    assert args.model == "medium-0b3"
    assert args.device == "cpu"
    assert args.install_desktop is True


def test_typer_cli_help():
    """Test typer CLI help option."""
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Janus Core" in result.stdout
    assert "--tab" in result.stdout
    assert "--arch" in result.stdout


def test_typer_cli_version():
    """Test typer CLI version flag."""
    runner = CliRunner()
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"janus-core-ux {__version__}" in result.stdout
