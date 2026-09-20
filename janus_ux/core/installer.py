"""Asynchronous package installer for multi-environment MLIP setup using uv."""

from __future__ import annotations

import os
import subprocess

from PySide6.QtCore import QThread, Signal


class PackageInstaller(QThread):
    """Background worker to install MLIP packages into a specific environment using uv."""  # noqa: E501

    log_line = Signal(str)
    finished_install = Signal(bool, str)

    def __init__(self, python_path: str, packages: list[str], parent=None):
        super().__init__(parent)
        self.python_path = python_path
        self.packages = packages
        self._process = None

    def run(self):
        """Run."""
        pkg_str = " ".join(self.packages)
        self.log_line.emit(
            f"[INFO] Installing: {pkg_str} into {self.python_path} via uv..."
        )

        cmd = ["uv", "pip", "install"] + self.packages + ["--python", self.python_path]
        try:
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"

            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
            )

            if self._process.stdout:
                for line in iter(self._process.stdout.readline, ""):
                    line_clean = line.rstrip()
                    if line_clean:
                        self.log_line.emit(line_clean)

            self._process.wait()
            ret = self._process.returncode
            if ret == 0:
                self.log_line.emit(f"[SUCCESS] Successfully installed {pkg_str}!")
                self.finished_install.emit(True, f"Installed {pkg_str}")
            else:
                self.log_line.emit(
                    f"[ERROR] uv pip install failed with exit code {ret}"
                )
                self.finished_install.emit(
                    False, f"Installation failed (exit code {ret})"
                )
        except Exception as e:
            self.log_line.emit(f"[ERROR] Exception during installation: {str(e)}")
            self.finished_install.emit(False, str(e))
