"""Asynchronous calculation runner for Janus Core operations using QThread."""

import os
import sys
import subprocess
import tempfile
from typing import Dict, Any, List, Optional
from PySide6.QtCore import QThread, Signal

class CalcRunner(QThread):
    """Background worker thread to execute janus CLI or python commands in a chosen environment."""

    log_line = Signal(str)
    progress = Signal(float, str)
    finished_calculation = Signal(bool, str, dict)

    def __init__(
        self,
        command: str,
        args: List[str],
        cwd: Optional[str] = None,
        expected_output_files: Optional[Dict[str, str]] = None,
        python_path: Optional[str] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.command = command
        self.args = args
        self.cwd = cwd or tempfile.gettempdir()
        self.expected_output_files = expected_output_files or {}
        self.python_path = python_path
        self._is_cancelled = False
        self._process: Optional[subprocess.Popen] = None

    def run(self):
        self._is_cancelled = False

        # Determine binary / invocation command based on target environment
        target_py = self.python_path or "/opt/micromamba/envs/janus/bin/python"
        if not os.path.exists(target_py):
            target_py = sys.executable

        bin_dir = os.path.dirname(target_py)
        janus_bin = os.path.join(bin_dir, "janus")

        if os.path.exists(janus_bin):
            full_cmd = [janus_bin, self.command] + self.args
        else:
            # Fallback to uv run or python module execution
            full_cmd = [target_py, "-m", "janus_core.cli.janus", self.command] + self.args

        cmd_str = " ".join(full_cmd)
        self.log_line.emit(f"[INFO] Target Environment Python: {target_py}")
        self.log_line.emit(f"[INFO] Launching command: {cmd_str}")
        self.log_line.emit(f"[INFO] Working directory: {self.cwd}")

        try:
            # Setup environment with target bin directory prioritized in PATH
            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
            env["PYTHONUNBUFFERED"] = "1"
            env["CODECARBON_LOG_LEVEL"] = "ERROR"

            self._process = subprocess.Popen(
                full_cmd,
                cwd=self.cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
            )

            if self._process.stdout:
                for line in iter(self._process.stdout.readline, ""):
                    if self._is_cancelled:
                        break
                    line_clean = line.rstrip()
                    if line_clean:
                        self.log_line.emit(line_clean)

            self._process.wait()

            if self._is_cancelled:
                self.log_line.emit("[WARNING] Calculation was cancelled by user.")
                self.finished_calculation.emit(False, "Cancelled by user", {})
                return

            return_code = self._process.returncode
            if return_code == 0:
                self.log_line.emit("[SUCCESS] Calculation finished successfully!")
                self.finished_calculation.emit(
                    True, "Completed successfully", self.expected_output_files
                )
            else:
                self.log_line.emit(f"[ERROR] Process exited with error code {return_code}")
                self.finished_calculation.emit(
                    False, f"Exited with code {return_code}", {}
                )

        except Exception as e:
            self.log_line.emit(f"[ERROR] Exception during execution: {str(e)}")
            self.finished_calculation.emit(False, str(e), {})

    def cancel(self):
        """Cancel the running process."""
        self._is_cancelled = True
        if self._process and self._process.poll() is None:
            try:
                self._process.terminate()
                self.log_line.emit("[INFO] Sent terminate signal to process...")
            except Exception:
                pass
