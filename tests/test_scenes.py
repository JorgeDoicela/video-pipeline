"""
Pruebas unitarias para el motor multi-escena y componentes narrativos SVG/HTML.
"""

import json
import re
from pathlib import Path

import pytest

from core.scenes import (
    COMPONENT_REGISTRY,
    SceneSpec,
    StoryboardSpec,
    align_storyboard_to_transcript,
    attach_audio_track_to_html,
    build_storyboard_from_transcript,
    build_storyboard_html_and_gsap,
    extract_sfx_events,
    inject_storyboard_into_html,
    load_storyboard,
)
from core.styles import DESIGN_SYSTEMS, apply_style_to_project


def _sample_storyboard_dict() -> dict:
    return {
        "title": "Demo Explainer",
        "duration": 10.0,
        "aspect_ratio": "9:16",
        "atmosphere": "sunburst",
        "scenes": [
            {
                "id": "s1",
                "start": 0.0,
                "end": 3.5,
                "badge": "01 · ALERTA",
                "headline": "Sin acceso al terminal",
                "component": "phone_mockup",
                "transition": "snap",
                "sfx": "sub_hit",
                "sfx_volume": 0.4,
                "props": {"app": "SSH", "status": "BLOQUEADO", "detail": "Puerto 22 cerrado"},
            },
            {
                "id": "s2",
                "start": 3.5,
                "end": 7.0,
                "headline": "Mapa de red",
                "component": "network_graph",
                "transition": "zoom_in",
                "sfx": "whoosh",
                "props": {
                    "nodes": [
                        {"id": "gw", "label": "Gateway", "x": 200, "y": 200, "alert": False},
                        {"id": "db", "label": "DB", "x": 650, "y": 420, "alert": True},
                    ]
                },
            },
            {
                "id": "s3",
                "start": 7.0,
                "end": 10.0,
                "headline": "Impacto medido",
                "component": "stat_callout",
                "transition": "slide_up",
                "sfx": "pop",
                "props": {"value": "99.9%", "label": "Disponibilidad", "note": "Cero caidas"},
            },
        ],
    }


def test_load_storyboard_and_extract_sfx(tmp_path: Path):
    spec_path = tmp_path / "storyboard.json"
    spec_path.write_text(json.dumps(_sample_storyboard_dict()), encoding="utf-8")

    sb = load_storyboard(spec_path)
    assert sb.title == "Demo Explainer"
    assert sb.duration == 10.0
    assert len(sb.scenes) == 3

    events = extract_sfx_events(sb)
    assert len(events) == 3
    assert events[0].sfx == "sub_hit"
    assert events[0].time_sec == 0.0
    assert events[0].volume == pytest.approx(0.4)


def test_all_registered_components_render_valid_html_and_gsap():
    for comp_name in COMPONENT_REGISTRY:
        scene = SceneSpec(
            id=f"test_{comp_name}",
            start=0.0,
            end=3.0,
            headline=f"Escena {comp_name}",
            component=comp_name,
            badge="PRUEBA",
            props={},
        )
        sb = StoryboardSpec(title="Test", duration=3.0, scenes=[scene])
        markup, js_code = build_storyboard_html_and_gsap(sb)
        assert f'id="test_{comp_name}"' in markup
        assert "tl." in js_code
        assert "transition:" not in markup.lower()


def test_inject_storyboard_is_idempotent_and_respects_clean_aesthetics(tmp_path: Path):
    base_html = """<!doctype html>
<html lang="es">
<head><meta charset="utf-8"><title>Test</title></head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="10" data-width="1080" data-height="1920">
<!-- @scenes:start -->
<p>old</p>
<!-- @scenes:end -->
</div>
<script>
const tl = gsap.timeline({ paused: true });
// @scenes-gsap:start
// old
// @scenes-gsap:end
window.__timelines = { main: tl };
tl.seek(0);
</script>
</body>
</html>
"""
    html_file = tmp_path / "index.html"
    html_file.write_text(base_html, encoding="utf-8")

    spec_path = tmp_path / "storyboard.json"
    spec_path.write_text(json.dumps(_sample_storyboard_dict()), encoding="utf-8")
    sb = load_storyboard(spec_path)

    inject_storyboard_into_html(html_file, sb)
    first_pass = html_file.read_text(encoding="utf-8")
    inject_storyboard_into_html(html_file, sb)
    second_pass = html_file.read_text(encoding="utf-8")

    assert first_pass == second_pass
    assert "<p>old</p>" not in second_pass
    assert 'id="s1"' in second_pass
    assert 'id="s3"' in second_pass
    assert not re.search(r"border-left\s*:", second_pass)
    assert "transition:" not in second_pass


def test_attach_audio_track_to_html_is_idempotent(tmp_path: Path):
    html_file = tmp_path / "index.html"
    html_file.write_text(
        '<div id="root" data-composition-id="main" data-start="0" data-duration="10" data-width="1080" data-height="1920"></div>',
        encoding="utf-8",
    )
    attach_audio_track_to_html(html_file, "audio_mix.wav", 10.0)
    attach_audio_track_to_html(html_file, "audio_mix.wav", 10.0)

    content = html_file.read_text(encoding="utf-8")
    assert content.count('src="audio_mix.wav"') == 1
    assert 'data-duration="10.00"' in content


def test_component_registry_includes_universal_primitives():
    expected = {
        "phone_mockup",
        "network_graph",
        "terminal_grid",
        "connector_flow",
        "stat_callout",
        "timeline_steps",
        "comparison_split",
        "quote_focus",
        "bar_chart",
        "code_spotlight",
        "icon_spotlight",
        "radar_map",
        "xray_scanner",
        "system_alert",
        "hex_inspector",
        "desktop_monitor",
        "keyboard_type",
        "padlock_denied",
        "file_cards",
        "custom_scene",
    }
    assert expected == set(COMPONENT_REGISTRY.keys())


def test_stat_callout_and_phone_app_grid_and_hero_top_render():
    s1 = SceneSpec(
        id="s_grid",
        start=0.0,
        end=3.0,
        headline="",
        component="phone_mockup",
        accent="danger",
        atmosphere="sunburst",
        props={"mode": "app_grid", "alert_text": "PRÓXIMA CAPTURA 00:02"},
    )
    s2 = SceneSpec(
        id="s_stat",
        start=3.0,
        end=6.0,
        headline="Disponibilidad",
        component="stat_callout",
        accent="secondary",
        atmosphere="grid",
        props={"value": "99.9%", "label": "SLA Producción", "note": "Cero caídas"},
    )
    sb = StoryboardSpec(
        title="Hero Test",
        duration=6.0,
        caption_position="hero_top",
        brand="hack4u.io",
        category="CIBERSEGURIDAD",
        ambient_bed=True,
        scenes=[s1, s2],
    )
    markup, js_code = build_storyboard_html_and_gsap(sb)
    assert "99.9%" in markup
    assert "SLA Producción" in markup
    assert "PRÓXIMA CAPTURA 00:02" in markup
    assert 'id="brand-bar"' in markup
    assert "hack4u.io" in markup
    assert "CIBERSEGURIDAD" in markup
    assert "--scene-accent: var(--accent-danger);" in markup
    assert "#atmosphere-grid" in js_code

    sub_events = extract_sfx_events(sb, include_sub_events=True)
    assert len(sub_events) > 2


def test_vocabulary_replacements_in_transcribe():
    from core.transcribe import apply_vocabulary_replacements, parse_replacements

    rep = parse_replacements(["lidis=Redis", "kubernets=Kubernetes"])
    sample = {
        "segments": [
            {
                "text": "Escalamos con lidis, y kubernets.",
                "words": [
                    {"word": "Escalamos", "start": 0.0, "end": 0.4},
                    {"word": "con", "start": 0.4, "end": 0.6},
                    {"word": "lidis,", "start": 0.6, "end": 1.0},
                    {"word": "y", "start": 1.0, "end": 1.1},
                    {"word": "kubernets.", "start": 1.1, "end": 1.6},
                ],
            }
        ]
    }
    updated = apply_vocabulary_replacements(sample, rep)
    assert updated["segments"][0]["text"] == "Escalamos con Redis, y Kubernetes."
    assert updated["segments"][0]["words"][2]["word"] == "Redis,"
    assert updated["segments"][0]["words"][4]["word"] == "Kubernetes."


def test_align_storyboard_to_transcript_resolves_cue_words():
    sb = StoryboardSpec(
        title="Cue Test",
        duration=8.0,
        scenes=[
            SceneSpec(
                id="s1",
                start=0.0,
                end=4.0,
                headline="Intro",
                component="quote_focus",
            ),
            SceneSpec(
                id="s2",
                start=4.0,
                end=8.0,
                headline="Datos",
                component="bar_chart",
                cue_word="Métrica",
            ),
        ],
    )
    transcript = {
        "segments": [
            {
                "words": [
                    {"word": "Hoy", "start": 0.1},
                    {"word": "vemos", "start": 0.6},
                    {"word": "la", "start": 1.1},
                    {"word": "metrica!", "start": 2.75},
                    {"word": "final", "start": 3.5},
                ]
            }
        ]
    }
    aligned = align_storyboard_to_transcript(sb, transcript, total_duration=9.5)
    assert aligned.scenes[0].end == pytest.approx(2.75)
    assert aligned.scenes[1].start == pytest.approx(2.75)
    assert aligned.scenes[1].end == pytest.approx(9.5)
    assert aligned.duration == pytest.approx(9.5)


def test_build_storyboard_from_transcript_generates_valid_spec(tmp_path: Path):
    transcript = {
        "duration": 10.5,
        "segments": [
            {"start": 0.0, "end": 3.5, "text": "Primer concepto clave del video"},
            {"start": 3.6, "end": 7.0, "text": "Segundo punto con datos reales"},
            {"start": 7.1, "end": 10.5, "text": "Conclusión práctica y cierre"},
        ],
    }
    raw_spec = build_storyboard_from_transcript(
        transcript, title="Mi Video", aspect_ratio="16:9", atmosphere="grid"
    )
    spec_path = tmp_path / "storyboard.json"
    spec_path.write_text(json.dumps(raw_spec), encoding="utf-8")

    sb = load_storyboard(spec_path)
    assert sb.title == "Mi Video"
    assert sb.aspect_ratio == "16:9"
    assert sb.atmosphere == "grid"
    assert len(sb.scenes) == 3


def test_explainer_project_supports_switching_all_macro_designs(tmp_path: Path):
    proj_dir = tmp_path / "explainer-demo"
    proj_dir.mkdir()
    src_html = (
        Path(__file__).resolve().parent.parent
        / "templates"
        / "explainer_scenes_9_16"
        / "index.html"
    )
    html_file = proj_dir / "index.html"
    html_file.write_text(src_html.read_text(encoding="utf-8"), encoding="utf-8")
    (proj_dir / "package.json").write_text('{"name": "explainer-demo"}', encoding="utf-8")

    for design_slug in DESIGN_SYSTEMS:
        apply_style_to_project(proj_dir, design_slug=design_slug)
        content = html_file.read_text(encoding="utf-8")
        assert f'data-design="{design_slug}"' in content
        assert "<!-- @scenes:start -->" in content
        assert "<!-- @captions:start -->" in content
        assert ".ng-quote-text" in content
        assert ".ng-timeline" in content
        assert ".ng-spotlight" in content
