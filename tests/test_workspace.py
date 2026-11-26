"""
Pruebas unitarias para la capa de Workspace, Perfiles de Canal/Cliente e Historial (core/workspace.py).
"""

import json
from datetime import date

import pytest

from core._runtime import resolve_project_dir
from core.create_project import create_project
from core.workspace import (
    WORKSPACE_ENV_VAR,
    ChannelProfile,
    format_project_slug,
    infer_workspace_root_from_project,
    list_profiles,
    load_history,
    load_profile,
    record_history_event,
    resolve_workspace_root,
    sanitize_channel_path,
    save_profile,
)


def test_seed_profiles_catalog_is_valid():
    profiles = list_profiles()
    slugs = {p.slug for p in profiles}
    assert {"tech_short", "editorial_essay", "client_clean"}.issubset(slugs)

    tech = load_profile("tech_short")
    assert tech.channel == "tech"
    assert tech.design == "cinematic"
    assert tech.style == "dark_violet"
    assert tech.voice_polish is True

    client = load_profile("client_clean")
    assert client.template == "talking_head_16_9"
    assert client.overrides["caption_text"] == "#f8fafc"
    assert client.overrides["caption_active"] == "#38bdf8"


def test_sanitize_channel_path_allows_nested_and_blocks_traversal():
    assert sanitize_channel_path("tech").as_posix() == "tech"
    assert sanitize_channel_path("Clientes / Acme Corp").as_posix() == "clientes/acme-corp"
    assert sanitize_channel_path("") is None
    assert sanitize_channel_path(None) is None

    for bad in ["../escape", "tech/../../etc", "/abs/path", "C:\\Windows"]:
        with pytest.raises(ValueError):
            sanitize_channel_path(bad)


def test_format_project_slug_dated():
    ref = date(2026, 11, 26)
    assert format_project_slug("Redis Cache!", dated=True, ref_date=ref) == "2026-11-26_redis-cache"
    # No duplica prefijo si ya trae fecha
    assert (
        format_project_slug("2026-11-26_redis-cache", dated=True, ref_date=ref)
        == "2026-11-26_redis-cache"
    )


def test_save_and_load_custom_profile_validation(tmp_path):
    prof = ChannelProfile(
        slug="canal_finanzas",
        name="Canal Finanzas",
        channel="finanzas",
        template="editorial_16_9",
        design="editorial",
        style="paper_warm",
        overrides={"accent_primary": "#047857"},
        replacements={"etefe": "ETF"},
    )
    saved = save_profile(prof, profiles_dir=tmp_path)
    assert saved.exists()

    loaded = load_profile("canal_finanzas", profiles_dir=tmp_path)
    assert loaded.overrides == {"accent_primary": "#047857"}
    assert loaded.replacements == {"etefe": "ETF"}

    with pytest.raises(FileExistsError):
        save_profile(prof, profiles_dir=tmp_path, force=False)

    # Perfil con diseño o plantilla inválida falla validación
    bad_file = tmp_path / "roto.json"
    bad_file.write_text('{"slug": "roto", "design": "inventado"}', encoding="utf-8")
    with pytest.raises(ValueError, match="inválido"):
        load_profile(bad_file)

    bad_tpl = tmp_path / "roto_tpl.json"
    bad_tpl.write_text('{"slug": "roto_tpl", "template": "no_existe"}', encoding="utf-8")
    with pytest.raises(ValueError, match="plantilla"):
        load_profile(bad_tpl)


def test_resolve_workspace_root_precedence_and_runtime_lookup(tmp_path, monkeypatch):
    env_ws = tmp_path / "env_studio"
    profile_ws = tmp_path / "profile_studio"
    cli_ws = tmp_path / "cli_studio"

    monkeypatch.setenv(WORKSPACE_ENV_VAR, str(env_ws))
    assert resolve_workspace_root(base_dir=tmp_path) == env_ws
    assert (
        resolve_workspace_root(profile_output_root=str(profile_ws), base_dir=tmp_path) == profile_ws
    )
    assert (
        resolve_workspace_root(
            output_dir=cli_ws, profile_output_root=str(profile_ws), base_dir=tmp_path
        )
        == cli_ws
    )

    # resolve_project_dir encuentra proyectos dentro de VIDEO_PIPELINE_WORKSPACE
    proj_dir = env_ws / "tech" / "2026-11-26_demo"
    proj_dir.mkdir(parents=True)
    assert resolve_project_dir("tech/2026-11-26_demo", base_dir=tmp_path) == proj_dir


def test_create_project_with_profile_channel_external_workspace_and_history(tmp_path):
    external_ws = tmp_path / "video-studio"
    proj_path = create_project(
        name="Arquitectura Redis",
        profile="tech_short",
        channel="clientes/acme",
        output_dir=external_ws,
        dated=True,
        title="Redis en Producción",
        overrides={"accent_primary": "#34d399"},
    )

    assert proj_path.parent == external_ws / "clientes" / "acme"
    assert proj_path.name.endswith("_arquitectura-redis")

    pkg = json.loads((proj_path / "package.json").read_text(encoding="utf-8"))
    assert pkg["videoProject"]["channel"] == "clientes/acme"
    assert pkg["videoProject"]["profile"] == "tech_short"
    assert pkg["videoDesign"]["design"] == "cinematic"
    assert pkg["videoDesign"]["overrides"]["accent_primary"] == "#34d399"

    sb = json.loads((proj_path / "storyboard.json").read_text(encoding="utf-8"))
    assert sb["category"] == "TECNOLOGIA"

    # Historial registrado automáticamente en <workspace>/catalog.jsonl
    records = load_history(external_ws)
    assert len(records) == 1
    assert records[0]["action"] == "scaffold"
    assert records[0]["channel"] == "clientes/acme"
    assert records[0]["profile"] == "tech_short"


def test_history_filtering_and_ordering(tmp_path):
    p1 = tmp_path / "tech" / "vid-1"
    p2 = tmp_path / "editorial" / "vid-2"
    p1.mkdir(parents=True)
    p2.mkdir(parents=True)

    record_history_event(
        tmp_path,
        action="scaffold",
        project_slug="vid-1",
        project_dir=p1,
        channel="tech",
        profile="tech_short",
    )
    record_history_event(
        tmp_path,
        action="produce",
        project_slug="vid-2",
        project_dir=p2,
        channel="editorial",
        profile="editorial_essay",
        duration=42.5,
    )

    all_recs = load_history(tmp_path)
    assert [r["project"] for r in all_recs] == ["vid-2", "vid-1"]
    assert len(load_history(tmp_path, channel="tech")) == 1
    assert len(load_history(tmp_path, profile="editorial_essay")) == 1
    assert len(load_history(tmp_path, limit=1)) == 1


def test_infer_workspace_root_from_nested_channel_project(tmp_path):
    ws = tmp_path / "video-studio"
    proj = ws / "clientes" / "acme" / "2026-11-26_demo"
    proj.mkdir(parents=True)
    assert infer_workspace_root_from_project(proj, "clientes/acme") == ws
    assert infer_workspace_root_from_project(ws / "solo-slug", "") == ws
