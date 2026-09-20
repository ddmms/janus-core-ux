"""Prominent structure file upload and selection widget with drag-and-drop support."""

from __future__ import annotations

from pathlib import Path

from ase import Atoms
import ase.io
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class StructureFileInput(QWidget):
    """Widget allowing user to upload/browse and inspect atomic structure files."""

    structure_loaded = Signal(object, str)  # (Atoms, filepath)
    structure_cleared = Signal()

    def __init__(
        self,
        title: str = "Input Structure File",
        require_periodic: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.require_periodic = require_periodic
        self.current_atoms: Atoms | None = None
        self._current_path: str = ""

        self.setAcceptDrops(True)
        self._setup_ui(title)

    def _setup_ui(self, title: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        group = QGroupBox(title)
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(6)

        # File selection row
        file_row = QHBoxLayout()
        self.input_file = QLineEdit()
        self.input_file.setPlaceholderText(
            "Select, enter path, or drop structure file (.cif, .xyz, .poscar, .extxyz, ...)"  # noqa: E501
        )
        self.input_file.returnPressed.connect(self._on_path_entered)
        file_row.addWidget(self.input_file)

        self.btn_browse = QPushButton("📂 Upload / Browse...")
        self.btn_browse.setStyleSheet("padding: 6px 12px; font-weight: bold;")
        self.btn_browse.setToolTip(
            "Upload or select an atomic structure file from your system"
        )
        self.btn_browse.clicked.connect(self.browse_file)
        file_row.addWidget(self.btn_browse)

        group_layout.addLayout(file_row)

        # Status info row
        self.lbl_info = QLabel(
            "No structure file uploaded. Please upload a file to proceed."
        )
        self.lbl_info.setStyleSheet("color: #a6adc8; font-size: 11px;")
        group_layout.addWidget(self.lbl_info)

        layout.addWidget(group)

    def dragEnterEvent(self, event):  # noqa: N802
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):  # noqa: N802
        """Handle drop event."""
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path and Path(path).is_file():
                self.load_file(path)
                event.acceptProposedAction()
            else:
                event.ignore()

    def _on_path_entered(self):
        path = self.input_file.text().strip()
        if path:
            self.load_file(path)

    def browse_file(self):
        """Open structure file dialog."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Upload / Select Atomic Structure File",
            "",
            "Atomic Structure Files (*.cif *.xyz *.poscar *.extxyz *.pdb *.json *.gen *.vasp);;All Files (*)",  # noqa: E501
        )
        if filepath:
            self.load_file(filepath)

    def load_file(self, filepath: str | Path) -> bool:
        """Load atomic structure from file with ASE and notify listeners."""
        p = Path(filepath).expanduser().resolve()
        if not p.is_file():
            QMessageBox.critical(self, "File Not Found", f"File does not exist:\n{p}")
            return False

        try:
            atoms = ase.io.read(str(p))
            if self.require_periodic and not atoms.pbc.any():
                QMessageBox.warning(
                    self,
                    "Periodic Boundary Warning",
                    f"The loaded file '{p.name}' does not have periodic boundary conditions (PBC) enabled.\n"  # noqa: E501
                    "This calculation typically requires a 3D periodic crystal unit cell.",  # noqa: E501
                )

            self.current_atoms = atoms
            self._current_path = str(p)
            self.input_file.setText(str(p))

            formula = atoms.get_chemical_formula()
            n_atoms = len(atoms)
            pbc = "Periodic" if atoms.pbc.any() else "Molecule/Cluster"
            filename = p.name
            self.lbl_info.setText(
                f"✓ Loaded: {formula} ({n_atoms} atoms, {pbc}) — {filename}"
            )
            self.lbl_info.setStyleSheet(
                "color: #a6e3a1; font-weight: bold; font-size: 11px;"
            )

            self.structure_loaded.emit(atoms, str(p))
            return True
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error Loading Structure",
                f"Could not parse atomic structure file '{p.name}':\n{e}",  # noqa: E501
            )
            return False

    def clear(self):
        """Clear current structure."""
        self.current_atoms = None
        self._current_path = ""
        self.input_file.clear()
        self.lbl_info.setText(
            "No structure file uploaded. Please upload a file to proceed."
        )
        self.lbl_info.setStyleSheet("color: #a6adc8; font-size: 11px;")
        self.structure_cleared.emit()

    def get_filepath(self) -> str:
        """Return filepath of selected structure."""
        return self._current_path or self.input_file.text().strip()

    def get_atoms(self) -> Atoms | None:
        """Return current Atoms structure."""
        return self.current_atoms
