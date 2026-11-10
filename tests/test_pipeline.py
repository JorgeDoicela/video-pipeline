"""
Pruebas de interfaz y comprobación de subcomandos para pipeline.py.
"""

import subprocess
import sys


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


def test_pipeline_subcommand_style_list():
    res = subprocess.run(
        [sys.executable, "core/pipeline.py", "style", "--list"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "cyber_glass" in res.stdout
    assert "clean_studio" in res.stdout
    assert "bento_grid" in res.stdout
    assert "academic_paper" in res.stdout
    assert "cyber_dark" in res.stdout
    assert "minimal_light" in res.stdout
    assert "terminal_hacker" in res.stdout
    assert "linear_violet" in res.stdout
    assert "blueprint_cad" in res.stdout
    assert "dracula_pro" in res.stdout
    assert "solarized_sand" in res.stdout
    assert "crimson_ops" in res.stdout
    assert "underline_bar" in res.stdout
    assert "box_invert" in res.stdout
