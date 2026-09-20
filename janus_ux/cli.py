"""CLI entrypoint using Typer and Argparse for Janus Core UX."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Annotated

from PySide6.QtCore import Qt  # noqa: F401
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
import typer

from janus_ux import __version__
from janus_ux.app import MainWindow
from janus_ux.core.desktop_integration import get_asset_path, install_desktop_entry

app = typer.Typer(
    name="janus-core-ux",
    help="Janus-Core UX - Desktop GUI for STFC janus-core atomistic simulations.",
    add_completion=False,
)


def build_argparser() -> argparse.ArgumentParser:
    """Construct an argparse.ArgumentParser matching the CLI options."""
    parser = argparse.ArgumentParser(
        prog="janus-core-ux",
        description="Desktop UX for STFC janus-core atomistic simulations.",
    )
    parser.add_argument(
        "structure",
        nargs="?",
        type=Path,
        default=None,
        help="Path to atomic structure file (.cif, .xyz, etc.) to load on launch.",
    )
    parser.add_argument(
        "--tab",
        "-t",
        type=str,
        default=None,
        help="Initial tab to select (e.g. geomopt, singlepoint, md, phonons, eos, elasticity, neb, descriptors, environments).",  # noqa: E501
    )
    parser.add_argument(
        "--install-desktop",
        action="store_true",
        help="Install .desktop shortcut and application icons to system menu.",
    )
    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version=f"janus-core-ux {__version__}",
        help="Show application version and exit.",
    )
    parser.add_argument(
        "--arch",
        "-a",
        type=str,
        default=None,
        help="Initial MLIP architecture (mace_mp, sevennet, chgnet, etc.).",
    )
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default=None,
        help="Initial MLIP model name or file path.",
    )
    parser.add_argument(
        "--device",
        "-d",
        type=str,
        default=None,
        help="Compute device (cpu, cuda, mps, xpu).",
    )
    return parser


def launch_gui(
    structure: Path | None = None,
    tab: str | None = None,
    arch: str | None = None,
    model: str | None = None,
    device: str | None = None,
) -> int:
    """Launch the Qt application window."""
    # Ensure QApplication exists
    qapp = QApplication.instance()
    if qapp is None:
        qapp = QApplication(sys.argv[:1])

    qapp.setApplicationName("Janus-Core UX")
    qapp.setOrganizationName("STFC")

    icon_path = get_asset_path("janus-core.png")
    if not icon_path.exists():
        icon_path = get_asset_path("icon.png")
    if icon_path.exists():
        qapp.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow(
        structure_path=structure,
        initial_tab=tab,
        arch=arch,
        model=model,
        device=device,
    )
    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))

    window.show()
    return qapp.exec()


@app.command()
def cli_main(
    structure: Annotated[
        Path | None,
        typer.Argument(
            help="Path to atomic structure file (.cif, .xyz, etc.) to load on launch."
        ),
    ] = None,
    tab: Annotated[
        str | None,
        typer.Option(
            "--tab",
            "-t",
            help="Initial calculation tab to select.",
        ),
    ] = None,
    install_desktop: Annotated[
        bool,
        typer.Option(
            "--install-desktop",
            help="Install .desktop shortcut and application icons to system menu.",
        ),
    ] = False,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            help="Show application version and exit.",
        ),
    ] = False,
    arch: Annotated[
        str | None,
        typer.Option(
            "--arch",
            "-a",
            help="Initial MLIP architecture (mace_mp, sevennet, chgnet, etc.).",
        ),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option(
            "--model",
            "-m",
            help="Initial MLIP model name or file path.",
        ),
    ] = None,
    device: Annotated[
        str | None,
        typer.Option(
            "--device",
            "-d",
            help="Compute device (cpu, cuda, mps, xpu).",
        ),
    ] = None,
):
    """Launch the Janus Core Desktop UX."""
    if version:
        typer.echo(f"janus-core-ux {__version__}")
        raise typer.Exit(0)

    if install_desktop:
        success = install_desktop_entry()
        if success:
            typer.echo("Desktop shortcut and application icon installed successfully!")
            raise typer.Exit(0)
        typer.echo("Failed to install desktop shortcut.", err=True)
        raise typer.Exit(1)

    sys.exit(
        launch_gui(
            structure=structure,
            tab=tab,
            arch=arch,
            model=model,
            device=device,
        )
    )


def main_argparse(argv: list[str] | None = None) -> int:
    """Run CLI using argparse parser."""
    parser = build_argparser()
    args = parser.parse_args(argv)

    if args.install_desktop:
        success = install_desktop_entry()
        if success:
            print("Desktop shortcut and application icon installed successfully!")
            return 0
        print("Failed to install desktop shortcut.", file=sys.stderr)
        return 1

    return launch_gui(
        structure=args.structure,
        tab=args.tab,
        arch=args.arch,
        model=args.model,
        device=args.device,
    )


def main():
    """Execute main CLI entrypoint."""
    app()


if __name__ == "__main__":
    main()
