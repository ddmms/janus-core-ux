"""Structure Inspector Widget displaying atomic and unit cell properties."""

from typing import Optional
import numpy as np
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QLineEdit,
    QHeaderView,
)
from PySide6.QtCore import Qt
from ase import Atoms

class StructureInspector(QWidget):
    """Displays chemical formula, unit cell vectors, angles, density, and atomic coordinates."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_atoms: Optional[Atoms] = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        # Overview Card
        overview_group = QGroupBox("Crystallographic Summary")
        ov_layout = QGridLayout(overview_group)
        ov_layout.setHorizontalSpacing(12)
        ov_layout.setVerticalSpacing(4)

        self.lbl_formula = QLabel("Formula: -")
        self.lbl_formula.setStyleSheet("font-weight: bold; color: #89b4fa;")
        ov_layout.addWidget(self.lbl_formula, 0, 0)

        self.lbl_natoms = QLabel("Atoms: 0")
        ov_layout.addWidget(self.lbl_natoms, 0, 1)

        self.lbl_pbc = QLabel("PBC: [False, False, False]")
        ov_layout.addWidget(self.lbl_pbc, 0, 2)

        self.lbl_lengths = QLabel("Cell: a=-, b=-, c=- Å")
        ov_layout.addWidget(self.lbl_lengths, 1, 0)

        self.lbl_angles = QLabel("Angles: α=-, β=-, γ=- °")
        ov_layout.addWidget(self.lbl_angles, 1, 1)

        self.lbl_volume = QLabel("Volume: - Å³")
        ov_layout.addWidget(self.lbl_volume, 1, 2)

        layout.addWidget(overview_group)

        # Coordinates table with quick filter
        table_group = QGroupBox("Atomic Coordinates")
        t_layout = QVBoxLayout(table_group)
        t_layout.setContentsMargins(6, 6, 6, 6)
        t_layout.setSpacing(4)

        self.input_filter = QLineEdit()
        self.input_filter.setPlaceholderText("Filter by element symbol (e.g. Si, O)...")
        self.input_filter.textChanged.connect(self._apply_filter)
        t_layout.addWidget(self.input_filter)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Index", "Element", "X (Å)", "Y (Å)", "Z (Å)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        t_layout.addWidget(self.table)

        layout.addWidget(table_group, stretch=1)

    def load_structure(self, atoms: Optional[Atoms]):
        """Populate the inspector with details from an ASE Atoms object."""
        self._current_atoms = atoms
        if atoms is None:
            self.lbl_formula.setText("Formula: -")
            self.lbl_natoms.setText("Atoms: 0")
            self.lbl_pbc.setText("PBC: -")
            self.lbl_lengths.setText("Cell: -")
            self.lbl_angles.setText("Angles: -")
            self.lbl_volume.setText("Volume: -")
            self.table.setRowCount(0)
            return

        formula = atoms.get_chemical_formula()
        n_atoms = len(atoms)
        pbc = atoms.get_pbc()

        self.lbl_formula.setText(f"Formula: {formula}")
        self.lbl_natoms.setText(f"Atoms: {n_atoms}")
        self.lbl_pbc.setText(f"PBC: [{int(pbc[0])}, {int(pbc[1])}, {int(pbc[2])}]")

        cell = atoms.get_cell()
        if atoms.pbc.any():
            a, b, c = cell.lengths()
            alpha, beta, gamma = cell.angles()
            vol = atoms.get_volume()
            self.lbl_lengths.setText(f"Cell: a={a:.2f}, b={b:.2f}, c={c:.2f} Å")
            self.lbl_angles.setText(f"Angles: α={alpha:.1f}°, β={beta:.1f}°, γ={gamma:.1f}°")
            self.lbl_volume.setText(f"Volume: {vol:.2f} Å³")
        else:
            self.lbl_lengths.setText("Cell: Non-periodic")
            self.lbl_angles.setText("Angles: N/A")
            self.lbl_volume.setText("Volume: N/A")

        self._populate_table()

    def _populate_table(self):
        if self._current_atoms is None:
            return

        positions = self._current_atoms.get_positions()
        symbols = self._current_atoms.get_chemical_symbols()
        filter_text = self.input_filter.text().strip().lower()

        rows = []
        for i, (sym, pos) in enumerate(zip(symbols, positions)):
            if filter_text and filter_text not in sym.lower():
                continue
            rows.append((i, sym, pos[0], pos[1], pos[2]))

        self.table.setRowCount(len(rows))
        for r_idx, (orig_i, sym, x, y, z) in enumerate(rows):
            item_i = QTableWidgetItem(str(orig_i))
            item_i.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r_idx, 0, item_i)

            item_s = QTableWidgetItem(sym)
            item_s.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r_idx, 1, item_s)

            for c_idx, val in enumerate([x, y, z], start=2):
                item_v = QTableWidgetItem(f"{val:.4f}")
                item_v.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(r_idx, c_idx, item_v)

    def _apply_filter(self):
        self._populate_table()
