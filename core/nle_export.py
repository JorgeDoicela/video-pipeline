#!/usr/bin/env python3
"""
Exportador Profesional para Editores NLE (DaVinci Resolve Free/Studio, Premiere Pro, Final Cut Pro).

Genera un paquete de postproducción autocontenido (<proyecto>/export_nle/) con:
  - 01_video_clips/ : Clips cortados por escena/acto (sin audio incrustado). Con --split-layers,
                      separa además fondo/3D limpio (.mp4) y gráficos/texto con canal alfa
                      (ProRes 4444 .mov o .webm transparente).
  - 02_audio_stems/ : Pistas WAV PCM 48kHz 16-bit separadas (stem_voz, stem_musica, stem_sfx
                      o stem_master) para mezclar libremente en el editor.
  - 03_subtitulos/  : Subtítulos editables (.srt / .vtt) si existen en el proyecto.
  - timeline.fcpxml : Proyecto FCPXML v1.10 estándar listo para File -> Import -> Timeline.
  - manifest.json   : Inventario estructurado de activos y tiempos exportados.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
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

from core.audio_mix import (  # noqa: E402
    SfxEvent,
    build_sfx_mix_command,
    resolve_ffmpeg,
)
from core.generate_sfx import ensure_sfx_assets, resolve_music_source  # noqa: E402
from core.scenes import extract_sfx_events, load_storyboard  # noqa: E402


@dataclass(frozen=True)
class TimelineSegment:
    """Segmento temporal (escena o acto) a exportar como clip independiente."""

    index: int
    slug: str
    label: str
    start: float
    end: float

    @property
    def duration(self) -> float:
        return max(0.0, round(self.end - self.start, 4))


@dataclass(frozen=True)
class ExportedClip:
    """Clip de video exportado en disco y vinculado a un segmento temporal."""

    segment: TimelineSegment
    video_path: Path
    overlay_path: Path | None = None


@dataclass(frozen=True)
class ExportedStem:
    """Pista de audio WAV independiente (stem) exportada en 02_audio_stems/."""

    kind: str  # "voz" | "musica" | "sfx" | "master"
    label: str
    path: Path
    duration: float


@dataclass(frozen=True)
class NleExportResult:
    """Resultado completo de la exportación NLE."""

    export_dir: Path
    fcpxml_path: Path
    manifest_path: Path
    clips: list[ExportedClip]
    stems: list[ExportedStem]
    subtitles: list[Path]
    width: int
    height: int
    fps: int
    total_duration: float


def _sanitize_slug(raw: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_\-]+", "_", raw.strip().lower())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "escena"


def read_composition_meta(html_path: Path) -> tuple[int, int, float]:
    """Extrae (width, height, duration) desde el nodo raíz data-composition-id de index.html."""
    content = html_path.read_text(encoding="utf-8")
    w_m = re.search(r'data-width="(\d+)"', content)
    h_m = re.search(r'data-height="(\d+)"', content)
    d_m = re.search(r'data-duration="([0-9.]+)"', content)
    width = int(w_m.group(1)) if w_m else 1920
    height = int(h_m.group(1)) if h_m else 1080
    duration = float(d_m.group(1)) if d_m else 10.0
    return width, height, duration


def parse_cuts_argument(raw_cuts: str | None, total_duration: float) -> list[TimelineSegment]:
    """
    Convierte una lista de marcas temporales (ej. '0,3.7,7.5,11.4') en segmentos contiguos
    hasta total_duration.
    """
    if not raw_cuts or not raw_cuts.strip():
        return []
    points: list[float] = []
    for token in raw_cuts.split(","):
        cleaned = token.strip()
        if not cleaned:
            continue
        val = float(cleaned)
        if val < 0 or val > total_duration + 0.05:
            raise ValueError(
                f"Corte '{val}s' fuera del rango de la composición (0..{total_duration:.2f}s)."
            )
        points.append(min(val, total_duration))

    if not points:
        return []
    points = sorted(set(points))
    if points[0] > 0.02:
        points.insert(0, 0.0)
    if total_duration - points[-1] > 0.05:
        points.append(total_duration)

    segments: list[TimelineSegment] = []
    for idx, (s, e) in enumerate(zip(points, points[1:], strict=False), start=1):
        if e - s < 0.05:
            continue
        segments.append(
            TimelineSegment(
                index=idx,
                slug=f"acto_{idx:02d}",
                label=f"Acto {idx:02d}",
                start=round(s, 3),
                end=round(e, 3),
            )
        )
    return segments


def resolve_timeline_segments(
    project_dir: Path,
    total_duration: float,
    raw_cuts: str | None = None,
) -> list[TimelineSegment]:
    """
    Determina los segmentos de corte del proyecto con precedencia:
      1. --cuts explícitos por CLI
      2. Escenas declaradas en storyboard.json
      3. Segmento único completo (0.0 -> total_duration)
    """
    if raw_cuts:
        segs = parse_cuts_argument(raw_cuts, total_duration)
        if segs:
            return segs

    sb_path = project_dir / "storyboard.json"
    if sb_path.is_file():
        sb = load_storyboard(sb_path)
        if sb.scenes:
            segments: list[TimelineSegment] = []
            for idx, sc in enumerate(sb.scenes, start=1):
                s = max(0.0, min(sc.start, total_duration))
                e = max(s, min(sc.end, total_duration))
                if e - s < 0.05:
                    continue
                label = sc.headline or sc.badge or sc.id
                segments.append(
                    TimelineSegment(
                        index=idx,
                        slug=_sanitize_slug(sc.id),
                        label=label,
                        start=round(s, 3),
                        end=round(e, 3),
                    )
                )
            if segments:
                return segments

    return [
        TimelineSegment(
            index=1,
            slug="escena_completa",
            label="Composición Completa",
            start=0.0,
            end=round(total_duration, 3),
        )
    ]


def build_layer_html(original_html: str, layer: str) -> str:
    """
    Construye una variante HTML no destructiva para renderizar capas separadas:
      - 'bg'      : Solo fondo atmosférico, WebGL 3D y video base (oculta textos/escenas/subtítulos).
      - 'overlay' : Solo tipografía, tarjetas, HUD y subtítulos sobre fondo 100% transparente.
    """
    if layer == "bg":
        inject_css = """
      /* @nle-layer:bg */
      .act, #scenes-stage, #caption-zone, #captions-container, #brand-bar,
      #progress-bar, #timeline-bar, #header, .lower-third, #main-card, #card, .panel {
        visibility: hidden !important;
        opacity: 0 !important;
      }
"""
    elif layer == "overlay":
        inject_css = """
      /* @nle-layer:overlay */
      html, body, #root, #main, [data-composition-id] {
        background: transparent !important;
        background-image: none !important;
      }
      video, #bg-video, #video-layer, .video-bg, #webgl-canvas, #orb-p, #orb-s, .bg-orb,
      #atmo-warm, #atmo-glow, #atmo-vignette, .atmosphere-bg, #atmosphere-rays, #atmosphere-grid {
        visibility: hidden !important;
        opacity: 0 !important;
      }
"""
    else:
        raise ValueError(f"Capa NLE inválida: '{layer}'. Use 'bg' o 'overlay'.")

    if "</style>" in original_html:
        return original_html.replace("</style>", f"{inject_css}    </style>", 1)
    return original_html.replace("</head>", f"  <style>{inject_css}</style>\n  </head>", 1)


def _frames_from_seconds(seconds: float, fps: int) -> int:
    return max(0, round(seconds * fps))


def _rational_from_frames(frames: int, fps: int) -> str:
    """Convierte un conteo exacto de fotogramas a fracción racional FCPXML."""
    if frames <= 0:
        return "0s"
    return f"{frames * 100}/{fps * 100}s"


def _frames_rational(seconds: float, fps: int) -> str:
    """Convierte segundos a fracción racional FCPXML alineada a fotogramas exactos."""
    return _rational_from_frames(_frames_from_seconds(seconds, fps), fps)


def _file_uri(path: Path) -> str:
    return path.resolve().as_uri()


_STANDARD_16_9_FORMATS: set[tuple[int, int]] = {
    (1280, 720),
    (1920, 1080),
    (3840, 2160),
}


def _fcpxml_format_name(width: int, height: int, fps: int) -> str:
    """
    Devuelve el identificador FCPXML estándar para el nodo <format>.
    En FCPXML v1.10 los presets FFVideoFormat<H>p<FPS> aplican solo a 16:9 estándar;
    para vertical 9:16 u otras resoluciones se requiere FFVideoFormatRateUndefined.
    """
    if (width, height) in _STANDARD_16_9_FORMATS:
        return f"FFVideoFormat{height}p{fps}"
    return "FFVideoFormatRateUndefined"


def _compute_segment_frames(segment: TimelineSegment, fps: int) -> tuple[int, int]:
    """Devuelve (start_frame, duration_frames) exactos para un segmento."""
    s_fr = _frames_from_seconds(segment.start, fps)
    e_fr = max(s_fr + 1, _frames_from_seconds(segment.end, fps))
    return s_fr, e_fr - s_fr


def build_fcpxml(
    *,
    project_name: str,
    width: int,
    height: int,
    fps: int,
    total_duration: float,
    clips: list[ExportedClip],
    stems: list[ExportedStem],
) -> str:
    """
    Genera un documento FCPXML v1.10 limpio y estándar compatible con DaVinci Resolve
    (Free y Studio), Premiere Pro y Final Cut Pro.
    """
    root = ET.Element("fcpxml", version="1.10")
    resources = ET.SubElement(root, "resources")

    frame_dur = f"100/{fps * 100}s"
    ET.SubElement(
        resources,
        "format",
        id="r1",
        name=_fcpxml_format_name(width, height, fps),
        frameDuration=frame_dur,
        width=str(width),
        height=str(height),
        colorSpace="1-1-1 (Rec. 709)",
    )

    next_res_id = 2
    video_asset_ids: dict[int, str] = {}
    overlay_asset_ids: dict[int, str] = {}
    stem_asset_ids: dict[str, str] = {}
    clip_frame_bounds: dict[int, tuple[int, int]] = {}

    for clip in clips:
        s_fr, dur_fr = _compute_segment_frames(clip.segment, fps)
        clip_frame_bounds[clip.segment.index] = (s_fr, dur_fr)

        rid = f"r{next_res_id}"
        next_res_id += 1
        video_asset_ids[clip.segment.index] = rid
        asset = ET.SubElement(
            resources,
            "asset",
            id=rid,
            name=clip.video_path.stem,
            start="0s",
            duration=_rational_from_frames(dur_fr, fps),
            hasVideo="1",
            hasAudio="0",
            format="r1",
        )
        ET.SubElement(asset, "media-rep", kind="original-media", src=_file_uri(clip.video_path))

        if clip.overlay_path is not None:
            orid = f"r{next_res_id}"
            next_res_id += 1
            overlay_asset_ids[clip.segment.index] = orid
            ov_asset = ET.SubElement(
                resources,
                "asset",
                id=orid,
                name=clip.overlay_path.stem,
                start="0s",
                duration=_rational_from_frames(dur_fr, fps),
                hasVideo="1",
                hasAudio="0",
                format="r1",
            )
            ET.SubElement(
                ov_asset, "media-rep", kind="original-media", src=_file_uri(clip.overlay_path)
            )

    for stem in stems:
        srid = f"r{next_res_id}"
        next_res_id += 1
        stem_asset_ids[stem.kind] = srid
        s_asset = ET.SubElement(
            resources,
            "asset",
            id=srid,
            name=stem.label,
            start="0s",
            duration=_frames_rational(stem.duration, fps),
            hasVideo="0",
            hasAudio="1",
            audioSources="1",
            audioChannels="2",
            audioRate="48000",
        )
        ET.SubElement(s_asset, "media-rep", kind="original-media", src=_file_uri(stem.path))

    library = ET.SubElement(root, "library")
    event = ET.SubElement(library, "event", name=project_name)
    project = ET.SubElement(event, "project", name=f"{project_name}_NLE")
    sequence = ET.SubElement(
        project,
        "sequence",
        format="r1",
        duration=_frames_rational(total_duration, fps),
        tcStart="0s",
        tcFormat="NDF",
        audioLayout="stereo",
        audioRate="48k",
    )
    spine = ET.SubElement(sequence, "spine")

    anchor_el: ET.Element | None = None
    cursor_fr = 0
    for clip in clips:
        seg = clip.segment
        s_fr, dur_fr = clip_frame_bounds[seg.index]
        if s_fr > cursor_fr:
            gap_el = ET.SubElement(
                spine,
                "gap",
                name="Gap",
                offset=_rational_from_frames(cursor_fr, fps),
                start="0s",
                duration=_rational_from_frames(s_fr - cursor_fr, fps),
            )
            if anchor_el is None:
                anchor_el = gap_el
            cursor_fr = s_fr
        elif s_fr < cursor_fr:
            s_fr = cursor_fr

        clip_el = ET.SubElement(
            spine,
            "asset-clip",
            name=seg.label,
            ref=video_asset_ids[seg.index],
            offset=_rational_from_frames(s_fr, fps),
            start="0s",
            duration=_rational_from_frames(dur_fr, fps),
            format="r1",
        )
        ET.SubElement(
            clip_el,
            "marker",
            start="0s",
            duration=frame_dur,
            value=seg.label,
        )
        if clip.overlay_path is not None:
            ET.SubElement(
                clip_el,
                "asset-clip",
                name=f"{seg.label} (Overlay Alfa)",
                lane="1",
                ref=overlay_asset_ids[seg.index],
                offset="0s",
                start="0s",
                duration=_rational_from_frames(dur_fr, fps),
                format="r1",
            )
        if anchor_el is None:
            anchor_el = clip_el
        cursor_fr = s_fr + dur_fr

    # Conectar stems de audio al primer elemento del spine (siempre en t=0s) en pistas -1, -2, -3
    if anchor_el is not None:
        for lane_idx, stem in enumerate(stems, start=1):
            ET.SubElement(
                anchor_el,
                "asset-clip",
                name=stem.label,
                lane=str(-lane_idx),
                ref=stem_asset_ids[stem.kind],
                offset="0s",
                start="0s",
                duration=_frames_rational(stem.duration, fps),
                role="dialogue"
                if stem.kind == "voz"
                else ("music" if stem.kind == "musica" else "effects"),
            )

    ET.indent(root, space="  ")
    xml_body = ET.tostring(root, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n' + xml_body + "\n"


def _run_ffmpeg(cmd: list[str], context: str) -> None:
    """Ejecuta FFmpeg y expone el error real de stderr si falla."""
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as exc:
        err_text = ""
        if exc.stderr:
            decoded = exc.stderr.decode("utf-8", errors="replace").strip().splitlines()
            err_text = " | ".join(decoded[-4:])
        raise RuntimeError(f"FFmpeg falló al {context}: {err_text or exc}") from exc


def _cut_video_segment(
    ffmpeg_bin: str,
    source_video: Path,
    dest_video: Path,
    start_frame: int,
    frame_count: int,
    fps: int,
    *,
    alpha: bool = False,
) -> None:
    """Recorta un tramo exacto al fotograma sin pista de audio (el audio va en stems)."""
    start_sec = start_frame / fps
    cmd = [
        ffmpeg_bin,
        "-hide_banner",
        "-y",
        "-ss",
        f"{start_sec:.6f}",
        "-i",
        str(source_video),
        "-frames:v",
        str(frame_count),
        "-r",
        str(fps),
        "-an",
    ]
    if alpha:
        if dest_video.suffix.lower() == ".mov":
            cmd.extend(["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le"])
        else:
            cmd.extend(["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "18"])
    else:
        cmd.extend(["-c:v", "libx264", "-crf", "16", "-preset", "fast", "-pix_fmt", "yuv420p"])
    cmd.append(str(dest_video))
    _run_ffmpeg(cmd, f"recortar {dest_video.name}")


def _has_audio_stream(media_path: Path) -> bool:
    """Verifica mediante ffprobe si un medio contiene al menos una pista de audio real."""
    ffprobe_bin = shutil.which("ffprobe")
    if not ffprobe_bin:
        return True
    res = subprocess.run(
        [
            ffprobe_bin,
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(media_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(res.stdout.strip())


def _export_audio_stems(
    project_dir: Path,
    stems_dir: Path,
    total_duration: float,
    ffmpeg_bin: str,
) -> list[ExportedStem]:
    """Exporta las pistas de audio independientes (voz, música, SFX o master) en WAV 48kHz."""
    stems_dir.mkdir(parents=True, exist_ok=True)
    exported: list[ExportedStem] = []

    voice_candidate: Path | None = None
    for name in ("cut.wav", "cut.mp3", "cut.m4a", "cut.mp4"):
        p = project_dir / name
        if p.is_file() and _has_audio_stream(p):
            voice_candidate = p
            break

    sb_path = project_dir / "storyboard.json"
    sb = load_storyboard(sb_path) if sb_path.is_file() else None

    # 1. Stem de voz
    if voice_candidate is not None:
        voice_out = stems_dir / "stem_voz.wav"
        cmd = build_sfx_mix_command(
            voice_path=voice_candidate,
            events=[],
            total_duration=total_duration,
            output_wav=voice_out,
            ffmpeg_bin=ffmpeg_bin,
            voice_polish=bool(sb.voice_polish) if sb else False,
        )
        _run_ffmpeg(cmd, "exportar stem_voz.wav")
        exported.append(ExportedStem("voz", "Voz", voice_out, total_duration))

    # 2. Stem de música / cama ambiental
    if sb is not None:
        sfx_map = ensure_sfx_assets()
        project_music_dir = project_dir / "assets" / "music"
        music_src: Path | None = None
        if sb.music:
            if project_music_dir.is_dir():
                try:
                    music_src = resolve_music_source(sb.music, music_dir=project_music_dir)
                except FileNotFoundError:
                    music_src = None
            if music_src is None:
                music_src = resolve_music_source(sb.music)
        if music_src is None and sb.ambient_bed and "drone" in sfx_map:
            music_src = sfx_map["drone"]
        if music_src is not None:
            music_out = stems_dir / "stem_musica.wav"
            cmd = build_sfx_mix_command(
                voice_path=None,
                events=[],
                total_duration=total_duration,
                output_wav=music_out,
                ffmpeg_bin=ffmpeg_bin,
                music_path=music_src,
                music_volume=0.20,
            )
            _run_ffmpeg(cmd, "exportar stem_musica.wav")
            exported.append(
                ExportedStem("musica", f"Música ({music_src.stem})", music_out, total_duration)
            )

        # 3. Stem de SFX posicionados
        events: list[SfxEvent] = extract_sfx_events(sb, include_sub_events=True)
        resolved_ev = [
            (sfx_map[ev.sfx], ev.time_sec, ev.volume) for ev in events if ev.sfx in sfx_map
        ]
        if resolved_ev:
            sfx_out = stems_dir / "stem_sfx.wav"
            cmd = build_sfx_mix_command(
                voice_path=None,
                events=resolved_ev,
                total_duration=total_duration,
                output_wav=sfx_out,
                ffmpeg_bin=ffmpeg_bin,
            )
            _run_ffmpeg(cmd, "exportar stem_sfx.wav")
            exported.append(ExportedStem("sfx", "Efectos SFX", sfx_out, total_duration))

    # Respaldo para composiciones full-bleed sin storyboard pero con audio_mix.wav
    if not exported:
        audio_mix = project_dir / "audio_mix.wav"
        if audio_mix.is_file():
            master_out = stems_dir / "stem_master.wav"
            shutil.copy2(audio_mix, master_out)
            exported.append(ExportedStem("master", "Audio Master", master_out, total_duration))

    return exported


def _resolve_pnpm_bin() -> str:
    pnpm_bin = shutil.which("pnpm")
    if not pnpm_bin:
        raise FileNotFoundError("No se encontró 'pnpm' en PATH para invocar HyperFrames.")
    return pnpm_bin


def export_nle_package(
    project: str | Path,
    *,
    output_dir: str | Path | None = None,
    cuts: str | None = None,
    split_layers: bool = False,
    alpha_format: str = "mov",
    fps: int = 30,
    rerender: bool = False,
) -> NleExportResult:
    """
    Exporta un proyecto completo como paquete NLE editable (clips por escena, capas alfa
    opcionales, stems de audio WAV, subtítulos SRT/VTT y timeline.fcpxml).
    """
    if alpha_format not in {"mov", "webm"}:
        raise ValueError(
            f"Formato alfa '{alpha_format}' inválido. Use 'mov' (ProRes 4444) o 'webm'."
        )
    if fps <= 0:
        raise ValueError(f"FPS inválido: {fps}. Debe ser un entero positivo.")

    project_dir = resolve_project_dir(project)
    html_path = project_dir / "index.html"
    if not html_path.is_file():
        raise FileNotFoundError(f"No se encontró index.html en '{project_dir}'.")

    width, height, total_duration = read_composition_meta(html_path)
    segments = resolve_timeline_segments(project_dir, total_duration, raw_cuts=cuts)
    ffmpeg_bin = resolve_ffmpeg()

    export_dir = Path(output_dir).resolve() if output_dir else (project_dir / "export_nle")
    clips_dir = export_dir / "01_video_clips"
    stems_dir = export_dir / "02_audio_stems"
    subs_dir = export_dir / "03_subtitulos"
    for stale_dir in (clips_dir, stems_dir, subs_dir):
        if stale_dir.exists():
            shutil.rmtree(stale_dir)
    clips_dir.mkdir(parents=True, exist_ok=True)
    stems_dir.mkdir(parents=True, exist_ok=True)

    # 1. Obtener o renderizar videos fuente (compuesto único o capas bg + overlay alfa)
    master_bg_video: Path
    master_overlay_video: Path | None = None

    if split_layers:
        pnpm_bin = _resolve_pnpm_bin()
        orig_html = html_path.read_text(encoding="utf-8")
        tmp_bg_html = project_dir / "_nle_bg.html"
        tmp_ov_html = project_dir / "_nle_overlay.html"
        master_bg_video = export_dir / "_master_bg.mp4"
        master_overlay_video = export_dir / f"_master_overlay.{alpha_format}"
        try:
            tmp_bg_html.write_text(build_layer_html(orig_html, "bg"), encoding="utf-8")
            tmp_ov_html.write_text(build_layer_html(orig_html, "overlay"), encoding="utf-8")
            print("[NLE] Renderizando capa 1/2: Fondo y 3D limpio...")
            subprocess.run(
                [
                    pnpm_bin,
                    "exec",
                    "hyperframes",
                    "render",
                    str(project_dir.resolve()),
                    "-c",
                    tmp_bg_html.name,
                    "-f",
                    str(fps),
                    "-o",
                    str(master_bg_video.resolve()),
                ],
                check=True,
                cwd=str(REPO_ROOT),
            )
            print(
                f"[NLE] Renderizando capa 2/2: Overlay tipografía/HUD con canal alfa ({alpha_format})..."
            )
            subprocess.run(
                [
                    pnpm_bin,
                    "exec",
                    "hyperframes",
                    "render",
                    str(project_dir.resolve()),
                    "-c",
                    tmp_ov_html.name,
                    "--format",
                    alpha_format,
                    "-f",
                    str(fps),
                    "-o",
                    str(master_overlay_video.resolve()),
                ],
                check=True,
                cwd=str(REPO_ROOT),
            )
        finally:
            for tmp_file in (tmp_bg_html, tmp_ov_html):
                if tmp_file.exists():
                    tmp_file.unlink()
    else:
        default_mp4 = project_dir / f"video_{project_dir.name}.mp4"
        if rerender or not default_mp4.is_file():
            pnpm_bin = _resolve_pnpm_bin()
            print(f"[NLE] Renderizando video base -> {default_mp4.name}...")
            subprocess.run(
                [
                    pnpm_bin,
                    "exec",
                    "hyperframes",
                    "render",
                    str(project_dir.resolve()),
                    "-f",
                    str(fps),
                    "-o",
                    str(default_mp4.resolve()),
                ],
                check=True,
                cwd=str(REPO_ROOT),
            )
        master_bg_video = default_mp4

    # 2. Segmentar clips de video por escena/acto (sin audio incrustado)
    exported_clips: list[ExportedClip] = []
    try:
        for seg in segments:
            s_fr, dur_fr = _compute_segment_frames(seg, fps)
            suffix = "_bg" if split_layers else ""
            clip_out = clips_dir / f"{seg.index:02d}_{seg.slug}{suffix}.mp4"
            _cut_video_segment(
                ffmpeg_bin, master_bg_video, clip_out, s_fr, dur_fr, fps, alpha=False
            )
            ov_out: Path | None = None
            if split_layers and master_overlay_video is not None:
                ov_out = clips_dir / f"{seg.index:02d}_{seg.slug}_overlay.{alpha_format}"
                _cut_video_segment(
                    ffmpeg_bin, master_overlay_video, ov_out, s_fr, dur_fr, fps, alpha=True
                )
            exported_clips.append(
                ExportedClip(segment=seg, video_path=clip_out, overlay_path=ov_out)
            )
    finally:
        # Limpiar siempre masters temporales en modo split_layers, incluso si falla FFmpeg
        if split_layers:
            for tmp_master in (master_bg_video, master_overlay_video):
                if tmp_master is not None and tmp_master.exists():
                    tmp_master.unlink()

    # 3. Exportar stems de audio WAV independientes
    stems = _export_audio_stems(project_dir, stems_dir, total_duration, ffmpeg_bin)

    # 4. Copiar subtítulos SRT/VTT si existen
    subtitles: list[Path] = []
    for sub_name in ("subtitles.srt", "subtitles.vtt"):
        src_sub = project_dir / sub_name
        if src_sub.is_file():
            subs_dir.mkdir(parents=True, exist_ok=True)
            dst_sub = subs_dir / sub_name
            shutil.copy2(src_sub, dst_sub)
            subtitles.append(dst_sub)

    # 5. Generar timeline.fcpxml y manifest.json
    fcpxml_content = build_fcpxml(
        project_name=project_dir.name,
        width=width,
        height=height,
        fps=fps,
        total_duration=total_duration,
        clips=exported_clips,
        stems=stems,
    )
    fcpxml_path = export_dir / "timeline.fcpxml"
    fcpxml_path.write_text(fcpxml_content, encoding="utf-8")

    manifest_data: dict[str, Any] = {
        "project": project_dir.name,
        "resolution": f"{width}x{height}",
        "fps": fps,
        "duration": total_duration,
        "split_layers": split_layers,
        "fcpxml": fcpxml_path.name,
        "clips": [
            {
                "index": c.segment.index,
                "label": c.segment.label,
                "start": c.segment.start,
                "end": c.segment.end,
                "video": str(c.video_path.relative_to(export_dir).as_posix()),
                "overlay": (
                    str(c.overlay_path.relative_to(export_dir).as_posix())
                    if c.overlay_path
                    else None
                ),
            }
            for c in exported_clips
        ],
        "audio_stems": [
            {
                "kind": s.kind,
                "label": s.label,
                "file": str(s.path.relative_to(export_dir).as_posix()),
                "duration": s.duration,
            }
            for s in stems
        ],
        "subtitles": [str(p.relative_to(export_dir).as_posix()) for p in subtitles],
    }
    manifest_path = export_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(
        f"[NLE] Paquete editable exportado ({len(exported_clips)} clip(s), "
        f"{len(stems)} stem(s) audio) -> {export_dir}"
    )
    print(
        f"[NLE] Importar en DaVinci Resolve / Premiere: File -> Import -> Timeline -> {fcpxml_path}"
    )

    return NleExportResult(
        export_dir=export_dir,
        fcpxml_path=fcpxml_path,
        manifest_path=manifest_path,
        clips=exported_clips,
        stems=stems,
        subtitles=subtitles,
        width=width,
        height=height,
        fps=fps,
        total_duration=total_duration,
    )


def register_nle_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("project", help="Nombre o ruta del proyecto a exportar")
    parser.add_argument(
        "-o", "--output", help="Directorio destino (defecto: <proyecto>/export_nle)"
    )
    parser.add_argument(
        "--cuts",
        help="Marcas de corte manuales en segundos separadas por coma (ej. 0,3.7,7.5,11.4)",
    )
    parser.add_argument(
        "--split-layers",
        action="store_true",
        help="Renderizar por separado fondo/3D (.mp4) y overlay tipografía/HUD con canal alfa",
    )
    parser.add_argument(
        "--alpha-format",
        default="mov",
        choices=["mov", "webm"],
        help="Formato de la capa transparente con --split-layers (mov=ProRes 4444, webm=VP9 alfa)",
    )
    parser.add_argument("--fps", type=int, default=30, help="Frame rate del timeline (defecto: 30)")
    parser.add_argument(
        "--rerender",
        action="store_true",
        help="Forzar re-renderizado del MP4 base aunque ya exista en el proyecto",
    )


def main() -> None:
    ensure_local_venv()
    parser = argparse.ArgumentParser(
        description="Exportar paquete NLE editable (clips por escena, capas alfa, stems WAV y FCPXML)"
    )
    register_nle_arguments(parser)
    args = parser.parse_args()
    try:
        export_nle_package(
            args.project,
            output_dir=args.output,
            cuts=args.cuts,
            split_layers=args.split_layers,
            alpha_format=args.alpha_format,
            fps=args.fps,
            rerender=args.rerender,
        )
    except (FileNotFoundError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
