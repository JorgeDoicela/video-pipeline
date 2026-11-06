"""
Pruebas unitarias para el módulo de creación de proyectos y sanitización de slugs.
"""

import pytest

from core.create_project import create_project, sanitize_project_name


def test_sanitize_project_name():
    assert sanitize_project_name("Mi Proyecto de Video!") == "mi-proyecto-de-video"
    assert sanitize_project_name("  TEST---123__abc  ") == "test-123__abc"
    assert sanitize_project_name("arquitectura-cqrs") == "arquitectura-cqrs"


def test_sanitize_project_name_empty():
    with pytest.raises(ValueError):
        sanitize_project_name("!@#$%^&*()")


def test_create_project_lifecycle(tmp_path, monkeypatch):
    # Redirigir directorio projects a tmp_path para pruebas aisladas
    base_dir = tmp_path / "video-pipeline"
    projects_dir = base_dir / "projects"
    templates_dir = base_dir / "templates"
    templates_dir.mkdir(parents=True)
    projects_dir.mkdir(parents=True)

    # Crear una plantilla simulada
    test_tmpl = templates_dir / "portrait_9_16"
    test_tmpl.mkdir()
    (test_tmpl / "index.html").write_text(
        '<div data-duration="10"><h1>Original</h1></div>', encoding="utf-8"
    )
    (test_tmpl / "package.json").write_text('{"name": "template"}', encoding="utf-8")

    monkeypatch.setattr(
        "core.create_project.__file__", str(base_dir / "core" / "create_project.py")
    )

    # Ejecutar creación de proyecto
    proj_path = create_project(
        name="test-scaffold-unit",
        template="portrait_9_16",
        title="Nuevo Titulo Inyectado",
        duration=15.5,
    )

    assert proj_path.exists()
    html_content = (proj_path / "index.html").read_text(encoding="utf-8")
    assert 'data-duration="15.5"' in html_content
    assert "<h1>Nuevo Titulo Inyectado</h1>" in html_content

    # Limpieza
    import shutil

    shutil.rmtree(proj_path)
