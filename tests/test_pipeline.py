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
    assert "--auto-render" in res.stdout
