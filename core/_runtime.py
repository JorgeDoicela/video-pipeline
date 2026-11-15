"""
Utilidades de inicialización del entorno de ejecución para los scripts del núcleo.
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def ensure_repo_root_on_path() -> None:
    """Garantiza que la raíz del repositorio esté en sys.path al ejecutar scripts directos."""
    root_str = str(REPO_ROOT)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


def ensure_local_venv() -> None:
    """Re-ejecuta el proceso actual con el Python del .venv local si existe y no está activo."""
    venv_dir = REPO_ROOT / ".venv"
    venv_py = venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if venv_py.exists() and Path(sys.prefix).resolve() != venv_dir.resolve():
        os.execv(str(venv_py), [str(venv_py), *sys.argv])
