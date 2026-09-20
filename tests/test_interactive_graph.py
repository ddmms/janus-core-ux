"""Tests for InteractiveGraph widget and click picking signals."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication
import pytest

from janus_ux.widgets.interactive_graph import InteractiveGraph


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_interactive_graph_init(qapp):
    graph = InteractiveGraph(title="Test Convergence")
    assert graph.plot_title == "Test Convergence"
    assert graph.web_view is not None


def test_interactive_graph_click_signal(qapp):
    graph = InteractiveGraph(title="Test Plot")
    clicked_indices = []
    graph.point_clicked.connect(lambda idx: clicked_indices.append(idx))

    # Simulate title change indicating click
    graph._handle_title_change("POINT_CLICK:4")
    assert clicked_indices == [4]

    graph._handle_title_change("POINT_CLICK:12")
    assert clicked_indices == [4, 12]


def test_interactive_graph_plot_curve(qapp):
    graph = InteractiveGraph()
    x = [0, 1, 2, 3]
    y = [-10.0, -10.5, -10.8, -10.9]
    graph.plot_curve(x, y, x_label="Step", y_label="Energy (eV)")
    assert graph.web_view is not None
