"""
Pruebas unitarias para el exportador NLE (core/nle_export.py):
  - Segmentación por --cuts o storyboard.json
  - Generación no destructiva de capas HTML (bg / overlay transparente)
  - Generación de FCPXML v1.10 válido y alineado a frames
  - Exportación completa con stems de audio, clips cortados y subtítulos
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from core.nle_export import (
    ExportedClip,
    ExportedStem,
    TimelineSegment,
    build_fcpxml,
    build_layer_html,
    export_nle_package,
    parse_cuts_argument,
    resolve_timeline_segments,
)


def test_parse_cuts_argument_builds_contiguous_acts():
    segs = parse_cuts_argument("0, 3.7, 7.5, 11.4", total_duration=15.0)
    assert len(segs) == 4
    assert [(s.start, s.end) for s in segs] == [
        (0.0, 3.7),
        (3.7, 7.5),
        (7.5, 11.4),
        (11.4, 15.0),
    ]

    # Si omite el 0 inicial, lo agrega automáticamente
    segs2 = parse_cuts_argument("4.0, 8.0", total_duration=12.0)
    assert [(s.start, s.end) for s in segs2] == [(0.0, 4.0), (4.0, 8.0), (8.0, 12.0)]

    with pytest.raises(ValueError, match="fuera del rango"):
        parse_cuts_argument("0, 20.0", total_duration=10.0)


def test_resolve_timeline_segments_prefers_cuts_then_storyboard(tmp_path):
    sb = {
        "title": "Demo",
        "duration": 10.0,
        "scenes": [
            {"id": "s1", "start": 0.0, "end": 4.0, "headline": "Intro", "component": "quote_focus"},
            {
                "id": "s2",
                "start": 4.0,
                "end": 10.0,
                "headline": "Cierre",
                "component": "quote_focus",
            },
        ],
    }
    (tmp_path / "storyboard.json").write_text(json.dumps(sb), encoding="utf-8")

    from_sb = resolve_timeline_segments(tmp_path, total_duration=10.0)
    assert [s.slug for s in from_sb] == ["s1", "s2"]
    assert [s.label for s in from_sb] == ["Intro", "Cierre"]

    from_cuts = resolve_timeline_segments(tmp_path, total_duration=10.0, raw_cuts="0,5.0")
    assert [s.slug for s in from_cuts] == ["acto_01", "acto_02"]


def test_build_layer_html_bg_and_overlay():
    sample = "<html><head><style>body{background:#000;}</style></head><body></body></html>"
    bg_html = build_layer_html(sample, "bg")
    assert "@nle-layer:bg" in bg_html
    assert "visibility: hidden !important;" in bg_html
    assert "#card" in bg_html

    ov_html = build_layer_html(sample, "overlay")
    assert "@nle-layer:overlay" in ov_html
    assert "background: transparent !important;" in ov_html
    assert "#main" in ov_html
    assert "#bg-video" in ov_html
    assert "#orb-p" in ov_html

    with pytest.raises(ValueError, match="Capa NLE inválida"):
        build_layer_html(sample, "otra")


def test_build_fcpxml_vertical_9_16_uses_rate_undefined_and_inserts_gaps(tmp_path):
    c1 = tmp_path / "c1.mp4"
    c2 = tmp_path / "c2.mp4"
    voz = tmp_path / "stem_voz.wav"
    for p in (c1, c2, voz):
        p.write_bytes(b"x")

    xml_str = build_fcpxml(
        project_name="vertical-gaps",
        width=1080,
        height=1920,
        fps=30,
        total_duration=10.0,
        clips=[
            ExportedClip(TimelineSegment(1, "s1", "Escena 1", 1.0, 4.0), c1),
            ExportedClip(TimelineSegment(2, "s2", "Escena 2", 5.0, 10.0), c2),
        ],
        stems=[ExportedStem("voz", "Voz", voz, 10.0)],
    )
    root = ET.fromstring(xml_str.split("\n", 2)[2])
    fmt = root.find("./resources/format")
    assert fmt is not None
    assert fmt.attrib["name"] == "FFVideoFormatRateUndefined"
    assert fmt.attrib["width"] == "1080"
    assert fmt.attrib["height"] == "1920"

    spine_children = list(root.find(".//spine"))
    assert [el.tag for el in spine_children] == ["gap", "asset-clip", "gap", "asset-clip"]
    # El stem de voz queda anclado al primer elemento del spine (gap en t=0s)
    assert spine_children[0].attrib["offset"] == "0s"
    stem_el = spine_children[0].find("./asset-clip")
    assert stem_el is not None
    assert stem_el.attrib["lane"] == "-1"
    assert stem_el.attrib["offset"] == "0s"


def test_fcpxml_frame_alignment_has_zero_gaps_on_fractional_cuts(tmp_path):
    c1 = tmp_path / "c1.mp4"
    c2 = tmp_path / "c2.mp4"
    c3 = tmp_path / "c3.mp4"
    for p in (c1, c2, c3):
        p.write_bytes(b"v")

    xml_str = build_fcpxml(
        project_name="drift-check",
        width=1920,
        height=1080,
        fps=30,
        total_duration=10.0,
        clips=[
            ExportedClip(TimelineSegment(1, "a", "A", 0.0, 3.35), c1),
            ExportedClip(TimelineSegment(2, "b", "B", 3.35, 6.70), c2),
            ExportedClip(TimelineSegment(3, "c", "C", 6.70, 10.0), c3),
        ],
        stems=[],
    )
    root = ET.fromstring(xml_str.split("\n", 2)[2])
    spine_clips = root.findall(".//spine/asset-clip")

    def parse_frames(val: str) -> int:
        if val == "0s":
            return 0
        num = int(val.split("/")[0])
        return num // 100

    cursor = 0
    for cl in spine_clips:
        off = parse_frames(cl.attrib["offset"])
        dur = parse_frames(cl.attrib["duration"])
        assert off == cursor
        cursor += dur
    assert cursor == 300  # 10.0s * 30fps exactos


def test_build_fcpxml_is_valid_xml_with_lanes_and_markers(tmp_path):
    clip1 = tmp_path / "01_intro_bg.mp4"
    ov1 = tmp_path / "01_intro_overlay.mov"
    clip2 = tmp_path / "02_cierre_bg.mp4"
    ov2 = tmp_path / "02_cierre_overlay.mov"
    voz = tmp_path / "stem_voz.wav"
    mus = tmp_path / "stem_musica.wav"
    for p in (clip1, ov1, clip2, ov2, voz, mus):
        p.write_bytes(b"demo")

    xml_str = build_fcpxml(
        project_name="demo-proyecto",
        width=1920,
        height=1080,
        fps=30,
        total_duration=10.0,
        clips=[
            ExportedClip(TimelineSegment(1, "intro", "Introducción", 0.0, 4.0), clip1, ov1),
            ExportedClip(TimelineSegment(2, "cierre", "Conclusión", 4.0, 10.0), clip2, ov2),
        ],
        stems=[
            ExportedStem("voz", "Voz", voz, 10.0),
            ExportedStem("musica", "Música", mus, 10.0),
        ],
    )

    assert "<!DOCTYPE fcpxml>" in xml_str
    # Parsear el XML (saltando las 2 líneas de cabecera XML/DOCTYPE)
    root = ET.fromstring(xml_str.split("\n", 2)[2])
    assert root.tag == "fcpxml"
    assert root.attrib["version"] == "1.10"

    assets = root.findall("./resources/asset")
    assert len(assets) == 6  # 2 bg + 2 overlay + 2 stems

    spine_clips = root.findall(".//spine/asset-clip")
    assert len(spine_clips) == 2
    # Overlay alfa en lane="1" y stems de audio en lane="-1" y lane="-2"
    lanes = [el.attrib.get("lane") for el in spine_clips[0].findall("./asset-clip")]
    assert "1" in lanes
    assert "-1" in lanes
    assert "-2" in lanes
    assert spine_clips[0].find("./marker").attrib["value"] == "Introducción"


def test_export_nle_package_creates_clips_stems_subtitles_and_fcpxml(tmp_path, monkeypatch):
    proj = tmp_path / "mi-video"
    proj.mkdir()
    (proj / "index.html").write_text(
        '<div id="root" data-composition-id="main" data-width="1920" data-height="1080" data-duration="8.00"></div>',
        encoding="utf-8",
    )
    (proj / "video_mi-video.mp4").write_bytes(b"FAKE_MASTER_MP4")
    (proj / "audio_mix.wav").write_bytes(b"RIFF_MASTER_AUDIO")
    (proj / "subtitles.srt").write_text(
        "1\n00:00:00,000 --> 00:00:02,000\nHola\n", encoding="utf-8"
    )

    ffmpeg_calls: list[list[str]] = []

    def fake_run(cmd, check=True, stdout=None, stderr=None):
        ffmpeg_calls.append(cmd)
        Path(cmd[-1]).write_bytes(b"CUT_CLIP")

    monkeypatch.setattr("core.nle_export.resolve_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr("core.nle_export.subprocess.run", fake_run)

    res = export_nle_package(proj, cuts="0,4.0", fps=30)
    assert res.fcpxml_path.is_file()
    assert res.manifest_path.is_file()
    assert len(res.clips) == 2
    assert len(res.stems) == 1
    assert res.stems[0].kind == "master"
    assert len(res.subtitles) == 1
    assert len(ffmpeg_calls) == 2
    assert "-frames:v" in ffmpeg_calls[0]
    assert ffmpeg_calls[0][ffmpeg_calls[0].index("-frames:v") + 1] == "120"

    manifest = json.loads(res.manifest_path.read_text(encoding="utf-8"))
    assert manifest["resolution"] == "1920x1080"
    assert len(manifest["clips"]) == 2
