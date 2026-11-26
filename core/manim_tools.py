#!/usr/bin/env python3
"""
Motor e integrador profesional de Manim Community para video-pipeline.

Conecta animaciones matemáticas, algorítmicas y geométricas de Manim con:
  - El sistema de diseño en 3 niveles (core/styles.py): sincroniza fondo, texto y acentos WCAG AA
    mediante get_pipeline_palette() y variables VP_MANIM_*.
  - Los formatos del pipeline (16:9 horizontal y 9:16 vertical) en presets preview / hd / prod
    y exportación opcional con fondo transparente (--transparent).
  - El motor multi-escena (core/scenes.py): renderiza en --media_dir temporal aislado sin
    ensuciar el repositorio y exporta directo a assets/videos/ o <proyecto>/assets/videos/.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core._runtime import (  # noqa: E402
    REPO_ROOT,
    ensure_local_venv,
    ensure_repo_root_on_path,
    resolve_project_dir,
)

ensure_repo_root_on_path()

from core.styles import (  # noqa: E402
    DEFAULT_THEME,
    THEMES,
    get_theme,
    parse_set_overrides,
)

MANIM_SCRIPTS_DIR = REPO_ROOT / "assets" / "manim"
MANIM_VIDEOS_DIR = REPO_ROOT / "assets" / "videos"

ASPECT_RESOLUTIONS: dict[str, dict[str, tuple[int, int, int]]] = {
    "16:9": {
        "preview": (854, 480, 30),
        "hd": (1280, 720, 30),
        "prod": (1920, 1080, 60),
    },
    "9:16": {
        "preview": (480, 854, 30),
        "hd": (720, 1280, 30),
        "prod": (1080, 1920, 60),
    },
}

MANIM_PRESETS: dict[str, str] = {
    "math_proof": "Ejes coordinados, curva funcional y transformación geométrica limpia (sin LaTeX obligatorio).",
    "algorithm_flow": "Grafo de nodos, aristas animadas y recorrido de estado paso a paso.",
    "vector_field": "Plano cartesiano con vectores, suma geométrica y trazado suave.",
}


@dataclass(frozen=True)
class ManimRenderResult:
    """Resultado estructurado de una compilación de escena Manim."""

    script_path: Path
    scene_class: str
    output_path: Path
    aspect: str
    quality: str
    fps: int
    theme: str
    transparent: bool


def _sanitize_slug(raw: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_\-]+", "_", raw.strip().lower())
    slug = re.sub(r"_+", "_", slug).strip("_")
    if not slug:
        raise ValueError(f"El identificador '{raw}' no contiene caracteres alfanuméricos válidos.")
    return slug


def resolve_manim() -> str:
    """Resuelve el ejecutable de Manim en el .venv local o en PATH (Linux, Windows, macOS)."""
    venv_bin = REPO_ROOT / ".venv" / ("Scripts/manim.exe" if os.name == "nt" else "bin/manim")
    if venv_bin.exists():
        return str(venv_bin)
    found = shutil.which("manim")
    if found:
        return found
    raise FileNotFoundError(
        "No se encontró 'manim' en .venv ni en PATH. Instálalo como extra opcional:\n"
        '  uv pip install -e ".[dev,manim]"'
    )


def check_manim_environment() -> dict[str, Any]:
    """Diagnostica disponibilidad de Manim, FFmpeg y herramientas LaTeX opcionales."""
    info: dict[str, Any] = {
        "manim_available": False,
        "manim_bin": None,
        "manim_version": None,
        "ffmpeg_bin": shutil.which("ffmpeg"),
        "latex_bin": shutil.which("latex") or shutil.which("xelatex"),
        "dvisvgm_bin": shutil.which("dvisvgm"),
        "mathtex_ready": False,
    }
    try:
        manim_bin = resolve_manim()
        info["manim_available"] = True
        info["manim_bin"] = manim_bin
        proc = subprocess.run(
            [manim_bin, "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        ver = (proc.stdout or proc.stderr or "").strip().splitlines()
        info["manim_version"] = ver[0] if ver else None
    except FileNotFoundError:
        pass

    info["mathtex_ready"] = bool(info["latex_bin"] and info["dvisvgm_bin"])
    return info


def manim_theme_palette(
    theme_slug: str = DEFAULT_THEME,
    overrides: dict[str, str] | None = None,
) -> dict[str, str]:
    """Devuelve el diccionario de tokens cromáticos WCAG AA del pipeline listo para Manim."""
    theme = get_theme(theme_slug)
    ov = overrides or {}
    return {
        "theme": theme.slug,
        "color_scheme": theme.color_scheme,
        "bg": ov.get("bg", theme.bg),
        "surface": ov.get("node_fill", theme.node_fill),
        "text_primary": ov.get("text_primary", theme.text_primary),
        "text_secondary": ov.get("text_secondary", theme.text_secondary),
        "text_muted": ov.get("text_muted", theme.text_muted),
        "accent_primary": ov.get("accent_primary", theme.accent_primary),
        "accent_secondary": ov.get("accent_secondary", theme.accent_secondary),
        "accent_tertiary": ov.get("accent_tertiary", theme.accent_tertiary),
        "accent_warning": ov.get("accent_warning", theme.accent_warning),
        "accent_danger": ov.get("accent_danger", theme.accent_danger),
        "cable_idle": ov.get("cable_idle", theme.cable_idle),
        "font_sans": "Inter",
        "font_mono": "JetBrains Mono",
    }


def is_vertical_aspect() -> bool:
    """Devuelve True si la escena Manim se está renderizando en formato vertical 9:16."""
    return os.environ.get("VP_MANIM_ASPECT", "16:9").strip() == "9:16"


def is_transparent_render() -> bool:
    """Devuelve True si la escena Manim se está renderizando con fondo transparente (--transparent)."""
    return os.environ.get("VP_MANIM_TRANSPARENT", "0").strip() == "1"


def apply_pipeline_background(scene: Any, palette: dict[str, str]) -> None:
    """Aplica el color de fondo del tema solo cuando no se solicitó canal alfa transparente."""
    if not is_transparent_render():
        scene.camera.background_color = palette["bg"]


def get_pipeline_palette(default_theme: str = DEFAULT_THEME) -> dict[str, str]:
    """
    Helper importable desde cualquier escena Manim (.py):
        from core.manim_tools import get_pipeline_palette
    Lee el tema inyectado por el pipeline (VP_MANIM_THEME / VP_MANIM_PALETTE_JSON)
    o usa default_theme si la escena se ejecuta manualmente con 'manim'.
    """
    raw_json = os.environ.get("VP_MANIM_PALETTE_JSON")
    if raw_json:
        try:
            parsed = json.loads(raw_json)
            if isinstance(parsed, dict):
                return {str(k): str(v) for k, v in parsed.items()}
        except json.JSONDecodeError:
            pass
    theme_slug = os.environ.get("VP_MANIM_THEME", default_theme)
    return manim_theme_palette(theme_slug)


def detect_scene_classes(script_path: Path) -> list[str]:
    """Extrae los nombres de clases que heredan de *Scene en un archivo Python de Manim."""
    content = script_path.read_text(encoding="utf-8")
    return re.findall(
        r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*Scene[^)]*\)\s*:",
        content,
        flags=re.MULTILINE,
    )


def resolve_resolution_and_fps(
    aspect: str = "16:9",
    quality: str = "prod",
    fps: int | None = None,
) -> tuple[int, int, int]:
    """Resuelve (width, height, fps) deterministas según aspecto y calidad."""
    if aspect not in ASPECT_RESOLUTIONS:
        raise ValueError(
            f"Relación de aspecto '{aspect}' inválida. Opciones: {', '.join(ASPECT_RESOLUTIONS)}."
        )
    if quality not in ASPECT_RESOLUTIONS[aspect]:
        raise ValueError(
            f"Calidad '{quality}' inválida. Opciones: {', '.join(ASPECT_RESOLUTIONS[aspect])}."
        )
    width, height, default_fps = ASPECT_RESOLUTIONS[aspect][quality]
    effective_fps = int(fps) if fps is not None else default_fps
    if effective_fps <= 0:
        raise ValueError(f"FPS inválido: {effective_fps}. Debe ser un entero positivo.")
    return width, height, effective_fps


def build_manim_render_command(
    script_path: Path,
    scene_class: str,
    *,
    media_dir: Path,
    output_filename: str,
    aspect: str = "16:9",
    quality: str = "prod",
    fps: int | None = None,
    transparent: bool = False,
    manim_bin: str = "manim",
) -> list[str]:
    """Construye el comando CLI determinista para renderizar una escena con Manim."""
    width, height, effective_fps = resolve_resolution_and_fps(aspect, quality, fps)
    cmd = [
        manim_bin,
        "render",
        str(script_path),
        scene_class,
        "--resolution",
        f"{width},{height}",
        "--fps",
        str(effective_fps),
        "--media_dir",
        str(media_dir),
        "--output_file",
        output_filename,
        "--disable_caching",
    ]
    if transparent:
        cmd.extend(["--transparent", "--format", "webm"])
    else:
        cmd.extend(["--format", "mp4"])
    return cmd


def build_manim_env(
    theme_slug: str = DEFAULT_THEME,
    overrides: dict[str, str] | None = None,
    aspect: str = "16:9",
    transparent: bool = False,
) -> dict[str, str]:
    """Prepara las variables de entorno para ejecutar Manim sincronizado con el tema del pipeline."""
    palette = manim_theme_palette(theme_slug, overrides=overrides)
    env = os.environ.copy()
    existing_pp = env.get("PYTHONPATH", "")
    repo_str = str(REPO_ROOT)
    if repo_str not in existing_pp.split(os.pathsep):
        env["PYTHONPATH"] = f"{repo_str}{os.pathsep}{existing_pp}" if existing_pp else repo_str
    env["VP_MANIM_THEME"] = palette["theme"]
    env["VP_MANIM_ASPECT"] = aspect
    env["VP_MANIM_TRANSPARENT"] = "1" if transparent else "0"
    env["VP_MANIM_PALETTE_JSON"] = json.dumps(palette)
    return env


def _locate_rendered_video(media_dir: Path, expected_stem: str, ext: str) -> Path:
    """Localiza el archivo de video generado por Manim dentro de media_dir/videos/."""
    candidates = sorted(
        media_dir.rglob(f"{expected_stem}.{ext}"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if candidates:
        return candidates[0]
    fallback = sorted(
        (p for p in media_dir.rglob(f"*.{ext}") if "partial_movie_files" not in p.parts),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if fallback:
        return fallback[0]
    raise FileNotFoundError(
        f"Manim finalizó sin generar el archivo '.{ext}' esperado en {media_dir}."
    )


def render_manim_scene(
    script_path: str | Path,
    scene_class: str | None = None,
    *,
    slug: str | None = None,
    aspect: str = "16:9",
    quality: str = "prod",
    fps: int | None = None,
    theme_slug: str = DEFAULT_THEME,
    overrides: dict[str, str] | None = None,
    transparent: bool = False,
    project: str | Path | None = None,
    output_dir: Path | None = None,
) -> ManimRenderResult:
    """
    Compila una escena Manim en un --media_dir temporal aislado y exporta el clip resultante
    a assets/videos/<slug>.mp4 (o <proyecto>/assets/videos/<slug>.mp4 si se indica --project).
    """
    script = Path(script_path)
    if not script.is_file():
        candidate = MANIM_SCRIPTS_DIR / (
            script.name if script.suffix == ".py" else f"{script.name}.py"
        )
        if candidate.is_file():
            script = candidate
        else:
            raise FileNotFoundError(f"No se encontró el script de Manim: '{script_path}'.")
    script = script.resolve()

    resolved_class = scene_class
    if not resolved_class:
        detected = detect_scene_classes(script)
        if not detected:
            raise ValueError(
                f"No se encontró ninguna subclase de Scene en '{script.name}'. "
                "Indica el nombre de la clase explícitamente."
            )
        resolved_class = detected[0]

    out_slug = _sanitize_slug(slug or f"{script.stem}_{resolved_class}")
    ext = "webm" if transparent else "mp4"
    _, _, effective_fps = resolve_resolution_and_fps(aspect, quality, fps)

    if output_dir is not None:
        dest_dir = Path(output_dir)
    elif project is not None:
        dest_dir = resolve_project_dir(project) / "assets" / "videos"
    else:
        dest_dir = MANIM_VIDEOS_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"{out_slug}.{ext}"

    manim_bin = resolve_manim()
    env = build_manim_env(
        theme_slug=theme_slug, overrides=overrides, aspect=aspect, transparent=transparent
    )

    with tempfile.TemporaryDirectory(prefix="vp_manim_") as tmp_dir:
        media_dir = Path(tmp_dir)
        cmd = build_manim_render_command(
            script_path=script,
            scene_class=resolved_class,
            media_dir=media_dir,
            output_filename=f"{out_slug}.{ext}",
            aspect=aspect,
            quality=quality,
            fps=effective_fps,
            transparent=transparent,
            manim_bin=manim_bin,
        )
        print(
            f"[Manim] Renderizando {script.name}:{resolved_class} "
            f"({aspect}, {quality}, {effective_fps}fps, tema={theme_slug})..."
        )
        subprocess.run(cmd, check=True, env=env)
        rendered_file = _locate_rendered_video(media_dir, out_slug, ext)
        shutil.copy2(rendered_file, dest_path)

    print(f"[Manim] Clip exportado -> {dest_path}")
    return ManimRenderResult(
        script_path=script,
        scene_class=resolved_class,
        output_path=dest_path,
        aspect=aspect,
        quality=quality,
        fps=effective_fps,
        theme=theme_slug,
        transparent=transparent,
    )


def _preset_source(preset: str, class_name: str, default_theme: str) -> str:
    if preset == "algorithm_flow":
        return f'''"""Escena Manim generada por video-pipeline (preset: algorithm_flow)."""

from manim import *

from core.manim_tools import apply_pipeline_background, get_pipeline_palette, is_vertical_aspect


class {class_name}(Scene):
    def construct(self):
        p = get_pipeline_palette("{default_theme}")
        vertical = is_vertical_aspect()
        apply_pipeline_background(self, p)

        title = Text("Flujo de Datos", font=p["font_sans"], color=p["text_primary"]).scale(
            0.55 if vertical else 0.85
        )
        title.to_edge(UP, buff=0.55)

        labels = ["Entrada", "Proceso", "Salida"]
        colors = [p["accent_primary"], p["accent_secondary"], p["accent_tertiary"]]
        box_w = 3.2 if vertical else 2.8
        box_h = 1.1 if vertical else 1.25
        nodes = VGroup()
        for label, color in zip(labels, colors, strict=True):
            box = RoundedRectangle(
                corner_radius=0.18,
                width=box_w,
                height=box_h,
                stroke_color=color,
                stroke_width=3,
                fill_color=p["surface"],
                fill_opacity=0.95,
            )
            txt = Text(label, font=p["font_sans"], color=p["text_primary"]).scale(0.42)
            nodes.add(VGroup(box, txt))

        if vertical:
            nodes.arrange(DOWN, buff=0.65).shift(DOWN * 0.25)
            arrows = VGroup(
                Arrow(nodes[0].get_bottom(), nodes[1].get_top(), buff=0.1, color=p["accent_primary"]),
                Arrow(nodes[1].get_bottom(), nodes[2].get_top(), buff=0.1, color=p["accent_secondary"]),
            )
        else:
            nodes.arrange(RIGHT, buff=0.9)
            arrows = VGroup(
                Arrow(nodes[0].get_right(), nodes[1].get_left(), buff=0.12, color=p["accent_primary"]),
                Arrow(nodes[1].get_right(), nodes[2].get_left(), buff=0.12, color=p["accent_secondary"]),
            )

        self.play(FadeIn(title, shift=DOWN * 0.2), run_time=0.5)
        self.play(LaggedStart(*[FadeIn(n, shift=UP * 0.25) for n in nodes], lag_ratio=0.25), run_time=1.0)
        self.play(LaggedStart(*[GrowArrow(a) for a in arrows], lag_ratio=0.3), run_time=0.8)
        self.play(Indicate(nodes[1][0], color=p["accent_secondary"]), run_time=0.7)
        self.wait(1.0)
'''

    if preset == "vector_field":
        return f'''"""Escena Manim generada por video-pipeline (preset: vector_field)."""

from manim import *

from core.manim_tools import apply_pipeline_background, get_pipeline_palette, is_vertical_aspect


class {class_name}(Scene):
    def construct(self):
        p = get_pipeline_palette("{default_theme}")
        vertical = is_vertical_aspect()
        apply_pipeline_background(self, p)

        plane = NumberPlane(
            x_range=[-3, 3, 1] if vertical else [-5, 5, 1],
            y_range=[-3, 3, 1],
            x_length=3.9 if vertical else 10.0,
            y_length=4.5 if vertical else 6.0,
            background_line_style={{"stroke_color": p["cable_idle"], "stroke_opacity": 0.45}},
            axis_config={{"stroke_color": p["text_muted"]}},
        )
        v1 = Arrow(plane.c2p(0, 0), plane.c2p(1.5, 1.0), buff=0, color=p["accent_primary"], stroke_width=5)
        v2 = Arrow(plane.c2p(1.5, 1.0), plane.c2p(2.5, 2.2), buff=0, color=p["accent_secondary"], stroke_width=5)
        v_sum = Arrow(plane.c2p(0, 0), plane.c2p(2.5, 2.2), buff=0, color=p["accent_warning"], stroke_width=5)

        label = Text("Suma Vectorial", font=p["font_sans"], color=p["text_primary"]).scale(
            0.52 if vertical else 0.75
        )
        label.to_edge(UP, buff=0.5)

        self.play(Create(plane), FadeIn(label), run_time=0.8)
        self.play(GrowArrow(v1), run_time=0.6)
        self.play(GrowArrow(v2), run_time=0.6)
        self.play(GrowArrow(v_sum), run_time=0.8)
        self.wait(1.2)
'''

    # Default: math_proof
    return f'''"""Escena Manim generada por video-pipeline (preset: math_proof)."""

import math

from manim import *

from core.manim_tools import apply_pipeline_background, get_pipeline_palette, is_vertical_aspect


class {class_name}(Scene):
    def construct(self):
        p = get_pipeline_palette("{default_theme}")
        vertical = is_vertical_aspect()
        apply_pipeline_background(self, p)

        axes = Axes(
            x_range=[-4, 4, 1],
            y_range=[-2, 2, 1],
            x_length=3.8 if vertical else 9.0,
            y_length=3.6 if vertical else 4.5,
            axis_config={{"color": p["text_muted"], "include_tip": True}},
        )
        curve_a = axes.plot(lambda x: math.sin(x), color=p["accent_primary"], stroke_width=5)
        curve_b = axes.plot(lambda x: math.cos(x), color=p["accent_secondary"], stroke_width=5)
        area = axes.get_area(curve_a, x_range=[0, math.pi], color=p["accent_primary"], opacity=0.25)

        title = Text("f(x) = sin(x) -> cos(x)", font=p["font_mono"], color=p["text_primary"]).scale(
            0.40 if vertical else 0.65
        )
        title.to_edge(UP, buff=0.6)

        self.play(Create(axes), FadeIn(title, shift=DOWN * 0.2), run_time=0.8)
        self.play(Create(curve_a), run_time=1.0)
        self.play(FadeIn(area), run_time=0.6)
        self.play(Transform(curve_a, curve_b), FadeOut(area), run_time=1.0)
        self.wait(1.0)
'''


def scaffold_manim_scene(
    slug: str,
    *,
    preset: str = "math_proof",
    theme_slug: str = DEFAULT_THEME,
    output_path: Path | None = None,
    force: bool = False,
) -> Path:
    """Crea un archivo .py de escena Manim sincronizado con el sistema de diseño del pipeline."""
    if preset not in MANIM_PRESETS:
        raise ValueError(f"Preset '{preset}' inválido. Opciones: {', '.join(MANIM_PRESETS)}.")
    get_theme(theme_slug)

    clean_slug = _sanitize_slug(slug)
    parts = [p for p in re.split(r"[_-]+", clean_slug) if p]
    class_name = "".join(part.capitalize() for part in parts) + "Scene"
    if not class_name[0].isalpha():
        class_name = f"M{class_name}"

    target = output_path or (MANIM_SCRIPTS_DIR / f"{clean_slug}.py")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not force:
        raise FileExistsError(f"El script '{target}' ya existe. Usa --force para sobrescribir.")

    target.write_text(_preset_source(preset, class_name, theme_slug), encoding="utf-8")
    print(f"[Manim] Escena '{class_name}' creada ({preset}) -> {target}")
    return target


def list_manim_assets(
    scripts_dir: Path | None = None, videos_dir: Path | None = None
) -> dict[str, list[str]]:
    """Lista scripts Manim en assets/manim/ y clips compilados en assets/videos/."""
    s_dir = scripts_dir or MANIM_SCRIPTS_DIR
    v_dir = videos_dir or MANIM_VIDEOS_DIR
    scripts = sorted(p.name for p in s_dir.glob("*.py")) if s_dir.exists() else []
    videos = (
        sorted(
            p.name
            for p in v_dir.iterdir()
            if p.is_file() and p.suffix.lower() in {".mp4", ".webm", ".mov"}
        )
        if v_dir.exists()
        else []
    )
    return {"scripts": scripts, "videos": videos}


def register_manim_subparsers(parser: argparse.ArgumentParser, dest: str = "manim_action") -> None:
    sub = parser.add_subparsers(dest=dest, help="Operaciones del motor Manim integrado")

    sub.add_parser("doctor", help="Verificar instalación de Manim, FFmpeg y LaTeX opcional")

    p_list = sub.add_parser(
        "list", help="Listar scripts en assets/manim/ y clips en assets/videos/"
    )
    p_list.add_argument("--json", action="store_true", help="Exportar inventario en JSON")

    p_new = sub.add_parser("new", help="Crear una escena Manim lista y sincronizada con los temas")
    p_new.add_argument("slug", help="Nombre/slug del archivo (ej. fourier_transform)")
    p_new.add_argument(
        "--preset",
        default="math_proof",
        choices=list(MANIM_PRESETS),
        help="Plantilla inicial de escena Manim",
    )
    p_new.add_argument("-s", "--style", default=DEFAULT_THEME, choices=list(THEMES))
    p_new.add_argument("-o", "--output", help="Ruta alternativa para guardar el archivo .py")
    p_new.add_argument("-f", "--force", action="store_true", help="Sobrescribir si ya existe")

    p_ren = sub.add_parser(
        "render",
        help="Compilar una escena Manim a MP4/WebM y copiarla a assets/videos/ o a un proyecto",
    )
    p_ren.add_argument("script", help="Ruta al script .py o nombre en assets/manim/")
    p_ren.add_argument(
        "scene_class",
        nargs="?",
        default=None,
        help="Clase Scene a renderizar (por defecto detecta la primera del archivo)",
    )
    p_ren.add_argument("--slug", help="Nombre base del clip de salida (sin extensión)")
    p_ren.add_argument(
        "--aspect", default="16:9", choices=list(ASPECT_RESOLUTIONS), help="Formato 16:9 o 9:16"
    )
    p_ren.add_argument(
        "--quality",
        default="prod",
        choices=["preview", "hd", "prod"],
        help="Calidad de renderizado (preview=480p30, hd=720p30, prod=1080p60)",
    )
    p_ren.add_argument("--fps", type=int, default=None, help="FPS explícitos (sobrescribe preset)")
    p_ren.add_argument("-s", "--style", default=DEFAULT_THEME, choices=list(THEMES))
    p_ren.add_argument("--set", dest="overrides", action="append", metavar="CLAVE=VALOR")
    p_ren.add_argument(
        "--transparent",
        action="store_true",
        help="Exportar con canal alfa transparente (.webm) para superponer en HyperFrames",
    )
    p_ren.add_argument(
        "-p",
        "--project",
        help="Proyecto destino donde copiar el clip (<proyecto>/assets/videos/)",
    )


def dispatch_manim_action(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser | None = None,
    action_attr: str = "manim_action",
) -> None:
    action = getattr(args, action_attr, None)
    if not action:
        if parser is not None:
            parser.print_help()
        return

    try:
        if action == "doctor":
            info = check_manim_environment()
            print(json.dumps(info, indent=2, ensure_ascii=False))
            if not info["manim_available"]:
                sys.exit(1)
            return

        if action == "list":
            inv = list_manim_assets()
            if getattr(args, "json", False):
                print(json.dumps(inv, indent=2, ensure_ascii=False))
                return
            print("\n=== INVENTARIO MANIM ===")
            print(f"  Scripts (assets/manim/) : {', '.join(inv['scripts']) or '(ninguno)'}")
            print(f"  Clips   (assets/videos/): {', '.join(inv['videos']) or '(ninguno)'}")
            print()
            return

        if action == "new":
            scaffold_manim_scene(
                slug=args.slug,
                preset=args.preset,
                theme_slug=args.style,
                output_path=Path(args.output) if args.output else None,
                force=args.force,
            )
            return

        if action == "render":
            parsed_ov = parse_set_overrides(args.overrides)
            render_manim_scene(
                script_path=args.script,
                scene_class=args.scene_class,
                slug=args.slug,
                aspect=args.aspect,
                quality=args.quality,
                fps=args.fps,
                theme_slug=args.style,
                overrides=parsed_ov or None,
                transparent=args.transparent,
                project=args.project,
            )
            return
    except (FileNotFoundError, FileExistsError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    ensure_local_venv()
    parser = argparse.ArgumentParser(
        description="Conector Manim Community integrado con video-pipeline"
    )
    register_manim_subparsers(parser)
    args = parser.parse_args()
    dispatch_manim_action(args, parser=parser)


if __name__ == "__main__":
    main()
