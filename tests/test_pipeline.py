"""
Pruebas de interfaz y comprobación de subcomandos para pipeline.py.
"""

import subprocess
import sys

import pytest

from core.pipeline import resolve_pnpm


def test_pipeline_cli_help():
    res = subprocess.run(
        [sys.executable, "core/pipeline.py", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Orquestador Maestro" in res.stdout
    assert "produce" in res.stdout
    assert "captions" in res.stdout
    assert "scaffold" in res.stdout
    assert "style" in res.stdout


def test_pipeline_subcommand_produce_help():
    res = subprocess.run(
        [sys.executable, "core/pipeline.py", "produce", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "--input" in res.stdout
    assert "--project" in res.stdout
    assert "--template" in res.stdout
    assert "--style" in res.stdout
    assert "--caption-style" in res.stdout
    assert "--auto-render" in res.stdout


def test_pipeline_subcommands_delegate_full_arguments():
    res_caps = subprocess.run(
        [sys.executable, "core/pipeline.py", "captions", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "--words-per-group" in res_caps.stdout
    assert "--pause-threshold" in res_caps.stdout

    res_tr = subprocess.run(
        [sys.executable, "core/pipeline.py", "transcribe", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "--device" in res_tr.stdout
    assert "--replace" in res_tr.stdout

    res_assets = subprocess.run(
        [sys.executable, "core/pipeline.py", "assets", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "seed-icons" in res_assets.stdout
    assert "icon" in res_assets.stdout
    assert "map" in res_assets.stdout
    assert "audio" in res_assets.stdout


def test_pipeline_subcommand_style_list():
    res = subprocess.run(
        [sys.executable, "core/pipeline.py", "style", "--list"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "cinematic" in res.stdout
    assert "editorial" in res.stdout
    assert "clean" in res.stdout
    assert "dark_violet" in res.stdout
    assert "paper_warm" in res.stdout
    assert "clean_light" in res.stdout
    assert "minimal_clean" in res.stdout


def test_resolve_pnpm(monkeypatch):
    monkeypatch.setattr("core.pipeline.shutil.which", lambda name: r"C:\tools\pnpm.cmd")
    assert resolve_pnpm() == r"C:\tools\pnpm.cmd"

    monkeypatch.setattr("core.pipeline.shutil.which", lambda name: None)
    with pytest.raises(FileNotFoundError, match="pnpm"):
        resolve_pnpm()
