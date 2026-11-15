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
    attach_audio_track_to_html,
    build_storyboard_html_and_gsap,
    extract_sfx_events,
    inject_storyboard_into_html,
    load_storyboard,
)


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
