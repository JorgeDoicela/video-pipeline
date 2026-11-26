"""
Pruebas unitarias para la integración de Manim Community (core/manim_tools.py y manim_clip en scenes.py).
Funcionan con o sin el binario 'manim' instalado en el entorno (aptas para CI).
"""

import json
from pathlib import Path

import pytest

from core.manim_tools import (
    MANIM_PRESETS,
    SEED_MANIM_SCENES,
    build_manim_env,
    build_manim_render_command,
    detect_scene_classes,
    get_pipeline_palette,
    list_manim_assets,
    manim_theme_palette,
    render_manim_scene,
    resolve_resolution_and_fps,
    scaffold_manim_scene,
    seed_manim_library,
)
from core.scenes import (
    COMPONENT_REGISTRY,
    build_scenes_css,
    inject_storyboard_into_html,
    load_storyboard,
)


def test_manim_theme_palette_syncs_with_all_3_themes():
    for slug in ("dark_violet", "paper_warm", "clean_light"):
        pal = manim_theme_palette(slug)
        assert pal["theme"] == slug
        assert pal["bg"].startswith("#")
        assert pal["accent_primary"].startswith("#")
        assert pal["accent_secondary"].startswith("#")

    custom = manim_theme_palette("dark_violet", overrides={"accent_primary": "#00ff88"})
    assert custom["accent_primary"] == "#00ff88"


def test_get_pipeline_palette_reads_env_json(monkeypatch):
    env = build_manim_env("paper_warm", overrides={"accent_primary": "#b45309"}, aspect="9:16")
    monkeypatch.setenv("VP_MANIM_PALETTE_JSON", env["VP_MANIM_PALETTE_JSON"])
    pal = get_pipeline_palette("dark_violet")
    assert pal["theme"] == "paper_warm"
    assert pal["bg"] == "#f5f1ea"
    assert pal["accent_primary"] == "#b45309"


def test_resolution_and_build_render_command():
    assert resolve_resolution_and_fps("16:9", "prod") == (1920, 1080, 60)
    assert resolve_resolution_and_fps("9:16", "prod") == (1080, 1920, 60)
    assert resolve_resolution_and_fps("9:16", "preview", fps=24) == (480, 854, 24)

    with pytest.raises(ValueError, match="aspecto"):
        resolve_resolution_and_fps("4:3", "prod")
    with pytest.raises(ValueError, match="Calidad"):
        resolve_resolution_and_fps("16:9", "ultra")

    cmd_mp4 = build_manim_render_command(
        Path("demo.py"),
        "DemoScene",
        media_dir=Path("/tmp/m"),
        output_filename="clip.mp4",
        aspect="9:16",
        quality="hd",
        manim_bin="manim",
    )
    assert "--resolution" in cmd_mp4 and "720,1280" in cmd_mp4
    assert "--format" in cmd_mp4 and "mp4" in cmd_mp4
    assert "--transparent" not in cmd_mp4

    cmd_alpha = build_manim_render_command(
        Path("demo.py"),
        "DemoScene",
        media_dir=Path("/tmp/m"),
        output_filename="clip.webm",
        aspect="16:9",
        quality="prod",
        transparent=True,
        manim_bin="manim",
    )
    assert "--transparent" in cmd_alpha
    assert "webm" in cmd_alpha


def test_scaffold_and_detect_scene_classes_for_all_presets(tmp_path):
    assert len(MANIM_PRESETS) == 7
    for preset in MANIM_PRESETS:
        out = tmp_path / f"{preset}.py"
        created = scaffold_manim_scene(
            f"mi_{preset}", preset=preset, theme_slug="paper_warm", output_path=out
        )
        assert created.exists()
        classes = detect_scene_classes(created)
        assert len(classes) == 1
        assert classes[0].endswith("Scene")
        content = created.read_text(encoding="utf-8")
        assert "get_pipeline_palette" in content
        assert '"paper_warm"' in content
        compile(content, str(created), "exec")

    seed_dir = tmp_path / "seeded"
    seeded = seed_manim_library(scripts_dir=seed_dir)
    assert len(seeded) == len(SEED_MANIM_SCENES)
    assert all(p.is_file() for p in seeded)

    with pytest.raises(FileExistsError):
        scaffold_manim_scene("mi_math_proof", output_path=tmp_path / "math_proof.py", force=False)

    # Slugs con guiones o dígito inicial deben generar identificadores de clase Python válidos
    hyphen_file = scaffold_manim_scene(
        "3d-fourier-demo", preset="math_proof", output_path=tmp_path / "3d-fourier-demo.py"
    )
    classes = detect_scene_classes(hyphen_file)
    assert classes == ["M3dFourierDemoScene"]
    assert classes[0].isidentifier()
    compile(hyphen_file.read_text(encoding="utf-8"), str(hyphen_file), "exec")


def test_render_manim_scene_isolated_media_dir_and_copy(tmp_path, monkeypatch):
    script = scaffold_manim_scene(
        "demo_alg", preset="algorithm_flow", output_path=tmp_path / "demo_alg.py"
    )
    out_dir = tmp_path / "out_videos"

    def fake_run(cmd, check=True, env=None):
        media_idx = cmd.index("--media_dir") + 1
        media_dir = Path(cmd[media_idx])
        out_idx = cmd.index("--output_file") + 1
        out_name = cmd[out_idx]
        rendered = media_dir / "videos" / "demo_alg" / "1080p60" / out_name
        rendered.parent.mkdir(parents=True, exist_ok=True)
        rendered.write_bytes(b"MP4DATA")
        assert env is not None and env["VP_MANIM_THEME"] == "clean_light"

    monkeypatch.setattr("core.manim_tools.resolve_manim", lambda: "manim")
    monkeypatch.setattr("core.manim_tools.subprocess.run", fake_run)

    res = render_manim_scene(
        script,
        slug="flujo_algoritmo",
        aspect="16:9",
        quality="prod",
        theme_slug="clean_light",
        output_dir=out_dir,
    )
    assert res.scene_class == "DemoAlgScene"
    assert res.output_path == out_dir / "flujo_algoritmo.mp4"
    assert res.output_path.read_bytes() == b"MP4DATA"

    inv = list_manim_assets(scripts_dir=tmp_path, videos_dir=out_dir)
    assert "demo_alg.py" in inv["scripts"]
    assert "flujo_algoritmo.mp4" in inv["videos"]


def test_manim_clip_component_in_scenes_triggers_on_demand_compile(tmp_path, monkeypatch):
    assert "manim_clip" in COMPONENT_REGISTRY
    css = build_scenes_css(used_components={"manim_clip"})
    assert ".ng-vid-wrap" in css

    proj = tmp_path / "mi_proj"
    proj.mkdir()
    (proj / "package.json").write_text(
        json.dumps(
            {
                "name": "p",
                "videoDesign": {
                    "style": "paper_warm",
                    "overrides": {"accent_primary": "#0f766e"},
                },
            }
        ),
        encoding="utf-8",
    )
    html_file = proj / "index.html"
    html_file.write_text(
        """<!doctype html><html><head><style>:root{}/* @scenes-css:start *//* @scenes-css:end */</style></head>
<body><div id="root" data-composition-id="main"><!-- @scenes:start --><!-- @scenes:end --></div>
<script>const tl = gsap.timeline({paused:true});
// @scenes-gsap:start
// @scenes-gsap:end
window.__timelines={main:tl};</script></body></html>""",
        encoding="utf-8",
    )

    script = scaffold_manim_scene("curva", output_path=proj / "manim" / "curva.py")
    sb_file = proj / "storyboard.json"
    sb_file.write_text(
        json.dumps(
            {
                "title": "Demo Manim",
                "duration": 6.0,
                "aspect_ratio": "9:16",
                "scenes": [
                    {
                        "id": "s_math",
                        "start": 0.0,
                        "end": 6.0,
                        "headline": "Transformación",
                        "component": "manim_clip",
                        "props": {
                            "script": "manim/curva.py",
                            "slug": "curva_demo",
                            "layout_mode": "card",
                            "title": "Seno a Coseno",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    called: list[dict] = []

    def fake_render(**kwargs):
        called.append(kwargs)
        out = Path(kwargs["output_dir"]) / f"{kwargs['slug']}.mp4"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"FAKE_MANIM_MP4")

    monkeypatch.setattr("core.manim_tools.render_manim_scene", fake_render)

    sb = load_storyboard(sb_file)
    inject_storyboard_into_html(html_file, sb)

    assert len(called) == 1
    assert called[0]["script_path"] == script
    assert called[0]["theme_slug"] == "paper_warm"
    assert called[0]["overrides"] == {"accent_primary": "#0f766e"}
    assert called[0]["aspect"] == "9:16"
    assert (proj / "assets" / "videos" / "curva_demo.mp4").exists()

    html_out = html_file.read_text(encoding="utf-8")
    assert 'src="assets/videos/curva_demo.mp4"' in html_out
    assert 'data-start="0.00" data-duration="6.00"' in html_out

    # Si cambia package.json (ej. cambio de tema con pipeline.py style), debe recompilar automáticamente
    import os

    out_clip = proj / "assets" / "videos" / "curva_demo.mp4"
    old_ts = out_clip.stat().st_mtime - 10
    os.utime(out_clip, (old_ts, old_ts))
    (proj / "package.json").write_text(
        json.dumps({"name": "p", "videoDesign": {"style": "clean_light"}}), encoding="utf-8"
    )
    inject_storyboard_into_html(html_file, sb)
    assert len(called) == 2
    assert called[1]["theme_slug"] == "clean_light"
