"""Integration and end-to-end tests for all calculation modes.

Uses NaCl.cif and mace_mp medium-0b3.
"""

from __future__ import annotations

from pathlib import Path
import shutil

import ase.io
from PySide6.QtWidgets import QApplication
import pytest

from janus_ux.core.runner import CalcRunner
from janus_ux.tabs import (
    DescriptorsTab,
    ElasticityTab,
    EOSTab,
    GeomOptTab,
    MDTab,
    NEBTab,
    PhononsTab,
    SinglePointTab,
)
from janus_ux.widgets.calculator_selector import CalculatorSelector

# Detect if mace is importable in the current python runtime
try:
    import mace  # noqa: F401

    HAS_MACE = True
except ImportError:
    HAS_MACE = False


@pytest.fixture(scope="session")
def qapp():
    """Provide qapp fixture."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def nacl_file():
    """Provide nacl_file fixture."""
    path = Path("NaCl.cif").resolve()
    assert path.exists(), f"NaCl.cif not found at {path}"
    return str(path)


def test_modes_cli_args_with_nacl(qapp, nacl_file, monkeypatch):
    """Test all 8 calculation tabs generate valid CLI arguments for NaCl.cif."""
    calc = CalculatorSelector()
    calc.combo_arch.setCurrentText("mace_mp")
    calc.input_model.setText("medium-0b3")

    captured = {}

    orig_init = CalcRunner.__init__

    def fake_init(self, command, args, **kwargs):
        captured[command] = args
        orig_init(self, command, args, **kwargs)

    monkeypatch.setattr(CalcRunner, "__init__", fake_init)
    monkeypatch.setattr(CalcRunner, "start", lambda self: None)

    # 1. Single Point
    t_sp = SinglePointTab(calc_selector=calc)
    t_sp.load_structure_file(nacl_file)
    t_sp.chk_forces.setChecked(True)
    t_sp.chk_stress.setChecked(True)
    t_sp.run_singlepoint()

    assert "singlepoint" in captured
    sp_args = captured["singlepoint"]
    assert "--struct" in sp_args
    assert nacl_file in sp_args
    assert "--arch" in sp_args and "mace_mp" in sp_args
    assert "--model" in sp_args and "medium-0b3" in sp_args
    assert "--properties" in sp_args and "energy" in sp_args
    assert "forces" in sp_args
    assert "--property" not in sp_args

    # 2. GeomOpt
    t_opt = GeomOptTab(calc_selector=calc)
    t_opt.load_structure_file(nacl_file)
    t_opt.chk_write_traj.setChecked(True)
    t_opt.run_optimization()

    assert "geomopt" in captured
    opt_args = captured["geomopt"]
    assert "--struct" in opt_args
    assert "--arch" in opt_args and "mace_mp" in opt_args
    assert "--model" in opt_args and "medium-0b3" in opt_args
    assert "--fmax" in opt_args
    assert "--steps" in opt_args
    assert "--write-traj" in opt_args

    # 3. MD
    t_md = MDTab(calc_selector=calc)
    t_md.load_structure_file(nacl_file)
    t_md.run_md()

    assert "md" in captured
    md_args = captured["md"]
    assert "--struct" in md_args
    assert "--ensemble" in md_args and "nvt" in md_args
    assert "--temp" in md_args
    assert "--timestep" in md_args
    assert "--traj-file" in md_args
    assert "--stats-file" in md_args

    # 4. Phonons
    t_ph = PhononsTab(calc_selector=calc)
    t_ph.load_structure_file(nacl_file)
    t_ph.sc_x.setValue(2)
    t_ph.sc_y.setValue(2)
    t_ph.sc_z.setValue(2)
    t_ph.run_phonons()

    assert "phonons" in captured
    ph_args = captured["phonons"]
    assert "--struct" in ph_args
    assert "--supercell" in ph_args
    assert "2 2 2" in ph_args
    assert "--supercell-matrix" not in ph_args

    # 5. EOS
    t_eos = EOSTab(calc_selector=calc)
    t_eos.load_structure_file(nacl_file)
    t_eos.run_eos()

    assert "eos" in captured
    eos_args = captured["eos"]
    assert "--struct" in eos_args
    assert "--min-volume" in eos_args
    assert "--max-volume" in eos_args
    assert "--n-volumes" in eos_args
    assert "--write-structures" in eos_args
    assert "--min-strain" not in eos_args

    # 6. Elasticity
    t_el = ElasticityTab(calc_selector=calc)
    t_el.load_structure_file(nacl_file)
    t_el.run_elasticity()

    assert "elasticity" in captured
    el_args = captured["elasticity"]
    assert "--struct" in el_args
    assert "--shear-magnitude" in el_args
    assert "--normal-magnitude" in el_args
    assert "--n-strains" in el_args
    assert "--write-structures" in el_args
    assert "--strain" not in el_args

    # 7. Descriptors
    t_desc = DescriptorsTab(calc_selector=calc)
    t_desc.load_structure_file(nacl_file)
    t_desc.run_descriptors()

    assert "descriptors" in captured
    desc_args = captured["descriptors"]
    assert "--struct" in desc_args
    assert "--invariants-only" in desc_args
    assert "--calc-per-atom" in desc_args
    assert "--out" in desc_args

    # 8. NEB
    t_neb = NEBTab(calc_selector=calc)
    t_neb.input_init.setText(nacl_file)
    t_neb.input_final.setText(nacl_file)
    t_neb.chk_climb.setChecked(True)
    t_neb.run_neb()

    assert "neb" in captured
    neb_args = captured["neb"]
    assert "--init-struct" in neb_args
    assert "--final-struct" in neb_args
    assert "--write-band" in neb_args
    assert "--neb-kwargs" in neb_args
    assert "--end-point" not in neb_args


def test_modes_output_parsing(qapp, tmp_path):
    """Test output file parsing in all calculation tabs."""
    from ase.calculators.singlepoint import SinglePointCalculator
    import numpy as np

    # 1. SinglePoint parsing
    t_sp = SinglePointTab()
    test_xyz = tmp_path / "sp_res.extxyz"
    atoms = ase.io.read("NaCl.cif")
    calc = SinglePointCalculator(
        atoms, energy=-27.0314, forces=np.zeros((len(atoms), 3))
    )
    atoms.calc = calc
    ase.io.write(str(test_xyz), atoms)
    t_sp._on_singlepoint_finished(True, "", {"out_file": str(test_xyz)})
    assert "-27.03" in t_sp.lbl_energy.text()
    assert t_sp.forces_table.rowCount() == len(atoms)

    # 2. EOS parsing
    t_eos = EOSTab()
    fit_file = tmp_path / "eos-fit.dat"
    fit_file.write_text("#B0 E0 V0\n25.89 -27.035 184.30\n")
    t_eos._on_eos_finished(True, "", {"fit_dat": str(fit_file)})
    assert any(
        "25.89" in line
        for line in t_eos.log_console.text_edit.toPlainText().splitlines()
    )

    # 3. Elasticity parsing
    t_el = ElasticityTab()
    tens_file = tmp_path / "elastic_tensor.dat"
    tens_vals = "25.89 25.89 25.89 16.24 16.60 16.42 40.67 0.10 0.238 " + " ".join(
        ["10.0"] * 36
    )
    tens_file.write_text(f"# header\n{tens_vals}\n")
    t_el._on_elasticity_finished(True, "", {"tensor_file": str(tens_file)})
    assert "25.89" in t_el.lbl_bulk.text()
    assert "16.42" in t_el.lbl_shear.text()
    assert "40.67" in t_el.lbl_young.text()
    assert t_el.table_cij.item(0, 0).text() == "10.00"

    # 4. NEB parsing
    t_neb = NEBTab()
    neb_res = tmp_path / "neb-results.dat"
    neb_res.write_text("#Barrier deltaE maxF\n0.1234 -0.0450 0.0790\n")
    t_neb._on_neb_finished(True, "", {"results_file": str(neb_res)})
    assert any(
        "0.1234" in line
        for line in t_neb.log_console.text_edit.toPlainText().splitlines()
    )


@pytest.mark.skipif(not HAS_MACE, reason="mace is not installed in this environment")
def test_all_8_modes_end_to_end_nacl(nacl_file, tmp_path):
    """Run all 8 calculation modes end-to-end using NaCl.cif and mace_mp."""
    import subprocess
    import sys

    work_dir = Path(tmp_path)

    janus_bin = shutil.which("janus") or (Path(sys.executable).parent / "janus")

    def run_janus(subcommand, args):
        if Path(janus_bin).exists():
            cmd = [str(janus_bin), subcommand] + args
        else:
            cmd = [
                sys.executable,
                "-c",
                (
                    "from janus_core.cli.janus import app; import sys; "
                    "sys.argv=['janus'] + sys.argv[1:]; app()"
                ),
                subcommand,
            ] + args
        res = subprocess.run(cmd, cwd=work_dir, capture_output=True, text=True)
        assert res.returncode == 0, (
            f"{subcommand} failed:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}"
        )
        return res

    # 1. SinglePoint
    sp_out = work_dir / "sp-results.extxyz"
    run_janus(
        "singlepoint",
        [
            "--struct",
            nacl_file,
            "--arch",
            "mace_mp",
            "--model",
            "medium-0b3",
            "--properties",
            "energy",
            "--properties",
            "forces",
            "--file-prefix",
            str(work_dir / "sp"),
            "--out",
            str(sp_out),
            "--no-tracker",
        ],
    )
    assert sp_out.exists()

    # 2. GeomOpt
    opt_prefix = work_dir / "opt"
    run_janus(
        "geomopt",
        [
            "--struct",
            nacl_file,
            "--arch",
            "mace_mp",
            "--model",
            "medium-0b3",
            "--steps",
            "2",
            "--fmax",
            "0.2",
            "--write-traj",
            "--file-prefix",
            str(opt_prefix),
            "--no-tracker",
        ],
    )
    assert (
        Path(f"{opt_prefix}-opt.extxyz").exists()
        or Path(f"{opt_prefix}-opt.xyz").exists()
    )

    # 3. MD
    md_prefix = work_dir / "md"
    traj_f = work_dir / "md-traj.extxyz"
    stats_f = work_dir / "md-stats.dat"
    run_janus(
        "md",
        [
            "--struct",
            nacl_file,
            "--arch",
            "mace_mp",
            "--model",
            "medium-0b3",
            "--ensemble",
            "nvt",
            "--temp",
            "300",
            "--timestep",
            "1.0",
            "--steps",
            "2",
            "--traj-every",
            "1",
            "--traj-file",
            str(traj_f),
            "--stats-file",
            str(stats_f),
            "--file-prefix",
            str(md_prefix),
            "--no-tracker",
        ],
    )
    assert traj_f.exists()
    assert stats_f.exists()

    # 4. Phonons
    ph_prefix = work_dir / "ph"
    run_janus(
        "phonons",
        [
            "--struct",
            nacl_file,
            "--arch",
            "mace_mp",
            "--model",
            "medium-0b3",
            "--supercell",
            "1 1 1",
            "--displacement",
            "0.01",
            "--file-prefix",
            str(ph_prefix),
            "--no-tracker",
        ],
    )
    assert Path(f"{ph_prefix}-force_constants.hdf5").exists()

    # 5. EOS
    eos_prefix = work_dir / "eos"
    run_janus(
        "eos",
        [
            "--struct",
            nacl_file,
            "--arch",
            "mace_mp",
            "--model",
            "medium-0b3",
            "--min-volume",
            "0.98",
            "--max-volume",
            "1.02",
            "--n-volumes",
            "5",
            "--write-structures",
            "--file-prefix",
            str(eos_prefix),
            "--no-tracker",
        ],
    )
    assert Path(f"{eos_prefix}-eos-fit.dat").exists()

    # 6. Elasticity
    el_prefix = work_dir / "el"
    run_janus(
        "elasticity",
        [
            "--struct",
            nacl_file,
            "--arch",
            "mace_mp",
            "--model",
            "medium-0b3",
            "--shear-magnitude",
            "0.01",
            "--normal-magnitude",
            "0.01",
            "--n-strains",
            "2",
            "--file-prefix",
            str(el_prefix),
            "--no-tracker",
        ],
    )
    assert Path(f"{el_prefix}-elastic_tensor.dat").exists()

    # 7. Descriptors
    desc_out = work_dir / "desc.extxyz"
    run_janus(
        "descriptors",
        [
            "--struct",
            nacl_file,
            "--arch",
            "mace_mp",
            "--model",
            "medium-0b3",
            "--calc-per-atom",
            "--invariants-only",
            "--file-prefix",
            str(work_dir / "desc"),
            "--out",
            str(desc_out),
            "--no-tracker",
        ],
    )
    assert desc_out.exists()

    # 8. NEB
    disp_nacl = work_dir / "nacl_disp.cif"
    at = ase.io.read(nacl_file)
    at.positions[0] += [0.1, 0.0, 0.0]
    ase.io.write(str(disp_nacl), at)

    neb_prefix = work_dir / "neb"
    run_janus(
        "neb",
        [
            "--init-struct",
            nacl_file,
            "--final-struct",
            str(disp_nacl),
            "--arch",
            "mace_mp",
            "--model",
            "medium-0b3",
            "--n-images",
            "3",
            "--steps",
            "2",
            "--write-band",
            "--file-prefix",
            str(neb_prefix),
            "--no-tracker",
        ],
    )
    assert Path(f"{neb_prefix}-neb-results.dat").exists()
