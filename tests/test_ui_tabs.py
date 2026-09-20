"""Tests for MainWindow and calculation tabs initialization."""

import pytest
from PySide6.QtWidgets import QApplication
from janus_ux.app import MainWindow
from janus_ux.tabs import (
    GeomOptTab,
    SinglePointTab,
    MDTab,
    PhononsTab,
    EOSTab,
    ElasticityTab,
    NEBTab,
    DescriptorsTab,
)

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

def test_tabs_initialization(qapp):
    t_opt = GeomOptTab()
    assert t_opt.combo_optimizer.count() > 0
    assert t_opt.combo_filter.currentText() == "FrechetCellFilter"

    t_sp = SinglePointTab()
    assert t_sp.chk_energy.isChecked()

    t_md = MDTab()
    assert t_md.combo_ensemble.currentText() == "nvt"

    t_ph = PhononsTab()
    assert t_ph.sc_x.value() == 2

    t_eos = EOSTab()
    assert t_eos.spin_npoints.value() == 9

    t_elast = ElasticityTab()
    assert t_elast.table_cij.rowCount() == 6

    t_neb = NEBTab()
    assert t_neb.spin_images.value() == 5

    t_desc = DescriptorsTab()
    assert t_desc.chk_invariants.isChecked()

def test_main_window(qapp):
    win = MainWindow()
    assert win.tab_widget.count() == 9
    assert "Geometry Optimization" in win.tab_widget.tabText(0)
    assert "Single Point" in win.tab_widget.tabText(1)
    assert "Environments" in win.tab_widget.tabText(8)

    # Verify model selection is independent of run mode and shared across all tabs
    assert win.calc_selector is not None
    assert win.tab_geomopt.calc_selector is win.calc_selector
    assert win.tab_singlepoint.calc_selector is win.calc_selector
    assert win.tab_md.calc_selector is win.calc_selector
    assert win.tab_phonons.calc_selector is win.calc_selector
    assert win.tab_eos.calc_selector is win.calc_selector
    assert win.tab_elasticity.calc_selector is win.calc_selector
    assert win.tab_neb.calc_selector is win.calc_selector
    assert win.tab_descriptors.calc_selector is win.calc_selector

    # Changing model selection globally affects all calculation modes
    win.calc_selector.combo_arch.setCurrentText("sevennet")
    assert win.tab_geomopt.calc_selector.combo_arch.currentText() == "sevennet"
    assert win.tab_singlepoint.calc_selector.combo_arch.currentText() == "sevennet"
    cli_args = win.tab_geomopt.calc_selector.get_cli_args()
    assert "--arch" in cli_args
    assert "sevennet" in cli_args

def test_singlepoint_cli_args(qapp, tmp_path, monkeypatch):
    t_sp = SinglePointTab()
    from ase import Atoms
    import ase.io
    atoms = Atoms("Si2", positions=[[0, 0, 0], [1.36, 1.36, 1.36]], cell=[5.43, 5.43, 5.43], pbc=True)
    test_file = tmp_path / "si.xyz"
    ase.io.write(str(test_file), atoms)

    t_sp.load_structure_file(str(test_file))
    t_sp.chk_forces.setChecked(True)
    t_sp.chk_stress.setChecked(True)

    captured_args = []
    from janus_ux.core.runner import CalcRunner
    orig_init = CalcRunner.__init__
    def fake_init(self, command, args, **kwargs):
        captured_args.extend(args)
        orig_init(self, command, args, **kwargs)
    monkeypatch.setattr(CalcRunner, "__init__", fake_init)
    monkeypatch.setattr(CalcRunner, "start", lambda self: None)

    t_sp.run_singlepoint()

    assert "--properties" in captured_args
    assert "--property" not in captured_args
