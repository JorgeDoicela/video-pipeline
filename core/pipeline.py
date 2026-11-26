#!/usr/bin/env python3
"""
Orquestador CLI Unificado para el Pipeline de Video Programático con IA.
Encadena corte de silencios, transcripción, scaffolding, sistema de diseño en 3 niveles
(Diseño Macro, Variantes Internas y Overrides), sincronización de subtítulos,
auditoría de estándares y renderizado con un único comando.
"""

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core._runtime import (  # noqa: E402
    ensure_local_venv,
    ensure_repo_root_on_path,
    resolve_project_dir,
)

ensure_repo_root_on_path()

from core.audio_mix import mix_storyboard_audio  # noqa: E402
from core.create_project import (  # noqa: E402
    AVAILABLE_TEMPLATES,
    create_project,
    register_scaffold_arguments,
    update_composition_duration,
)
from core.cut_silence import (  # noqa: E402
    compute_keep_intervals,
    cut_and_concat,
    detect_silence,
    get_media_duration,
    register_cut_arguments,
)
from core.fetch_assets import (  # noqa: E402
    dispatch_assets_action,
    register_assets_subparsers,
)
from core.image_tools import (  # noqa: E402
    dispatch_image_action,
    register_image_subparsers,
)
from core.manim_tools import (  # noqa: E402
    dispatch_manim_action,
    register_manim_subparsers,
)
from core.nle_export import (  # noqa: E402
    export_nle_package,
    register_nle_arguments,
)
from core.scenes import (  # noqa: E402
    align_storyboard_to_transcript,
    attach_audio_track_to_html,
    build_storyboard_from_transcript,
    extract_sfx_events,
    inject_storyboard_into_html,
    load_storyboard,
)
from core.styles import (  # noqa: E402
    DEFAULT_DESIGN,
    add_design_arguments,
    apply_style_to_project,
    get_design_system,
    inspect_project_design,
    parse_set_overrides,
    print_catalog,
)
from core.sync_captions import (  # noqa: E402
    clear_captions_in_html,
    export_srt,
    export_vtt,
    extract_word_list,
    generate_html_and_gsap,
    group_words,
    inject_into_html,
    load_transcript,
    register_captions_arguments,
)
from core.transcribe import (  # noqa: E402
    parse_replacements,
    register_transcribe_arguments,
    transcribe,
)
from core.workspace import (  # noqa: E402
    dispatch_profiles_action,
    infer_workspace_root_from_project,
    load_history,
    load_profile,
    print_history_table,
    record_history_event,
    register_profiles_subparsers,
    resolve_workspace_root,
    sanitize_channel_path,
)


def resolve_pnpm() -> str:
    """Resuelve el ejecutable de pnpm de forma portable entre POSIX y Windows (.cmd/.exe)."""
    pnpm_bin = shutil.which("pnpm")
    if not pnpm_bin:
        raise FileNotFoundError(
            "No se encontró 'pnpm' en PATH. Instala Node.js/pnpm antes de ejecutar HyperFrames."
        )
    return pnpm_bin


def run_command(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Ejecuta un comando del sistema informando el binario invocado."""
    print(f"[Exec] {' '.join(cmd)}")
    return subprocess.run(cmd, check=check)


AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac"}


def produce_pipeline(
    input_media: str,
    project_name: str,
    template: str | None = None,
    design: str | None = None,
    style: str | None = None,
    layout: str | None = None,
    motion: str | None = None,
    caption_style: str | None = None,
    overrides: dict[str, str] | None = None,
    title: str | None = None,
    whisper_model: str | None = None,
    language: str | None = None,
    noise_db: float = -30.0,
    min_silence: float = 0.45,
    auto_render: bool = False,
    force: bool = False,
    storyboard_path: str | None = None,
    auto_storyboard: bool = False,
    whisper_prompt: str | None = None,
    whisper_hotwords: str | None = None,
    replacements: dict[str, str] | None = None,
    music_path: str | None = None,
    music_volume: float | None = None,
    ambient_bed: bool = False,
    voice_polish: bool = False,
    skip_cut_silence: bool = False,
    skip_sfx: bool = False,
    words_per_group: int | None = None,
    profile: str | None = None,
    channel: str | None = None,
    output_dir: str | Path | None = None,
    dated: bool = False,
):
    """Ejecuta la tubería de producción completa de extremo a extremo."""
    start_time = time.time()
    input_path = Path(input_media).resolve()
    if not input_path.exists():
        print(f"Error: El archivo de entrada '{input_path}' no existe.", file=sys.stderr)
        sys.exit(1)

    profile_obj = load_profile(profile) if profile else None

    effective_template = template or (profile_obj.template if profile_obj else "talking_head_16_9")
    effective_design = design or (profile_obj.design if profile_obj else DEFAULT_DESIGN)
    design_obj = get_design_system(effective_design)
    resolved_style = (
        style
        if style is not None
        else (profile_obj.style if profile_obj and profile_obj.style else design_obj.default_theme)
    )
    resolved_layout = (
        layout if layout is not None else (profile_obj.layout if profile_obj else None)
    )
    resolved_motion = (
        motion if motion is not None else (profile_obj.motion if profile_obj else None)
    )
    resolved_caption_style = (
        caption_style
        if caption_style is not None
        else (
            profile_obj.caption_style
            if profile_obj and profile_obj.caption_style
            else design_obj.default_caption_style
        )
    )
    merged_overrides: dict[str, str] = dict(profile_obj.overrides) if profile_obj else {}
    if overrides:
        merged_overrides.update(overrides)

    merged_replacements: dict[str, str] = dict(profile_obj.replacements) if profile_obj else {}
    if replacements:
        merged_replacements.update(replacements)

    effective_whisper_model = whisper_model or (
        profile_obj.whisper_model if profile_obj else "base"
    )
    effective_language = language or (profile_obj.language if profile_obj else "es")
    effective_prompt = (
        whisper_prompt
        if whisper_prompt is not None
        else (profile_obj.whisper_prompt if profile_obj else None)
    )
    effective_hotwords = (
        whisper_hotwords
        if whisper_hotwords is not None
        else (profile_obj.whisper_hotwords if profile_obj else None)
    )
    effective_music_arg = (
        music_path if music_path is not None else (profile_obj.music if profile_obj else None)
    )
    effective_music_volume = (
        music_volume
        if music_volume is not None
        else (profile_obj.music_volume if profile_obj else 0.14)
    )
    effective_ambient_bed = ambient_bed or (profile_obj.ambient_bed if profile_obj else False)
    effective_voice_polish = voice_polish or (profile_obj.voice_polish if profile_obj else False)
    effective_wpg_arg = (
        words_per_group
        if words_per_group is not None
        else (profile_obj.words_per_group if profile_obj else None)
    )
    effective_channel_raw = (
        channel if channel is not None else (profile_obj.channel if profile_obj else None)
    )
    channel_rel = sanitize_channel_path(effective_channel_raw)
    effective_channel = channel_rel.as_posix() if channel_rel else ""
    workspace_root = resolve_workspace_root(
        output_dir=output_dir,
        profile_output_root=profile_obj.output_root if profile_obj else None,
    )

    print("\n" + "=" * 65)
    print(" INICIANDO PIPELINE DE PRODUCCIÓN AUDIOVISUAL PROGRAMÁTICA")
    print("=" * 65)
    print(f"  Archivo de entrada : {input_path}")
    print(f"  Nombre del proyecto: {project_name}")
    if profile_obj:
        print(f"  Perfil de canal    : {profile_obj.slug} ({profile_obj.name})")
    if effective_channel:
        print(f"  Canal / Carpeta    : {effective_channel}")
    print(f"  Workspace raíz     : {workspace_root}")
    print(f"  Plantilla base     : {effective_template}")
    print(f"  Diseño Macro (N1)  : {effective_design}")
    print(f"  Tema Visual  (N2)  : {resolved_style}")
    print(f"  Subtítulos   (N2)  : {resolved_caption_style}")
    if merged_overrides:
        print(f"  Overrides    (N3)  : {merged_overrides}")
    print("=" * 65 + "\n")

    # 1. Scaffolding del Proyecto con el Diseño Macro y Variantes Seleccionadas
    print("--> [Paso 1/5] Inicializando estructura y arquitectura de diseño del proyecto...")
    project_dir = create_project(
        name=project_name,
        template=effective_template,
        title=title,
        force=force,
        design=effective_design,
        style=resolved_style,
        layout=resolved_layout,
        motion=resolved_motion,
        caption_style=resolved_caption_style,
        overrides=merged_overrides or None,
        profile=profile,
        channel=effective_channel or None,
        output_dir=workspace_root,
        dated=dated,
        record_history=False,
    )

    # 2. Recorte Algorítmico de Silencios con FFmpeg (u omisión con --no-cut-silence)
    is_audio_only = input_path.suffix.lower() in AUDIO_EXTENSIONS
    if skip_cut_silence:
        cut_video_path = project_dir / f"cut{input_path.suffix.lower()}"
        print(
            "\n--> [Paso 2/5] Preservando pista original sin recorte de silencios (--no-cut-silence)..."
        )
        shutil.copy2(input_path, cut_video_path)
    else:
        cut_video_path = project_dir / ("cut.wav" if is_audio_only else "cut.mp4")
        print("\n--> [Paso 2/5] Analizando pausas y recortando silencios...")
        total_dur = get_media_duration(str(input_path))
        silences = detect_silence(str(input_path), noise_db=noise_db, min_duration=min_silence)
        keep_intervals = compute_keep_intervals(total_dur, silences)
        cut_and_concat(str(input_path), str(cut_video_path), keep_intervals)

    cut_dur = get_media_duration(str(cut_video_path))
    if cut_dur > 0:
        update_composition_duration(project_dir / "index.html", cut_dur)

    # 3. Transcripción con Whisper (Timestamps palabra por palabra)
    transcript_path = project_dir / "transcript.json"
    print("\n--> [Paso 3/5] Transcribiendo audio con faster-whisper (int8)...")
    transcribe(
        audio_path=str(cut_video_path),
        output_path=str(transcript_path),
        model_size=effective_whisper_model,
        language=effective_language,
        device="cpu",
        initial_prompt=effective_prompt,
        hotwords=effective_hotwords,
        replacements=merged_replacements or None,
    )

    # Pre-resolución de storyboard para heredar ritmo y palabras de énfasis en subtítulos
    effective_sb_path: Path | None = None
    preloaded_sb = None
    if storyboard_path:
        effective_sb_path = Path(storyboard_path)
    elif (project_dir / "storyboard.json").exists():
        effective_sb_path = project_dir / "storyboard.json"
    if effective_sb_path is not None and effective_sb_path.exists():
        preloaded_sb = load_storyboard(effective_sb_path)

    # 4. Sincronización e Inyección de Subtítulos Cinéticos
    print("\n--> [Paso 4/5] Generando e inyectando subtítulos cinéticos en HTML/GSAP...")
    transcript_data = load_transcript(transcript_path)
    words = extract_word_list(transcript_data)
    effective_wpg = (
        effective_wpg_arg
        if effective_wpg_arg is not None
        else (preloaded_sb.words_per_group if preloaded_sb and preloaded_sb.words_per_group else 6)
    )
    emphasis_words = preloaded_sb.emphasis_words if preloaded_sb else None
    if words:
        groups = group_words(words, words_per_group=effective_wpg, pause_threshold=0.4)
        export_srt(groups, project_dir / "subtitles.srt")
        export_vtt(groups, project_dir / "subtitles.vtt")
        html_code, gsap_code = generate_html_and_gsap(
            groups,
            caption_style=resolved_caption_style,
            emphasis_words=emphasis_words,
        )
        inject_into_html(
            project_dir / "index.html",
            html_code,
            gsap_code,
            caption_style=resolved_caption_style,
        )
    else:
        clear_captions_in_html(project_dir / "index.html")
        print(
            "[Captions] No se detectó habla en la pista de audio; subtítulos placeholder limpiados."
        )

    # 4b. Compilación de Storyboard Multi-Escena + Mezcla de Voz y SFX (si aplica)
    if effective_sb_path is None and auto_storyboard:
        generated_sb = build_storyboard_from_transcript(
            transcript_data,
            title=title or project_name,
            aspect_ratio="16:9" if "16_9" in effective_template else "9:16",
        )
        effective_sb_path = project_dir / "storyboard.json"
        effective_sb_path.write_text(
            json.dumps(generated_sb, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    if effective_sb_path is not None:
        print(f"\n--> [Storyboard] Sincronizando escenas y audio ({effective_sb_path.name})...")
        sb = preloaded_sb if preloaded_sb is not None else load_storyboard(effective_sb_path)
        if profile_obj:
            if not sb.brand and profile_obj.brand:
                sb.brand = profile_obj.brand
            if not sb.category and profile_obj.category:
                sb.category = profile_obj.category
        sb = align_storyboard_to_transcript(
            sb, transcript_data, total_duration=cut_dur if cut_dur > 0 else None
        )
        inject_storyboard_into_html(project_dir / "index.html", sb)
        events = [] if skip_sfx else extract_sfx_events(sb, include_sub_events=True)
        effective_music = effective_music_arg or sb.music
        use_ambient = effective_ambient_bed or sb.ambient_bed
        use_voice_polish = effective_voice_polish or sb.voice_polish
        if not events and not effective_music and not use_ambient and not use_voice_polish:
            print(
                f"[AudioMix] Sin SFX ni cama adicional; vinculando pista limpia -> {cut_video_path.name}"
            )
            attach_audio_track_to_html(project_dir / "index.html", cut_video_path.name, sb.duration)
        else:
            mixed_wav = mix_storyboard_audio(
                project_dir=project_dir,
                events=events,
                total_duration=sb.duration,
                voice_path=cut_video_path,
                music_path=effective_music,
                music_volume=effective_music_volume,
                ambient_bed=use_ambient,
                voice_polish=use_voice_polish,
            )
            attach_audio_track_to_html(project_dir / "index.html", mixed_wav.name, sb.duration)
    else:
        effective_music = effective_music_arg
        use_ambient = effective_ambient_bed
        if not effective_music and not use_ambient and not effective_voice_polish:
            attach_audio_track_to_html(project_dir / "index.html", cut_video_path.name, cut_dur)
        else:
            mixed_wav = mix_storyboard_audio(
                project_dir=project_dir,
                events=[],
                total_duration=cut_dur,
                voice_path=cut_video_path,
                music_path=effective_music,
                music_volume=effective_music_volume,
                ambient_bed=use_ambient,
                voice_polish=effective_voice_polish,
            )
            attach_audio_track_to_html(project_dir / "index.html", mixed_wav.name, cut_dur)

    # 5. Auditoría de Estándares HyperFrames (WCAG AA, Motion, Layout)
    print("\n--> [Paso 5/5] Auditando estándares con hyperframes check...")
    pnpm_bin = resolve_pnpm()
    try:
        run_command([pnpm_bin, "exec", "hyperframes", "check", str(project_dir)])
    except subprocess.CalledProcessError:
        print("\nAdvertencia: El linter de HyperFrames reportó observaciones en el proyecto.")

    # 6. Renderizado de Producción (Opcional)
    final_output = project_dir / f"video_{project_dir.name}.mp4"
    if auto_render:
        print("\n--> Compilando MP4 final con aceleración GPU...")
        run_command(
            [
                pnpm_bin,
                "exec",
                "hyperframes",
                "render",
                str(project_dir),
                "-o",
                str(final_output),
            ]
        )
        print(f"\n[Éxito] Video final exportado a: {final_output.resolve()}")

    record_history_event(
        workspace_root,
        action="produce",
        project_slug=project_dir.name,
        project_dir=project_dir,
        channel=effective_channel,
        profile=profile_obj.slug if profile_obj else None,
        title=title,
        template=effective_template,
        design=effective_design,
        style=resolved_style,
        layout=resolved_layout,
        motion=resolved_motion,
        duration=cut_dur if cut_dur > 0 else None,
        output_video=final_output if auto_render else None,
    )

    elapsed = time.time() - start_time
    print("\n" + "=" * 65)
    print(f" PIPELINE COMPLETADO EXITOSAMENTE ({elapsed:.1f} segundos)")
    print("=" * 65)
    print("Directorios y artefactos listos:")
    print(f"  - Escena Web   : {project_dir / 'index.html'}")
    print(
        f"  - Diseño Activo: {effective_design} (tema: {resolved_style}, subtítulos: {resolved_caption_style})"
    )
    print(f"  - Video Cortado: {cut_video_path}")
    print(f"  - Transcripción: {transcript_path}")
    srt_path = project_dir / "subtitles.srt"
    if srt_path.exists():
        print(f"  - Subtítulos   : {srt_path}")
    else:
        print("  - Subtítulos   : (sin habla detectada)")
    if auto_render:
        print(f"  - Archivo Final: {final_output}")
    else:
        print("\nComando para previsualizar:")
        print(f"  pnpm exec hyperframes preview {project_dir}")
        print("Comando para cambiar a otro Diseño Macro o ajustar opciones:")
        print(
            f"  uv run python core/pipeline.py style {project_dir.name} -d editorial -s paper_warm"
        )
        print("Comando para renderizar MP4:")
        print(f"  pnpm exec hyperframes render {project_dir} -o {final_output}")
    print("=" * 65 + "\n")


def main():
    ensure_local_venv()
    parser = argparse.ArgumentParser(
        description="Orquestador Maestro del Pipeline de Video Programático con IA",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Comandos disponibles")

    # Subcomando: produce
    p_produce = subparsers.add_parser(
        "produce", help="Ejecutar pipeline completo de principio a fin"
    )
    p_produce.add_argument("-i", "--input", required=True, help="Video o audio crudo de entrada")
    p_produce.add_argument("-p", "--project", required=True, help="Nombre del proyecto destino")
    p_produce.add_argument(
        "-t",
        "--template",
        default=None,
        choices=list(AVAILABLE_TEMPLATES.keys()),
        help="Plantilla base para el proyecto (defecto: del perfil o talking_head_16_9)",
    )
    p_produce.add_argument(
        "--profile",
        help="Perfil de canal/cliente en profiles/<slug>.json o ruta directa",
    )
    p_produce.add_argument(
        "--channel",
        help="Subcarpeta de canal o cliente (ej. tech, editorial, clientes/acme)",
    )
    p_produce.add_argument(
        "--output-dir",
        help="Directorio raíz del workspace de proyectos (o variable VIDEO_PIPELINE_WORKSPACE)",
    )
    p_produce.add_argument(
        "--dated",
        action="store_true",
        help="Prefijar fecha YYYY-MM-DD_ al nombre del directorio del proyecto",
    )
    add_design_arguments(p_produce, default_design=None)
    p_produce.add_argument("--title", help="Título principal para inyectar en la composición")
    p_produce.add_argument(
        "--model", default=None, help="Modelo de Whisper (tiny, base, small, medium)"
    )
    p_produce.add_argument("--language", default=None, help="Idioma para transcripción")
    p_produce.add_argument(
        "--noise-db", type=float, default=-30.0, help="Umbral de ruido para corte (dB)"
    )
    p_produce.add_argument(
        "--min-silence", type=float, default=0.45, help="Duración mínima de silencio (s)"
    )
    p_produce.add_argument(
        "--storyboard",
        help="Ruta opcional a storyboard.json para sincronizar escenas y mezclar SFX con la voz",
    )
    p_produce.add_argument(
        "--auto-storyboard",
        action="store_true",
        help="Generar storyboard.json automáticamente a partir de transcript.json",
    )
    p_produce.add_argument(
        "--prompt",
        help="Prompt inicial de vocabulario técnico para guiar a Whisper (ej. 'Redis, Kubernetes')",
    )
    p_produce.add_argument(
        "--hotwords",
        help="Palabras clave técnicas prioritarias para Whisper separadas por coma",
    )
    p_produce.add_argument(
        "--replace",
        dest="replacements",
        action="append",
        metavar="ERRONEO=CORRECTO",
        help="Corrección determinista de términos en transcripción (ej. --replace lidis=Redis)",
    )
    p_produce.add_argument(
        "--music",
        help="Ruta opcional a pista de música/ambiente para mezclar con ducking automático",
    )
    p_produce.add_argument(
        "--music-volume",
        type=float,
        default=None,
        help="Volumen base de la pista musical/ambiental (defecto: del perfil o 0.14)",
    )
    p_produce.add_argument(
        "--ambient-bed",
        action="store_true",
        help="Activar cama ambiental sintética grave (drone.wav) con ducking automático",
    )
    p_produce.add_argument(
        "--voice-polish",
        action="store_true",
        help="Aplicar cadena de limpieza vocal de estudio FFmpeg (highpass, afftdn, compresor y loudnorm -14 LUFS)",
    )
    p_produce.add_argument(
        "--no-cut-silence",
        action="store_true",
        help="Preservar el audio/video original sin recortar pausas ni silencios",
    )
    p_produce.add_argument(
        "--no-sfx",
        action="store_true",
        help="Suprimir todos los SFX sintéticos del storyboard y conservar la pista limpia",
    )
    p_produce.add_argument(
        "--words-per-group",
        type=int,
        default=None,
        help="Máximo de palabras por bloque de subtítulo de 1-2 líneas balanceadas (defecto: storyboard o 6)",
    )
    p_produce.add_argument(
        "--auto-render", action="store_true", help="Compilar MP4 automáticamente al concluir"
    )
    p_produce.add_argument(
        "-f", "--force", action="store_true", help="Sobrescribir proyecto si ya existe"
    )

    # Subcomando: captions
    p_caps = subparsers.add_parser(
        "captions", help="Generar y sincronizar subtítulos desde transcript.json"
    )
    register_captions_arguments(p_caps)

    # Subcomando: cut
    p_cut = subparsers.add_parser("cut", help="Recortar silencios de un video")
    register_cut_arguments(p_cut)

    # Subcomando: transcribe
    p_tr = subparsers.add_parser("transcribe", help="Transcribir medios con marcas temporales")
    register_transcribe_arguments(p_tr)

    # Subcomando: scaffold
    p_sc = subparsers.add_parser("scaffold", help="Crear nuevo proyecto desde plantilla")
    register_scaffold_arguments(p_sc)

    # Subcomando: style
    p_st = subparsers.add_parser(
        "style",
        help="Conmutar entre Diseños Macro, opciones internas o ajustes puntuales sin perder datos",
    )
    p_st.add_argument(
        "project",
        nargs="?",
        help="Nombre o ruta del proyecto a estilizar (omitir si se usa --list)",
    )
    add_design_arguments(p_st, default_design=None)
    p_st.add_argument(
        "--reset-overrides",
        action="store_true",
        help="Limpiar ajustes individuales (--set) previos del proyecto",
    )
    p_st.add_argument(
        "-l", "--list", action="store_true", help="Listar catálogo completo de los 3 niveles"
    )
    p_st.add_argument(
        "--inspect",
        action="store_true",
        help="Inspeccionar el estado de diseño activo del proyecto",
    )
    p_st.add_argument("--json", action="store_true", help="Exportar catálogo en JSON")

    # Subcomando: check
    p_chk = subparsers.add_parser("check", help="Auditar proyecto con HyperFrames linter")
    p_chk.add_argument("project", help="Ruta o nombre del proyecto")

    # Subcomando: render
    p_rnd = subparsers.add_parser("render", help="Renderizar proyecto a MP4")
    p_rnd.add_argument("project", help="Ruta o nombre del proyecto")
    p_rnd.add_argument("-o", "--output", help="Ruta del video MP4 de salida")

    # Subcomando: storyboard
    p_sb = subparsers.add_parser(
        "storyboard",
        help="Compilar storyboard multi-escena en index.html y mezclar pista SFX",
    )
    p_sb.add_argument("project", help="Ruta o nombre del proyecto")
    p_sb.add_argument(
        "--spec",
        help="Ruta a storyboard.json (por defecto: <proyecto>/storyboard.json)",
    )
    p_sb.add_argument(
        "--audio",
        help="Ruta opcional de pista de voz (WAV/MP3/M4A) para mezclar con SFX",
    )
    p_sb.add_argument(
        "--mix-sfx",
        action="store_true",
        help="Mezclar eventos SFX (y voz si se indica --audio) en audio_mix.wav",
    )
    p_sb.add_argument(
        "--music",
        help="Ruta opcional a pista musical para mezclar con ducking",
    )
    p_sb.add_argument(
        "--music-volume",
        type=float,
        default=0.14,
        help="Volumen base de pista musical (defecto: 0.14)",
    )
    p_sb.add_argument(
        "--ambient-bed",
        action="store_true",
        help="Activar cama ambiental sintética (drone.wav) con ducking",
    )
    p_sb.add_argument(
        "--voice-polish",
        action="store_true",
        help="Aplicar limpieza vocal de estudio FFmpeg (highpass, afftdn, compresor y loudnorm -14 LUFS)",
    )

    # Subcomando: assets
    p_assets = subparsers.add_parser(
        "assets",
        help="Descargar y gestionar assets abiertos (Iconify SVG, mapas Natural Earth CC0, audio CC0 y modelos 3D glTF/GLB)",
    )
    register_assets_subparsers(p_assets, dest="asset_action")

    # Subcomando: image
    p_image = subparsers.add_parser(
        "image",
        help="Recortar, convertir y quitar el fondo de imágenes (rembg IA local ONNX / color, crop, convert)",
    )
    register_image_subparsers(p_image, dest="image_action")

    # Subcomando: manim
    p_manim = subparsers.add_parser(
        "manim",
        help="Crear, diagnosticar y renderizar escenas Manim sincronizadas con los temas del pipeline",
    )
    register_manim_subparsers(p_manim, dest="manim_action")

    # Subcomando: export-nle
    p_nle = subparsers.add_parser(
        "export-nle",
        help="Exportar paquete editable para DaVinci Resolve / Premiere (clips por escena, capas alfa, stems WAV y timeline.fcpxml)",
    )
    register_nle_arguments(p_nle)

    # Subcomando: profiles
    p_profiles = subparsers.add_parser(
        "profiles",
        help="Gestionar perfiles de canal y cliente (profiles/*.json)",
    )
    register_profiles_subparsers(p_profiles, dest="profile_action")

    # Subcomando: history
    p_hist = subparsers.add_parser(
        "history",
        help="Consultar el historial de videos producidos y renderizados (catalog.jsonl)",
    )
    p_hist.add_argument("--channel", help="Filtrar historial por canal (ej. tech)")
    p_hist.add_argument("--profile", help="Filtrar historial por slug de perfil")
    p_hist.add_argument("--limit", type=int, default=20, help="Máximo de registros a mostrar")
    p_hist.add_argument("--output-dir", help="Directorio raíz del workspace a consultar")
    p_hist.add_argument("--json", action="store_true", help="Exportar historial en JSON")

    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        sys.exit(0)

    if args.subcommand == "produce":
        parsed_overrides = parse_set_overrides(args.overrides)
        parsed_replacements = parse_replacements(args.replacements)
        produce_pipeline(
            input_media=args.input,
            project_name=args.project,
            template=args.template,
            design=args.design,
            style=args.style,
            layout=args.layout,
            motion=args.motion,
            caption_style=args.caption_style,
            overrides=parsed_overrides,
            title=args.title,
            whisper_model=args.model,
            language=args.language,
            noise_db=args.noise_db,
            min_silence=args.min_silence,
            auto_render=args.auto_render,
            force=args.force,
            storyboard_path=args.storyboard,
            auto_storyboard=args.auto_storyboard,
            whisper_prompt=args.prompt,
            whisper_hotwords=args.hotwords,
            replacements=parsed_replacements,
            music_path=args.music,
            music_volume=args.music_volume,
            ambient_bed=args.ambient_bed,
            voice_polish=args.voice_polish,
            skip_cut_silence=args.no_cut_silence,
            skip_sfx=args.no_sfx,
            words_per_group=args.words_per_group,
            profile=args.profile,
            channel=args.channel,
            output_dir=args.output_dir,
            dated=args.dated,
        )
    elif args.subcommand == "cut":
        dur = get_media_duration(args.input)
        sil = detect_silence(args.input, args.noise_db, args.min_silence)
        keep = compute_keep_intervals(dur, sil)
        cut_and_concat(args.input, args.output, keep)
    elif args.subcommand == "transcribe":
        transcribe(
            args.input,
            args.output,
            args.model,
            args.language,
            device=args.device,
            initial_prompt=args.prompt,
            hotwords=args.hotwords,
            replacements=parse_replacements(args.replacements),
        )
    elif args.subcommand == "captions":
        t_data = load_transcript(Path(args.input))
        w_list = extract_word_list(t_data)
        grps = group_words(
            w_list,
            words_per_group=args.words_per_group,
            pause_threshold=args.pause_threshold,
        )
        if args.export_srt:
            export_srt(grps, Path(args.export_srt))
        if args.export_vtt:
            export_vtt(grps, Path(args.export_vtt))
        h_code, g_code = generate_html_and_gsap(grps, caption_style=args.caption_style)
        if args.inject:
            inject_into_html(
                Path(args.inject),
                h_code,
                g_code,
                caption_style=args.caption_style,
            )
    elif args.subcommand == "scaffold":
        parsed_overrides = parse_set_overrides(args.overrides)
        create_project(
            args.name,
            args.template,
            args.title,
            args.duration,
            args.force,
            design=args.design,
            style=args.style,
            layout=args.layout,
            motion=args.motion,
            caption_style=args.caption_style,
            overrides=parsed_overrides,
            profile=args.profile,
            channel=args.channel,
            output_dir=args.output_dir,
            dated=args.dated,
        )
    elif args.subcommand == "style":
        if args.list or not args.project:
            print_catalog(as_json=args.json)
        elif args.inspect:
            state = inspect_project_design(args.project)
            print(json.dumps(state, indent=2, ensure_ascii=False))
        else:
            parsed_overrides = parse_set_overrides(args.overrides)
            apply_style_to_project(
                project_or_html=args.project,
                theme_slug=args.style,
                caption_style_slug=args.caption_style,
                design_slug=args.design,
                layout_slug=args.layout,
                motion_slug=args.motion,
                overrides=parsed_overrides,
                reset_overrides=args.reset_overrides,
            )
    elif args.subcommand == "check":
        p_dir = resolve_project_dir(args.project)
        run_command([resolve_pnpm(), "exec", "hyperframes", "check", str(p_dir)])
    elif args.subcommand == "render":
        p_dir = resolve_project_dir(args.project)
        out = args.output or str(p_dir / f"video_{p_dir.name}.mp4")
        run_command([resolve_pnpm(), "exec", "hyperframes", "render", str(p_dir), "-o", out])
        pkg_meta: dict = {}
        pkg_file = p_dir / "package.json"
        if pkg_file.exists():
            try:
                pkg_meta = json.loads(pkg_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pkg_meta = {}
        v_proj = pkg_meta.get("videoProject", {})
        v_design = pkg_meta.get("videoDesign", {})
        record_history_event(
            infer_workspace_root_from_project(p_dir, v_proj.get("channel")),
            action="render",
            project_slug=p_dir.name,
            project_dir=p_dir,
            channel=v_proj.get("channel"),
            profile=v_proj.get("profile"),
            title=v_proj.get("title"),
            template=v_proj.get("template"),
            design=v_design.get("design"),
            style=v_design.get("style"),
            layout=v_design.get("layout"),
            motion=v_design.get("motion"),
            output_video=out,
        )
    elif args.subcommand == "storyboard":
        p_dir = resolve_project_dir(args.project)
        spec_path = Path(args.spec) if args.spec else p_dir / "storyboard.json"
        html_path = p_dir / "index.html"
        sb = load_storyboard(spec_path)
        inject_storyboard_into_html(html_path, sb)
        print(f"Storyboard inyectado en {html_path} ({len(sb.scenes)} escenas)")
        if args.mix_sfx:
            events = extract_sfx_events(sb, include_sub_events=True)
            voice_path = Path(args.audio) if args.audio else None
            mixed_wav = mix_storyboard_audio(
                project_dir=p_dir,
                events=events,
                total_duration=sb.duration,
                voice_path=voice_path,
                music_path=args.music or sb.music,
                music_volume=args.music_volume,
                ambient_bed=args.ambient_bed or sb.ambient_bed,
                voice_polish=args.voice_polish or sb.voice_polish,
            )
            attach_audio_track_to_html(html_path, mixed_wav.name, sb.duration)
            print(f"Audio mezclado en {mixed_wav} ({len(events)} eventos SFX)")
    elif args.subcommand == "assets":
        dispatch_assets_action(args, action_attr="asset_action")
    elif args.subcommand == "image":
        dispatch_image_action(args, parser=p_image, action_attr="image_action")
    elif args.subcommand == "manim":
        dispatch_manim_action(args, parser=p_manim, action_attr="manim_action")
    elif args.subcommand == "export-nle":
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
    elif args.subcommand == "profiles":
        dispatch_profiles_action(args, action_attr="profile_action")
    elif args.subcommand == "history":
        ws_root = resolve_workspace_root(output_dir=args.output_dir)
        records = load_history(
            ws_root,
            channel=args.channel,
            profile=args.profile,
            limit=args.limit,
        )
        print_history_table(records, as_json=args.json)


if __name__ == "__main__":
    main()
