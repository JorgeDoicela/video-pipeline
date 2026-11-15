"""
Pruebas unitarias para el módulo de creación de proyectos y sanitización de slugs.
"""

import json
import shutil

import pytest

from core.create_project import AVAILABLE_TEMPLATES, create_project, sanitize_project_name


def test_available_templates_catalog():
    assert set(AVAILABLE_TEMPLATES) == {
        "short_quote_9_16",
        "short_tech_9_16",
        "talking_head_9_16",
        "editorial_16_9",
        "talking_head_16_9",
        "explainer_scenes_9_16",
    }


def test_sanitize_project_name():
    assert sanitize_project_name("Mi Proyecto de Video!") == "mi-proyecto-de-video"
    assert sanitize_project_name("  TEST---123__abc  ") == "test-123__abc"
    assert sanitize_project_name("arquitectura-cqrs") == "arquitectura-cqrs"


def test_sanitize_project_name_empty():
    with pytest.raises(ValueError):
        sanitize_project_name("!@#$%^&*()")


def test_create_project_lifecycle_with_styles(tmp_path, monkeypatch):
    # Redirigir directorio projects a tmp_path para pruebas aisladas
    base_dir = tmp_path / "video-pipeline"
    projects_dir = base_dir / "projects"
    templates_dir = base_dir / "templates"
    templates_dir.mkdir(parents=True)
    projects_dir.mkdir(parents=True)

    # Crear una plantilla simulada compatible con tokens
    test_tmpl = templates_dir / "short_quote_9_16"
    test_tmpl.mkdir()
    (test_tmpl / "index.html").write_text(
        '<style>:root { --bg: #09090b; }</style><div id="root" data-composition-id="main" data-duration="10"><h1>Original</h1></div>',
        encoding="utf-8",
    )
    (test_tmpl / "package.json").write_text('{"name": "template"}', encoding="utf-8")

    monkeypatch.setattr(
        "core.create_project.__file__", str(base_dir / "core" / "create_project.py")
    )

    # Ejecutar creación de proyecto con estilo clean_light y caracteres especiales en título
    proj_path = create_project(
        name="test-scaffold-unit",
        template="short_quote_9_16",
        title=r"Nuevo & <Titulo> \1 Inyectado",
        duration=15.5,
        style="clean_light",
        caption_style="minimal_clean",
    )

    assert proj_path.exists()
    html_content = (proj_path / "index.html").read_text(encoding="utf-8")
    assert 'data-duration="15.5"' in html_content
    assert 'data-style="clean_light"' in html_content
    assert "--bg: #f8fafc;" in html_content
    assert r"<h1>Nuevo &amp; &lt;Titulo&gt; \1 Inyectado</h1>" in html_content

    pkg_data = json.loads((proj_path / "package.json").read_text(encoding="utf-8"))
    assert pkg_data["videoStyle"] == "clean_light"
    assert pkg_data["captionStyle"] == "minimal_clean"

    shutil.rmtree(proj_path)
