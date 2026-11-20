"""
Utilidades transversales de inicialización de entorno, resolución de rutas y normalización
compartidas por los módulos del núcleo (core/).
"""

from __future__ import annotations

import os
import re
import sys
import unicodedata
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


def normalize_token(text: str) -> str:
    """Normaliza un token alfanumérico en minúsculas sin acentos ni signos de puntuación."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    ascii_only = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", ascii_only)


def resolve_project_dir(project_or_path: str | Path, base_dir: Path | None = None) -> Path:
    """
    Resuelve un identificador de proyecto ('mi-video' o ruta a directorio/index.html)
    al directorio del proyecto correspondiente.
    """
    root = base_dir or REPO_ROOT
    target = Path(project_or_path)
    if not target.exists():
        candidate = root / "projects" / str(project_or_path)
        if candidate.exists():
            target = candidate
    return target.parent if target.is_file() else target
