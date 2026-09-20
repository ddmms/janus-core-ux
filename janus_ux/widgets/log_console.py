"""Real-time log console widget with colorized output and search filtering."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QPushButton,
    QCheckBox,
    QLineEdit,
    QLabel,
)
from PySide6.QtGui import QTextCursor, QColor
from PySide6.QtCore import Slot

class LogConsole(QWidget):
    """Terminal-like log viewer widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Control toolbar
        bar = QHBoxLayout()
        bar.setContentsMargins(2, 2, 2, 2)
        lbl = QLabel("Execution Logs")
        lbl.setStyleSheet("font-weight: 600; color: #b4befe;")
        bar.addWidget(lbl)

        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("Filter logs...")
        self.input_search.textChanged.connect(self._filter_logs)
        bar.addWidget(self.input_search)

        self.chk_autoscroll = QCheckBox("Auto-scroll")
        self.chk_autoscroll.setChecked(True)
        bar.addWidget(self.chk_autoscroll)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self.clear)
        bar.addWidget(self.btn_clear)

        layout.addLayout(bar)

        # Text area
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setStyleSheet(
            "background-color: #11111b; color: #cdd6f4; font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace; font-size: 12px; border: 1px solid #313244; border-radius: 6px;"
        )
        layout.addWidget(self.text_area)

        self._all_lines = []

    @Slot(str)
    def append_log(self, text: str):
        """Append a log line with syntax coloring."""
        self._all_lines.append(text)

        color_hex = "#cdd6f4"
        if "[SUCCESS]" in text or "complete" in text.lower() or "converged" in text.lower():
            color_hex = "#a6e3a1"  # green
        elif "[ERROR]" in text or "error" in text.lower() or "traceback" in text.lower():
            color_hex = "#f38ba8"  # red
        elif "[WARNING]" in text or "warn" in text.lower():
            color_hex = "#fab387"  # peach
        elif "[INFO]" in text or "starting" in text.lower():
            color_hex = "#89b4fa"  # blue

        html_line = f'<span style="color: {color_hex};">{text}</span>'
        self.text_area.append(html_line)

        if self.chk_autoscroll.isChecked():
            self.text_area.moveCursor(QTextCursor.End)

    def clear(self):
        self._all_lines.clear()
        self.text_area.clear()

    def _filter_logs(self, query: str):
        query = query.strip().lower()
        if not query:
            self.text_area.clear()
            for line in self._all_lines:
                self.append_log(line)
            return

        self.text_area.clear()
        for line in self._all_lines:
            if query in line.lower():
                self.append_log(line)
