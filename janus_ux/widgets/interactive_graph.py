"""Interactive 2D & 3D Plotly graphs embedded in QWebEngineView with point picking."""

import os
import json
import tempfile
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl, Signal, Slot
import plotly.graph_objects as go

class InteractiveGraph(QWidget):
    """Interactive Plotly graph with click event emission back to Qt."""

    point_clicked = Signal(int)

    def __init__(self, parent=None, title: str = "Interactive Plot"):
        super().__init__(parent)
        self.plot_title = title
        self._temp_html_path = os.path.join(tempfile.gettempdir(), f"plotly_{id(self)}.html")

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Header
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(6, 2, 6, 2)
        self.header_title = QLabel(self.plot_title)
        self.header_title.setStyleSheet("font-weight: 600; color: #b4befe;")
        header_layout.addWidget(self.header_title)
        header_layout.addStretch()

        self.btn_reset_zoom = QPushButton("Reset Zoom")
        self.btn_reset_zoom.setStyleSheet("font-size: 11px; padding: 3px 8px;")
        self.btn_reset_zoom.clicked.connect(self.reset_axes)
        header_layout.addWidget(self.btn_reset_zoom)
        layout.addWidget(header)

        # WebEngine View
        self.web_view = QWebEngineView()
        self.web_view.setStyleSheet("background-color: #181825; border-radius: 6px;")
        self.web_view.titleChanged.connect(self._handle_title_change)
        layout.addWidget(self.web_view, stretch=1)

        self._load_placeholder()

    def _load_placeholder(self):
        html = """<!DOCTYPE html>
        <html>
        <body style="background:#181825; color:#6c7086; font-family:sans-serif; display:flex; justify-content:center; align-items:center; height:90vh; margin:0;">
            <p>Run a calculation to view interactive curves.</p>
        </body>
        </html>"""
        self.web_view.setHtml(html)

    def _handle_title_change(self, title: str):
        if title.startswith("POINT_CLICK:"):
            try:
                idx_str = title.split(":")[1]
                idx = int(idx_str)
                self.point_clicked.emit(idx)
            except Exception as e:
                print(f"Error parsing clicked point index: {e}")

    def plot_figure(self, fig: go.Figure):
        """Render a Plotly figure with dark styling and click-picking listener."""
        # Update dark layout
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#181825",
            plot_bgcolor="#1e1e2e",
            font=dict(color="#cdd6f4", family="sans-serif", size=11),
            margin=dict(l=50, r=20, t=40, b=45),
            hovermode="closest",
        )
        fig.update_xaxes(
            gridcolor="#313244",
            zerolinecolor="#45475a",
            showline=True,
            linecolor="#45475a",
        )
        fig.update_yaxes(
            gridcolor="#313244",
            zerolinecolor="#45475a",
            showline=True,
            linecolor="#45475a",
        )

        fig_json = fig.to_json()

        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; background: #181825; }}
#plot-div {{ width: 100%; height: 100%; }}
</style>
</head>
<body>
<div id="plot-div"></div>
<script>
const figData = {fig_json};
Plotly.newPlot('plot-div', figData.data, figData.layout, {{responsive: true, displayModeBar: false}}).then(function() {{
    const plotDiv = document.getElementById('plot-div');
    plotDiv.on('plotly_click', function(data) {{
        if (data && data.points && data.points.length > 0) {{
            const pt = data.points[0];
            const ptIdx = pt.pointIndex !== undefined ? pt.pointIndex : pt.pointNumber;
            document.title = "POINT_CLICK:" + ptIdx;
        }}
    }});
}});

function resetAxes() {{
    Plotly.relayout('plot-div', {{
        'xaxis.autorange': true,
        'yaxis.autorange': true
    }});
}}
</script>
</body>
</html>
"""
        with open(self._temp_html_path, "w", encoding="utf-8") as f:
            f.write(html)

        self.web_view.load(QUrl.fromLocalFile(self._temp_html_path))

    def plot_curve(
        self,
        x: List[float],
        y: List[float],
        x_label: str = "Step",
        y_label: str = "Energy (eV)",
        name: str = "Trajectory",
        color: str = "#89b4fa",
        secondary_y: Optional[Dict[str, Any]] = None,
    ):
        """Convenience method to plot a 2D line curve with markers."""
        fig = go.Figure()

        # Primary trace
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="lines+markers",
                name=name,
                line=dict(color=color, width=2.5),
                marker=dict(size=7, color=color, symbol="circle"),
                hovertemplate=f"{x_label}: %{{x}}<br>{y_label}: %{{y:.4f}}<extra></extra>",
            )
        )

        # Secondary trace (e.g. Max Force)
        if secondary_y:
            sec_y_vals = secondary_y.get("values", [])
            sec_name = secondary_y.get("name", "Force")
            sec_color = secondary_y.get("color", "#f38ba8")
            sec_label = secondary_y.get("label", "Max Force (eV/Å)")

            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=sec_y_vals,
                    mode="lines+markers",
                    name=sec_name,
                    yaxis="y2",
                    line=dict(color=sec_color, width=2, dash="dot"),
                    marker=dict(size=6, color=sec_color, symbol="diamond"),
                    hovertemplate=f"{x_label}: %{{x}}<br>{sec_label}: %{{y:.4f}}<extra></extra>",
                )
            )
            fig.update_layout(
                yaxis2=dict(
                    title=sec_label,
                    overlaying="y",
                    side="right",
                    gridcolor="#313244",
                    showgrid=False,
                )
            )

        fig.update_layout(
            xaxis_title=x_label,
            yaxis_title=y_label,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )

        self.plot_figure(fig)

    @Slot()
    def reset_axes(self):
        self.web_view.page().runJavaScript("if (typeof resetAxes === 'function') resetAxes();")
