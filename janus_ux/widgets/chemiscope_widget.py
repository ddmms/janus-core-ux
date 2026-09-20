"""Chemiscope 3D Atomic Structure and Trajectory Visualizer embedded in QWebEngineView."""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any

from ase import Atoms
import chemiscope
from PySide6.QtCore import QUrl, Signal, Slot
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from janus_ux.core.parser import extract_trajectory_properties


class ChemiscopeWidget(QWidget):
    """Embeds Chemiscope inside a PySide6 QWebEngineView for interactive 3D structures and linked maps."""

    structure_selected = Signal(int)

    def __init__(self, parent=None, default_mode: str = "default"):
        super().__init__(parent)
        self.default_mode = (
            default_mode  # "default" (map + struct) or "structure" (3D only)
        )
        self.current_structures: list[Atoms] = []
        self._temp_html_path = os.path.join(
            tempfile.gettempdir(), f"chemiscope_{id(self)}.html"
        )

        # Static assets
        chemiscope_pkg = os.path.dirname(chemiscope.__file__)
        self.static_dir = os.path.join(chemiscope_pkg, "sphinx", "static")
        self.js_path = os.path.join(self.static_dir, "chemiscope.min.js")
        self.css_path = os.path.join(self.static_dir, "chemiscope-sphinx.css")

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Mini control header
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 4, 8, 4)
        header_layout.setSpacing(8)

        self.title_label = QLabel("3D Visualizer (Chemiscope)")
        self.title_label.setStyleSheet("font-weight: bold; color: #89b4fa;")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        self.status_label = QLabel("No structure loaded")
        self.status_label.setStyleSheet("color: #6c7086; font-size: 11px;")
        header_layout.addWidget(self.status_label)

        self.btn_reset_view = QPushButton("Reset View")
        self.btn_reset_view.setToolTip("Reset 3D camera orientation")
        self.btn_reset_view.clicked.connect(self.reset_camera)
        header_layout.addWidget(self.btn_reset_view)

        layout.addWidget(header)

        # WebEngine View
        self.web_view = QWebEngineView()
        self.web_view.setStyleSheet("background-color: #181825; border-radius: 6px;")
        layout.addWidget(self.web_view, stretch=1)

        self._load_placeholder()

    def _load_placeholder(self):
        html = """<!DOCTYPE html>
        <html>
        <body style="background:#181825; color:#6c7086; font-family:sans-serif; display:flex; justify-content:center; align-items:center; height:90vh; margin:0;">
            <div style="text-align:center;">
                <h3 style="color:#89b4fa; margin-bottom:8px;">Chemiscope 3D Visualizer</h3>
                <p>Select or run a calculation to visualize atomic structures.</p>
            </div>
        </body>
        </html>"""
        self.web_view.setHtml(html)

    def load_atoms(self, atoms: Atoms, properties: dict[str, Any] | None = None):
        """Display a single atomic structure in 3D Structure mode."""
        self.load_trajectory([atoms], properties=properties, mode="structure")

    def load_trajectory(
        self,
        traj: list[Atoms],
        properties: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
        mode: str | None = None,
    ):
        """Display multiple atomic frames with interactive linked 2D/3D map and playback."""
        if not traj:
            self._load_placeholder()
            return

        self.current_structures = traj
        n_frames = len(traj)
        mode = mode or ("structure" if n_frames == 1 else "default")

        self.status_label.setText(
            f"{n_frames} configuration{'s' if n_frames > 1 else ''}"
        )

        # Extract properties if not provided
        if properties is None:
            properties = extract_trajectory_properties(traj)

        # Default settings
        if settings is None:
            settings = {
                "structure": [
                    {
                        "unitCell": True,
                        "bonds": True,
                        "spaceFilling": False,
                    }
                ]
            }
            if "Energy" in properties:
                settings["map"] = {
                    "x": {"property": "Step"},
                    "y": {"property": "Energy"},
                }

        # Build Chemiscope JSON input
        try:
            dataset = chemiscope.create_input(
                traj,
                properties=properties,
                settings=settings,
            )
        except Exception as e:
            print(f"Error creating chemiscope dataset: {e}")
            dataset = chemiscope.create_input(traj)

        dataset_json = json.dumps(dataset)
        self._render_chemiscope_html(dataset_json, mode)

    def _render_chemiscope_html(self, dataset_json: str, mode: str):
        """Write and load the Chemiscope container HTML into the QWebEngineView."""
        css_content = (
            open(self.css_path, encoding="utf-8").read()
            if os.path.exists(self.css_path)
            else ""
        )

        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
html, body {{
    margin: 0;
    padding: 0;
    width: 100vw;
    height: 100vh;
    overflow: hidden;
    background: #181825;
    color: #cdd6f4;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}}
{css_content}
.chemiscope-sphinx {{
    width: 100% !important;
    height: 100% !important;
}}
.visualizer-container {{
    display: flex;
    width: 100%;
    height: 100%;
    box-sizing: border-box;
}}
#chsp-map {{
    flex: 1.1;
    height: 100%;
    min-width: 0;
}}
#chsp-struct {{
    flex: 1;
    height: 100%;
    min-width: 0;
}}
#chsp-info {{
    display: none;
}}
#chsp-meta {{
    display: none;
}}
</style>
<script src="file://{self.js_path}"></script>
</head>
<body>
<div class="chemiscope-sphinx">
    <div class="visualizer-container">
        {'<div id="chsp-map"></div>' if mode == "default" else ""}
        <div id="chsp-struct" style="{"flex:1;" if mode == "structure" else ""}"></div>
        <div id="chsp-info"></div>
        <div id="chsp-meta"></div>
    </div>
</div>
<script>
window.dataset = {dataset_json};
window.visualizerMode = '{mode}';

async function initChemiscope() {{
    try {{
        const config = {{
            map: 'chsp-map',
            structure: 'chsp-struct',
            info: 'chsp-info',
            meta: 'chsp-meta'
        }};
        const warnings = new Chemiscope.Warnings();
        warnings.addHandler(() => {{}});
        if (window.visualizerMode === 'structure') {{
            window.vis = await Chemiscope.StructureVisualizer.load(config, window.dataset, warnings);
        }} else {{
            window.vis = await Chemiscope.DefaultVisualizer.load(config, window.dataset, warnings);
        }}
    }} catch (err) {{
        console.error("Chemiscope initialization error:", err);
    }}
}}

window.addEventListener('DOMContentLoaded', initChemiscope);
</script>
</body>
</html>
"""
        with open(self._temp_html_path, "w", encoding="utf-8") as f:
            f.write(html)

        self.web_view.load(QUrl.fromLocalFile(self._temp_html_path))

    @Slot(int)
    def select_frame(self, index: int):
        """Select a specific structure / frame in Chemiscope programmatically."""
        js_code = f"""
        if (window.vis) {{
            if (window.vis.structure && typeof window.vis.structure.show === 'function') {{
                window.vis.structure.show({index});
            }} else if (window.vis.map && typeof window.vis.map.select === 'function') {{
                window.vis.map.select({index});
            }}
        }}
        """
        self.web_view.page().runJavaScript(js_code)

    @Slot()
    def reset_camera(self):
        """Reset camera orientation."""
        js_code = """
        if (window.vis && window.vis.structure && typeof window.vis.structure.resetCamera === 'function') {
            window.vis.structure.resetCamera();
        }
        """
        self.web_view.page().runJavaScript(js_code)
