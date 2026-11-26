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
    "math_proof": "Ejes coordinados, curva funcional, recta tangente dinámica y área bajo la curva.",
    "algorithm_flow": "Grafo de nodos con paquete de datos animado recorriendo el flujo paso a paso.",
    "vector_field": "Plano cartesiano con suma vectorial, paralelogramo y descomposición geométrica.",
    "fourier_epicycles": "Síntesis de Fourier con epiciclos rotatorios y trazado de onda en tiempo real.",
    "neural_network": "Red neuronal multicapa con propagación hacia adelante (forward pass) y pulsos de activación.",
    "matrix_transform": "Transformación lineal 2D de grilla, vectores base (i, j) y área del determinante.",
    "sorting_algorithm": "Algoritmo de ordenamiento visualizado con comparaciones e intercambios animados.",
}

SEED_MANIM_SCENES: dict[str, tuple[str, str]] = {
    "demo_sine_wave": ("math_proof", "dark_violet"),
    "fourier_series": ("fourier_epicycles", "dark_violet"),
    "neural_forward": ("neural_network", "dark_violet"),
    "matrix_transform": ("matrix_transform", "paper_warm"),
    "sorting_bars": ("sorting_algorithm", "clean_light"),
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


def build_scene_header(
    title: str,
    subtitle: str,
    palette: dict[str, str],
    vertical: bool = False,
) -> Any:
    """
    Construye un encabezado tipográfico limpio (sin cajas, cápsulas ni líneas horizontales)
    sincronizado con los tokens del pipeline para cualquier escena Manim.
    """
    from manim import DOWN, UP, Text, VGroup  # import diferido para no exigir manim en CI

    eyebrow = Text(
        subtitle.upper(),
        font=palette["font_mono"],
        color=palette["accent_primary"],
        weight="BOLD",
    ).scale(0.24 if vertical else 0.34)
    heading = Text(
        title,
        font=palette["font_sans"],
        color=palette["text_primary"],
        weight="BOLD",
    ).scale(0.42 if vertical else 0.66)
    group = VGroup(eyebrow, heading).arrange(DOWN, buff=0.14 if vertical else 0.18)
    group.to_edge(UP, buff=0.42 if vertical else 0.45)
    return group


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
    if preset == "fourier_epicycles":
        return f'''"""Escena Manim generada por video-pipeline (preset: fourier_epicycles)."""

import math

from manim import *

from core.manim_tools import (
    apply_pipeline_background,
    build_scene_header,
    get_pipeline_palette,
    is_vertical_aspect,
)


class {class_name}(Scene):
    def construct(self):
        p = get_pipeline_palette("{default_theme}")
        vertical = is_vertical_aspect()
        apply_pipeline_background(self, p)

        header = build_scene_header(
            "Síntesis de Fourier", "Epiciclos · 4 Armónicos", p, vertical=vertical
        )
        harmonics = [1, 3, 5, 7]
        base_r = 0.85 if vertical else 1.45
        origin = np.array([0.0, 1.35, 0.0]) if vertical else np.array([-3.3, -0.35, 0.0])
        wave_start_x = -1.65 if vertical else -0.45
        wave_len = 3.3 if vertical else 6.0
        wave_y_base = -1.65 if vertical else -0.35

        phase = ValueTracker(0.0)
        colors = [
            p["accent_primary"],
            p["accent_secondary"],
            p["accent_tertiary"],
            p["accent_warning"],
        ]

        def epicycle_points(t: float) -> list[np.ndarray]:
            pts = [origin.copy()]
            cur = origin.copy()
            for n in harmonics:
                r = base_r * (4.0 / (n * math.pi)) * 0.55
                angle = n * t
                cur = cur + np.array([r * math.cos(angle), r * math.sin(angle), 0.0])
                pts.append(cur.copy())
            return pts

        epicycles = always_redraw(
            lambda: VGroup(
                *[
                    VGroup(
                        Circle(
                            radius=base_r * (4.0 / (n * math.pi)) * 0.55,
                            color=colors[i % len(colors)],
                            stroke_width=2.0 if i == 0 else 1.5,
                            stroke_opacity=0.65,
                        ).move_to(epicycle_points(phase.get_value())[i]),
                        Line(
                            epicycle_points(phase.get_value())[i],
                            epicycle_points(phase.get_value())[i + 1],
                            color=colors[i % len(colors)],
                            stroke_width=3.0 if i == 0 else 2.2,
                        ),
                    )
                    for i, n in enumerate(harmonics)
                ]
            )
        )

        tip_dot = always_redraw(
            lambda: Dot(
                epicycle_points(phase.get_value())[-1],
                radius=0.07,
                color=p["accent_secondary"],
            )
        )

        def build_wave() -> VMobject:
            t_now = phase.get_value()
            samples = 140
            pts = []
            for k in range(samples):
                u = k / (samples - 1)
                tau = t_now - u * 2.0 * math.pi
                y_sum = sum(
                    base_r * (4.0 / (n * math.pi)) * 0.55 * math.sin(n * tau) for n in harmonics
                )
                x_pos = wave_start_x + u * wave_len
                pts.append(np.array([x_pos, wave_y_base + y_sum, 0.0]))
            mob = VMobject(color=p["accent_primary"], stroke_width=4.0)
            mob.set_points_smoothly(pts)
            return mob

        wave = always_redraw(build_wave)

        connector = always_redraw(
            lambda: DashedLine(
                epicycle_points(phase.get_value())[-1],
                np.array(
                    [
                        wave_start_x,
                        wave_y_base
                        + sum(
                            base_r
                            * (4.0 / (n * math.pi))
                            * 0.55
                            * math.sin(n * phase.get_value())
                            for n in harmonics
                        ),
                        0.0,
                    ]
                ),
                color=p["text_muted"],
                stroke_width=1.8,
                dash_length=0.1,
            )
        )

        baseline = Line(
            np.array([wave_start_x, wave_y_base, 0.0]),
            np.array([wave_start_x + wave_len, wave_y_base, 0.0]),
            color=p["cable_idle"],
            stroke_width=1.5,
        )

        caption = Text(
            "f(t) = (4/pi) * [sin(t) + sin(3t)/3 + sin(5t)/5 + sin(7t)/7]",
            font=p["font_mono"],
            color=p["text_secondary"],
        ).scale(0.22 if vertical else 0.36)
        caption.to_edge(DOWN, buff=0.45)

        self.play(FadeIn(header, shift=DOWN * 0.2), Create(baseline), run_time=0.6)
        self.add(epicycles, wave, connector, tip_dot)
        self.play(FadeIn(caption), run_time=0.4)
        self.play(phase.animate.set_value(4.0 * math.pi), run_time=5.5, rate_func=linear)
        self.wait(0.5)
'''

    if preset == "neural_network":
        return f'''"""Escena Manim generada por video-pipeline (preset: neural_network)."""

from manim import *

from core.manim_tools import (
    apply_pipeline_background,
    build_scene_header,
    get_pipeline_palette,
    is_vertical_aspect,
)


class {class_name}(Scene):
    def construct(self):
        p = get_pipeline_palette("{default_theme}")
        vertical = is_vertical_aspect()
        apply_pipeline_background(self, p)

        header = build_scene_header(
            "Propagación en Red Neuronal", "Forward Pass · Activación", p, vertical=vertical
        )
        layer_sizes = [3, 5, 4, 2]
        layer_names = ["Entrada", "Oculta 1", "Oculta 2", "Salida"]
        layer_colors = [
            p["accent_primary"],
            p["accent_secondary"],
            p["accent_tertiary"],
            p["accent_warning"],
        ]

        x_spacing = 1.05 if vertical else 2.75
        y_spacing = 0.62 if vertical else 0.92
        radius = 0.16 if vertical else 0.26

        layers: list[VGroup] = []
        labels = VGroup()
        for li, (count, name, col) in enumerate(
            zip(layer_sizes, layer_names, layer_colors, strict=True)
        ):
            x_pos = (li - (len(layer_sizes) - 1) / 2.0) * x_spacing
            neurons = VGroup()
            for ni in range(count):
                y_pos = ((count - 1) / 2.0 - ni) * y_spacing - 0.25
                dot = Circle(
                    radius=radius,
                    stroke_color=col,
                    stroke_width=3.0,
                    fill_color=p["surface"],
                    fill_opacity=1.0,
                ).move_to(np.array([x_pos, y_pos, 0.0]))
                dot.set_z_index(3)
                neurons.add(dot)
            layers.append(neurons)
            lbl = Text(name, font=p["font_mono"], color=p["text_secondary"]).scale(
                0.20 if vertical else 0.30
            )
            lbl.move_to(np.array([x_pos, -2.65 if not vertical else -2.15, 0.0]))
            labels.add(lbl)

        edges_by_stage: list[VGroup] = []
        for li in range(len(layers) - 1):
            stage_edges = VGroup()
            for n_src in layers[li]:
                for n_dst in layers[li + 1]:
                    line = Line(
                        n_src.get_center(),
                        n_dst.get_center(),
                        stroke_color=p["cable_idle"],
                        stroke_width=1.4 if vertical else 1.8,
                        stroke_opacity=0.55,
                    )
                    stage_edges.add(line)
            edges_by_stage.append(stage_edges)

        self.play(FadeIn(header, shift=DOWN * 0.2), run_time=0.5)
        self.play(
            LaggedStart(*[Create(st) for st in edges_by_stage], lag_ratio=0.15),
            LaggedStart(*[FadeIn(ly, scale=0.8) for ly in layers], lag_ratio=0.15),
            FadeIn(labels),
            run_time=1.3,
        )

        # Forward pass con pulsos luminosos viajando entre capas
        for li, stage_edges in enumerate(edges_by_stage):
            col = layer_colors[li]
            pulses = [
                ShowPassingFlash(
                    edge.copy().set_stroke(color=col, width=3.5, opacity=1.0),
                    time_width=0.45,
                )
                for edge in stage_edges
            ]
            target_glow = [
                neuron.animate.set_fill(layer_colors[li + 1], opacity=0.85)
                for neuron in layers[li + 1]
            ]
            self.play(*pulses, run_time=0.85)
            self.play(*target_glow, run_time=0.35)

        self.play(Indicate(layers[-1][0], color=p["accent_warning"], scale_factor=1.35), run_time=0.7)
        self.wait(0.8)
'''

    if preset == "matrix_transform":
        return f'''"""Escena Manim generada por video-pipeline (preset: matrix_transform)."""

from manim import *

from core.manim_tools import (
    apply_pipeline_background,
    build_scene_header,
    get_pipeline_palette,
    is_vertical_aspect,
)


class {class_name}(Scene):
    def construct(self):
        p = get_pipeline_palette("{default_theme}")
        vertical = is_vertical_aspect()
        apply_pipeline_background(self, p)

        header = build_scene_header(
            "Transformación Lineal 2D", "Matriz A = [[1.5, 0.8], [0.3, 1.3]]", p, vertical=vertical
        )
        header.set_z_index(10)
        header_mask = BackgroundRectangle(header, color=p["bg"], fill_opacity=0.92, buff=0.18)
        header_mask.set_z_index(9)

        bg_grid = NumberPlane(
            x_range=[-5, 5, 1] if vertical else [-7, 7, 1],
            y_range=[-5, 5, 1] if vertical else [-4, 4, 1],
            background_line_style={{"stroke_color": p["cable_idle"], "stroke_opacity": 0.25}},
            axis_config={{"stroke_color": p["text_muted"], "stroke_opacity": 0.4}},
        )
        grid = NumberPlane(
            x_range=[-4, 4, 1] if vertical else [-6, 6, 1],
            y_range=[-4, 4, 1] if vertical else [-4, 4, 1],
            background_line_style={{"stroke_color": p["accent_primary"], "stroke_opacity": 0.48}},
            axis_config={{"stroke_color": p["text_primary"], "stroke_width": 2.2}},
        )

        unit_sq = Polygon(
            ORIGIN,
            RIGHT,
            RIGHT + UP,
            UP,
            stroke_color=p["accent_warning"],
            stroke_width=2.5,
            fill_color=p["accent_warning"],
            fill_opacity=0.22,
        )
        i_hat = Arrow(ORIGIN, RIGHT, buff=0, color=p["accent_secondary"], stroke_width=6)
        j_hat = Arrow(ORIGIN, UP, buff=0, color=p["accent_tertiary"], stroke_width=6)
        v_vec = Arrow(ORIGIN, RIGHT * 1.0 + UP * 1.5, buff=0, color=p["accent_primary"], stroke_width=6)

        transform_group = VGroup(grid, unit_sq, i_hat, j_hat, v_vec)
        if vertical:
            bg_grid.scale(0.60).shift(DOWN * 0.25)
            transform_group.scale(0.60).shift(DOWN * 0.25)
        else:
            bg_grid.scale(0.84).shift(DOWN * 0.22)
            transform_group.scale(0.84).shift(DOWN * 0.22)

        det_label = Text(
            "det(A) = 1.5 * 1.3 - 0.8 * 0.3 = 1.71x área",
            font=p["font_mono"],
            color=p["text_primary"],
        ).scale(0.24 if vertical else 0.38)
        det_label.to_edge(DOWN, buff=0.42)
        det_label.set_z_index(10)
        det_mask = BackgroundRectangle(det_label, color=p["bg"], fill_opacity=0.92, buff=0.15)
        det_mask.set_z_index(9)

        matrix = [[1.5, 0.8], [0.3, 1.3]]

        self.play(
            FadeIn(bg_grid),
            Create(grid),
            FadeIn(header_mask),
            FadeIn(header, shift=DOWN * 0.2),
            run_time=0.9,
        )
        self.play(FadeIn(unit_sq), GrowArrow(i_hat), GrowArrow(j_hat), GrowArrow(v_vec), run_time=0.9)
        self.wait(0.4)
        self.play(ApplyMatrix(matrix, transform_group), run_time=2.2, rate_func=smooth)
        self.play(FadeIn(det_mask), FadeIn(det_label, shift=UP * 0.15), run_time=0.5)
        self.wait(1.0)
'''

    if preset == "sorting_algorithm":
        return f'''"""Escena Manim generada por video-pipeline (preset: sorting_algorithm)."""

from manim import *

from core.manim_tools import (
    apply_pipeline_background,
    build_scene_header,
    get_pipeline_palette,
    is_vertical_aspect,
)


class {class_name}(Scene):
    def construct(self):
        p = get_pipeline_palette("{default_theme}")
        vertical = is_vertical_aspect()
        apply_pipeline_background(self, p)

        header = build_scene_header(
            "Ordenamiento Paso a Paso", "Algoritmo · Comparación e Intercambio", p, vertical=vertical
        )

        values = [6, 2, 8, 4, 7, 3]
        bar_w = 0.42 if vertical else 0.92
        gap = 0.16 if vertical else 0.35
        scale_h = 0.32 if vertical else 0.46
        base_y = -2.15 if vertical else -2.25

        bars: list[VGroup] = []
        n = len(values)
        total_w = n * bar_w + (n - 1) * gap
        start_x = -total_w / 2.0 + bar_w / 2.0

        for idx, val in enumerate(values):
            h = val * scale_h
            rect = RoundedRectangle(
                corner_radius=0.08,
                width=bar_w,
                height=h,
                stroke_color=p["accent_primary"],
                stroke_width=2.5,
                fill_color=p["surface"],
                fill_opacity=0.95,
            )
            x = start_x + idx * (bar_w + gap)
            rect.move_to(np.array([x, base_y + h / 2.0, 0.0]))
            num = Text(str(val), font=p["font_mono"], color=p["text_primary"]).scale(
                0.28 if vertical else 0.44
            )
            num.next_to(rect, UP, buff=0.14)
            bars.append(VGroup(rect, num))

        self.play(FadeIn(header, shift=DOWN * 0.2), run_time=0.5)
        self.play(LaggedStart(*[FadeIn(b, shift=UP * 0.25) for b in bars], lag_ratio=0.1), run_time=0.8)

        # Bubble Sort real animado (ordenando los elementos en vivo)
        arr = list(values)
        for end in range(n - 1, 0, -1):
            for j in range(end):
                b1, b2 = bars[j], bars[j + 1]
                self.play(
                    b1[0].animate.set_stroke(p["accent_warning"], width=4),
                    b2[0].animate.set_stroke(p["accent_warning"], width=4),
                    run_time=0.18,
                )
                if arr[j] > arr[j + 1]:
                    dx = b2[0].get_center()[0] - b1[0].get_center()[0]
                    self.play(
                        b1.animate.shift(RIGHT * dx),
                        b2.animate.shift(LEFT * dx),
                        run_time=0.28,
                    )
                    arr[j], arr[j + 1] = arr[j + 1], arr[j]
                    bars[j], bars[j + 1] = bars[j + 1], bars[j]
                self.play(
                    bars[j][0].animate.set_stroke(p["accent_primary"], width=2.5),
                    bars[j + 1][0].animate.set_stroke(p["accent_primary"], width=2.5),
                    run_time=0.12,
                )
            self.play(
                bars[end][0].animate.set_stroke(p["accent_secondary"], width=3.5).set_fill(
                    p["accent_secondary"], opacity=0.22
                ),
                run_time=0.18,
            )

        self.play(
            bars[0][0].animate.set_stroke(p["accent_secondary"], width=3.5).set_fill(
                p["accent_secondary"], opacity=0.22
            ),
            run_time=0.25,
        )
        self.wait(0.8)
'''

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


def seed_manim_library(
    *,
    scripts_dir: Path | None = None,
    force: bool = False,
) -> list[Path]:
    """Genera el catálogo completo de escenas semilla profesionales en assets/manim/."""
    target_dir = scripts_dir or MANIM_SCRIPTS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    for slug, (preset, theme_slug) in SEED_MANIM_SCENES.items():
        dest = target_dir / f"{slug}.py"
        if dest.exists() and not force:
            created.append(dest)
            continue
        created.append(
            scaffold_manim_scene(
                slug,
                preset=preset,
                theme_slug=theme_slug,
                output_path=dest,
                force=force,
            )
        )
    return created


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

    p_presets = sub.add_parser(
        "presets", help="Listar los presets profesionales disponibles para 'manim new'"
    )
    p_presets.add_argument("--json", action="store_true", help="Exportar presets en JSON")

    p_seed = sub.add_parser(
        "seed", help="Generar la biblioteca de escenas semilla profesionales en assets/manim/"
    )
    p_seed.add_argument(
        "-f", "--force", action="store_true", help="Sobrescribir scripts semilla existentes"
    )

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

        if action == "presets":
            if getattr(args, "json", False):
                print(json.dumps(MANIM_PRESETS, indent=2, ensure_ascii=False))
                return
            print("\n=== PRESETS PROFESIONALES DE MANIM ===")
            for name, desc in MANIM_PRESETS.items():
                print(f"  - {name:<18} : {desc}")
            print()
            return

        if action == "seed":
            seeded = seed_manim_library(force=args.force)
            print(
                f"[Manim] Catálogo semilla listo ({len(seeded)} escena(s)) en {MANIM_SCRIPTS_DIR}"
            )
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
