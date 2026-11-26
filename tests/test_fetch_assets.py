"""
Pruebas unitarias para el gestor y descargador de assets abiertos (core/fetch_assets.py):
  - Iconify SVG (Lucide / Tabler / Simple Icons)
  - Natural Earth GeoJSON -> compilador SVG para radar_map
  - Audio CC0 (URL directa y Freesound API v2 con filtro CC0 + normalización FFmpeg 48kHz 16-bit)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.fetch_assets import (
    BASE_ICONS,
    build_audio_normalize_command,
    compile_geojson_to_radar_svg,
    ensure_base_icons,
    fetch_audio_cc0,
    fetch_icon,
    fetch_map,
    list_local_assets,
    normalize_iconify_svg,
)


def test_normalize_iconify_svg_strips_fixed_dimensions_and_preserves_viewbox():
    raw = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><path fill="currentColor" d="M12 2L2 7l10 5l10-5z"/></svg>'
    cleaned = normalize_iconify_svg(raw)
    assert 'width="24"' not in cleaned
    assert 'height="24"' not in cleaned
    assert 'viewBox="0 0 24 24"' in cleaned
    assert "<path" in cleaned


def test_fetch_icon_downloads_and_caches_locally(tmp_path: Path, monkeypatch):
    sample_svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 24 24"><path stroke="currentColor" d="M1 1h22v22H1z"/></svg>'
    called_urls: list[str] = []

    def fake_get(url: str, timeout: float = 15.0) -> bytes:
        called_urls.append(url)
        return sample_svg

    monkeypatch.setattr("core.fetch_assets._http_get_bytes", fake_get)

    out = fetch_icon("simple-icons:wireshark", icons_dir=tmp_path)
    assert out == tmp_path / "wireshark.svg"
    assert out.exists()
    assert called_urls == ["https://api.iconify.design/simple-icons/wireshark.svg"]
    assert 'width="1em"' not in out.read_text(encoding="utf-8")

    # Segunda llamada usa caché en disco sin hacer petición HTTP
    out_cached = fetch_icon("simple-icons:wireshark", icons_dir=tmp_path)
    assert out_cached == out
    assert len(called_urls) == 1


def test_compile_geojson_to_radar_svg_and_fetch_map(tmp_path: Path):
    sample_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"ISO_A3": "PRK", "NAME": "North Korea"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [124.0, 38.0],
                            [130.0, 38.0],
                            [130.0, 42.5],
                            [124.0, 42.5],
                            [124.0, 38.0],
                        ]
                    ],
                },
            },
            {
                "type": "Feature",
                "properties": {"ISO_A3": "KOR", "NAME": "South Korea"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [126.0, 34.0],
                            [129.5, 34.0],
                            [129.5, 38.0],
                            [126.0, 38.0],
                            [126.0, 34.0],
                        ]
                    ],
                },
            },
        ],
    }

    svg = compile_geojson_to_radar_svg(
        sample_geojson,
        primary_queries=["PRK"],
        context_queries=["KOR"],
    )
    assert 'viewBox="0 0 880 680"' in svg
    assert 'fill="var(--accent-primary-soft)"' in svg
    assert 'fill="rgba(148,163,184,0.14)"' in svg

    geojson_file = tmp_path / "ne.geojson"
    geojson_file.write_text(json.dumps(sample_geojson), encoding="utf-8")
    out_map = fetch_map(
        country_queries="PRK",
        name="prk_real",
        context_queries="KOR",
        maps_dir=tmp_path,
        geojson_source=geojson_file,
    )
    assert out_map == tmp_path / "prk_real.svg"
    assert out_map.exists()

    with pytest.raises(ValueError, match="No se encontraron fronteras"):
        compile_geojson_to_radar_svg(sample_geojson, primary_queries=["NO_EXISTE"])


def test_build_audio_normalize_command_and_fetch_audio_cc0(tmp_path: Path, monkeypatch):
    cmd = build_audio_normalize_command(
        tmp_path / "in.ogg",
        tmp_path / "out.wav",
        max_duration=2.5,
    )
    assert "-ar" in cmd and "48000" in cmd
    assert "-c:a" in cmd and "pcm_s16le" in cmd
    assert "-t" in cmd and "2.500" in cmd

    def fake_get(url: str, timeout: float = 15.0) -> bytes:
        if "freesound.org" in url:
            return json.dumps(
                {
                    "results": [
                        {
                            "id": 101,
                            "name": "Mechanical Shutter CC0",
                            "license": "http://creativecommons.org/publicdomain/zero/1.0/",
                            "previews": {"preview-hq-ogg": "https://cdn.freesound.org/shutter.ogg"},
                        }
                    ]
                }
            ).encode("utf-8")
        return b"FAKE_AUDIO_BYTES"

    def fake_run(cmd_list: list[str], check: bool = True):
        out_wav = Path(cmd_list[-1])
        out_wav.write_bytes(b"RIFF_NORMALIZED_WAV")

    monkeypatch.setattr("core.fetch_assets._http_get_bytes", fake_get)
    monkeypatch.setattr("core.fetch_assets.subprocess.run", fake_run)

    out_wav = fetch_audio_cc0(
        name="shutter_real",
        freesound_query="camera shutter",
        kind="sfx",
        target_dir=tmp_path,
        api_key="test_token",
    )
    assert out_wav == tmp_path / "shutter_real.wav"
    assert out_wav.exists()
    assert out_wav.read_bytes() == b"RIFF_NORMALIZED_WAV"

    # Importación desde archivo local (--file) sin red
    local_mp3 = tmp_path / "cine_impact.mp3"
    local_mp3.write_bytes(b"FAKE_MP3")
    out_local = fetch_audio_cc0(
        name="cine_impact",
        source_path=local_mp3,
        kind="sfx",
        target_dir=tmp_path / "out_local",
    )
    assert out_local == tmp_path / "out_local" / "cine_impact.wav"
    assert out_local.exists()

    with pytest.raises(FileNotFoundError, match="archivo de audio local"):
        fetch_audio_cc0(name="missing", source_path=tmp_path / "no_existe.mp3", target_dir=tmp_path)


def test_list_local_assets_inventory(tmp_path: Path):
    inv = list_local_assets()
    assert "icons" in inv and len(inv["icons"]) >= 18
    assert "maps" in inv and "korea" in inv["maps"]
    assert "audio" in inv and "shutter" in inv["audio"]
    assert "music" in inv and "tension_pulse" in inv["music"]
    assert "models" in inv

    seeded = ensure_base_icons(icons_dir=tmp_path)
    assert len(seeded) == len(BASE_ICONS) == 18
    assert (tmp_path / "docker.svg").exists()
    assert (tmp_path / "shield.svg").exists()


def test_fetch_model_validates_glb_and_gltf(tmp_path: Path):
    from core.fetch_assets import fetch_model, validate_3d_model_bytes

    valid_glb = b"glTF" + b"\x02\x00\x00\x00" + b"\x10\x00\x00\x00" + b"\x00\x00\x00\x00"
    src_glb = tmp_path / "src_lamb.glb"
    src_glb.write_bytes(valid_glb)

    models_dir = tmp_path / "models"
    out = fetch_model(name="lamb_model", source_path=src_glb, models_dir=models_dir)
    assert out == models_dir / "lamb_model.glb"
    assert out.exists()
    assert out.read_bytes() == valid_glb

    valid_gltf = json.dumps({"asset": {"version": "2.0"}}).encode("utf-8")
    validate_3d_model_bytes(valid_gltf, ".gltf")

    with pytest.raises(ValueError, match="glTF"):
        validate_3d_model_bytes(b"NOT_A_GLB_FILE", ".glb")

    with pytest.raises(ValueError, match="asset"):
        validate_3d_model_bytes(b'{"meshes": []}', ".gltf")


def test_resolve_blender_and_compile_blender_to_glb(tmp_path: Path, monkeypatch):
    from core.fetch_assets import BASE_BLENDER_MODELS, compile_blender_to_glb, resolve_blender

    fake_blender = tmp_path / "blender.exe"
    fake_blender.write_bytes(b"EXE")
    monkeypatch.setenv("BLENDER_BIN", str(fake_blender))
    assert resolve_blender() == str(fake_blender.resolve())

    monkeypatch.delenv("BLENDER_BIN", raising=False)
    monkeypatch.setattr("core.fetch_assets.shutil.which", lambda name: "/usr/bin/blender")
    assert resolve_blender() == "/usr/bin/blender"

    def fake_run(cmd_list: list[str], check: bool = True, **kwargs):
        script_file = Path(cmd_list[-1])
        text = script_file.read_text(encoding="utf-8")
        assert "export_scene.gltf" in text
        out_file = tmp_path / "models" / "custom_shield.glb"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_bytes(
            b"glTF" + b"\x02\x00\x00\x00" + b"\x10\x00\x00\x00" + b"\x00\x00\x00\x00"
        )

    monkeypatch.setattr("core.fetch_assets.subprocess.run", fake_run)
    out = compile_blender_to_glb(
        name="custom_shield",
        blender_code=BASE_BLENDER_MODELS["shield_3d"],
        decimate_ratio=0.5,
        models_dir=tmp_path / "models",
        force=True,
    )
    assert out == tmp_path / "models" / "custom_shield.glb"
    assert out.exists()
    assert len(BASE_BLENDER_MODELS) == 6
