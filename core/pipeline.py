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

_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from core._runtime import ensure_local_venv  # noqa: E402

ensure_local_venv()

from core.audio_mix import mix_storyboard_audio  # noqa: E402
from core.create_project import (  # noqa: E402
    AVAILABLE_TEMPLATES,
    create_project,
    update_composition_duration,
)
from core.cut_silence import (  # noqa: E402
    compute_keep_intervals,
    cut_and_concat,
    detect_silence,
    get_media_duration,
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
    CAPTION_STYLES,
    CHROME_VARIANTS,
    DEFAULT_CAPTION_STYLE,
    DEFAULT_DESIGN,
    DESIGN_SYSTEMS,
    LAYOUT_VARIANTS,
    MOTION_PROFILES,
    THEMES,
    apply_style_to_project,
    get_design_system,
    inspect_project_design,
    parse_set_overrides,
    print_catalog,
)
from core.sync_captions import (  # noqa: E402
    export_srt,
    export_vtt,
    extract_word_list,
    generate_html_and_gsap,
    group_words,
    inject_into_html,
    load_transcript,
)
from core.transcribe import transcribe  # noqa: E402


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
    template: str = "talking_head_16_9",
    design: str = DEFAULT_DESIGN,
    style: str | None = None,
    layout: str | None = None,
    chrome: str | None = None,
    motion: str | None = None,
    caption_style: str | None = None,
    overrides: dict[str, str] | None = None,
    title: str | None = None,
    whisper_model: str = "base",
    language: str = "es",
    noise_db: float = -30.0,
    min_silence: float = 0.45,
    auto_render: bool = False,
    force: bool = False,
    storyboard_path: str | None = None,
    auto_storyboard: bool = False,
):
    """Ejecuta la tubería de producción completa de extremo a extremo."""
    start_time = time.time()
    input_path = Path(input_media).resolve()
    if not input_path.exists():
        print(f"Error: El archivo de entrada '{input_path}' no existe.", file=sys.stderr)
        sys.exit(1)

    design_obj = get_design_system(design)
    resolved_style = style or design_obj.default_theme
    resolved_caption_style = caption_style or design_obj.default_caption_style

    print("\n" + "=" * 65)
    print(" INICIANDO PIPELINE DE PRODUCCIÓN AUDIOVISUAL PROGRAMÁTICA")
    print("=" * 65)
    print(f"  Archivo de entrada : {input_path}")
    print(f"  Nombre del proyecto: {project_name}")
    print(f"  Plantilla base     : {template}")
    print(f"  Diseño Macro (N1)  : {design}")
    print(f"  Tema Visual  (N2)  : {resolved_style}")
    print(f"  Subtítulos   (N2)  : {resolved_caption_style}")
    if overrides:
        print(f"  Overrides    (N3)  : {overrides}")
    print("=" * 65 + "\n")

    # 1. Scaffolding del Proyecto con el Diseño Macro y Variantes Seleccionadas
    print("--> [Paso 1/5] Inicializando estructura y arquitectura de diseño del proyecto...")
    project_dir = create_project(
        name=project_name,
        template=template,
        title=title,
        force=force,
        design=design,
        style=resolved_style,
        layout=layout,
        chrome=chrome,
        motion=motion,
        caption_style=resolved_caption_style,
        overrides=overrides,
    )

    # 2. Recorte Algorítmico de Silencios con FFmpeg
    is_audio_only = input_path.suffix.lower() in AUDIO_EXTENSIONS
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
        model_size=whisper_model,
        language=language,
        device="cpu",
    )

    # 4. Sincronización e Inyección de Subtítulos Cinéticos
    print("\n--> [Paso 4/5] Generando e inyectando subtítulos cinéticos en HTML/GSAP...")
    transcript_data = load_transcript(transcript_path)
    words = extract_word_list(transcript_data)
    if words:
        groups = group_words(words, words_per_group=4, pause_threshold=0.4)
        export_srt(groups, project_dir / "subtitles.srt")
        export_vtt(groups, project_dir / "subtitles.vtt")
        html_code, gsap_code = generate_html_and_gsap(groups, caption_style=resolved_caption_style)
        inject_into_html(
            project_dir / "index.html",
            html_code,
            gsap_code,
            caption_style=resolved_caption_style,
        )
    else:
        print(
            "[Captions] No se detectó habla en la pista de audio; omitiendo subtítulos cinéticos."
        )

    # 4b. Compilación de Storyboard Multi-Escena + Mezcla de Voz y SFX (si aplica)
    effective_sb_path: Path | None = None
    if storyboard_path:
        effective_sb_path = Path(storyboard_path)
    elif auto_storyboard:
        generated_sb = build_storyboard_from_transcript(
            transcript_data,
            title=title or project_name,
            aspect_ratio="16:9" if "16_9" in template else "9:16",
        )
        effective_sb_path = project_dir / "storyboard.json"
        effective_sb_path.write_text(
            json.dumps(generated_sb, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    elif (project_dir / "storyboard.json").exists():
        effective_sb_path = project_dir / "storyboard.json"
    if effective_sb_path is not None:
        print(
            f"\n--> [Storyboard] Sincronizando escenas y mezclando voz + SFX ({effective_sb_path.name})..."
        )
        sb = load_storyboard(effective_sb_path)
        sb = align_storyboard_to_transcript(
            sb, transcript_data, total_duration=cut_dur if cut_dur > 0 else None
        )
        inject_storyboard_into_html(project_dir / "index.html", sb)
        events = extract_sfx_events(sb)
        mixed_wav = mix_storyboard_audio(
            project_dir=project_dir,
            events=events,
            total_duration=sb.duration,
            voice_path=cut_video_path,
        )
        attach_audio_track_to_html(project_dir / "index.html", mixed_wav.name, sb.duration)

    # 5. Auditoría de Estándares HyperFrames (WCAG AA, Motion, Layout)
    print("\n--> [Paso 5/5] Auditando estándares con hyperframes check...")
    pnpm_bin = resolve_pnpm()
    try:
        run_command([pnpm_bin, "exec", "hyperframes", "check", str(project_dir)])
    except subprocess.CalledProcessError:
        print("\nAdvertencia: El linter de HyperFrames reportó observaciones en el proyecto.")

    # 6. Renderizado de Producción (Opcional)
    final_output = project_dir / f"video_{project_name}.mp4"
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

    elapsed = time.time() - start_time
    print("\n" + "=" * 65)
    print(f" PIPELINE COMPLETADO EXITOSAMENTE ({elapsed:.1f} segundos)")
    print("=" * 65)
    print("Directorios y artefactos listos:")
    print(f"  - Escena Web   : {project_dir / 'index.html'}")
    print(
        f"  - Diseño Activo: {design} (tema: {resolved_style}, subtítulos: {resolved_caption_style})"
    )
    print(f"  - Video Cortado: {cut_video_path}")
    print(f"  - Transcripción: {transcript_path}")
    print(f"  - Subtítulos   : {project_dir / 'subtitles.srt'}")
    if auto_render:
        print(f"  - Archivo Final: {final_output}")
    else:
        print("\nComando para previsualizar:")
        print(f"  pnpm exec hyperframes preview {project_dir}")
        print("Comando para cambiar a otro Diseño Macro o ajustar opciones:")
        print(f"  python3 core/pipeline.py style {project_dir.name} -d editorial -s paper_warm")
        print("Comando para renderizar MP4:")
        print(f"  pnpm exec hyperframes render {project_dir} -o {final_output}")
    print("=" * 65 + "\n")


def _add_design_arguments(subparser: argparse.ArgumentParser, default_design: str | None = None):
    """Registra los argumentos de los 3 niveles de diseño en un subparser CLI."""
    subparser.add_argument(
        "-d",
        "--design",
        default=default_design,
        choices=list(DESIGN_SYSTEMS.keys()),
        help=f"Nivel 1: Diseño Macro completo ({', '.join(DESIGN_SYSTEMS.keys())})",
    )
    subparser.add_argument(
        "-s",
        "--style",
        choices=list(THEMES.keys()),
        help=f"Nivel 2: Tema cromático y tipográfico ({', '.join(THEMES.keys())})",
    )
    subparser.add_argument(
        "--layout",
        choices=list(LAYOUT_VARIANTS.keys()),
        help=f"Nivel 2: Variante de distribución interna ({', '.join(LAYOUT_VARIANTS.keys())})",
    )
    subparser.add_argument(
        "--chrome",
        choices=list(CHROME_VARIANTS.keys()),
        help=f"Nivel 2: Variante de marco de ventanas ({', '.join(CHROME_VARIANTS.keys())})",
    )
    subparser.add_argument(
        "--motion",
        choices=list(MOTION_PROFILES.keys()),
        help=f"Nivel 2: Perfil de animación GSAP ({', '.join(MOTION_PROFILES.keys())})",
    )
    subparser.add_argument(
        "--caption-style",
        choices=list(CAPTION_STYLES.keys()),
        help=f"Nivel 2: Estilo de subtítulos cinéticos ({', '.join(CAPTION_STYLES.keys())})",
    )
    subparser.add_argument(
        "--set",
        dest="overrides",
        action="append",
        metavar="CLAVE=VALOR",
        help="Nivel 3: Sobreescribir propiedad puntual de este diseño (ej. --set accent_primary=#ff5500)",
    )


def main():
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
        default="talking_head_16_9",
        choices=list(AVAILABLE_TEMPLATES.keys()),
        help="Plantilla base para el proyecto",
    )
    _add_design_arguments(p_produce, default_design=DEFAULT_DESIGN)
    p_produce.add_argument("--title", help="Título principal para inyectar en la composición")
    p_produce.add_argument(
        "--model", default="base", help="Modelo de Whisper (tiny, base, small, medium)"
    )
    p_produce.add_argument("--language", default="es", help="Idioma para transcripción")
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
        "--auto-render", action="store_true", help="Compilar MP4 automáticamente al concluir"
    )
    p_produce.add_argument(
        "-f", "--force", action="store_true", help="Sobrescribir proyecto si ya existe"
    )

    # Subcomando: captions
    p_caps = subparsers.add_parser(
        "captions", help="Generar y sincronizar subtítulos desde transcript.json"
    )
    p_caps.add_argument("-i", "--input", required=True, help="Ruta a transcript.json")
    p_caps.add_argument("--inject", help="Ruta al index.html donde inyectar subtítulos")
    p_caps.add_argument("--export-srt", help="Ruta de exportación SRT")
    p_caps.add_argument("--export-vtt", help="Ruta de exportación VTT")
    p_caps.add_argument(
        "--caption-style",
        default=DEFAULT_CAPTION_STYLE,
        choices=list(CAPTION_STYLES.keys()),
        help=f"Estilo visual y GSAP de subtítulos (defecto: {DEFAULT_CAPTION_STYLE})",
    )

    # Subcomando: cut
    p_cut = subparsers.add_parser("cut", help="Recortar silencios de un video")
    p_cut.add_argument("-i", "--input", required=True, help="Video o audio crudo")
    p_cut.add_argument("-o", "--output", required=True, help="Video podado de salida")
    p_cut.add_argument("--noise-db", type=float, default=-30.0, help="Umbral de silencio en dB")
    p_cut.add_argument(
        "--min-silence", type=float, default=0.45, help="Duración mínima de silencio en segundos"
    )

    # Subcomando: transcribe
    p_tr = subparsers.add_parser("transcribe", help="Transcribir medios con marcas temporales")
    p_tr.add_argument("-i", "--input", required=True, help="Archivo de audio o video")
    p_tr.add_argument("-o", "--output", required=True, help="JSON de salida")
    p_tr.add_argument("-m", "--model", default="base", help="Modelo de Whisper")
    p_tr.add_argument("-l", "--language", default="es", help="Idioma")

    # Subcomando: scaffold
    p_sc = subparsers.add_parser("scaffold", help="Crear nuevo proyecto desde plantilla")
    p_sc.add_argument("name", help="Nombre del proyecto")
    p_sc.add_argument(
        "-t",
        "--template",
        default="short_quote_9_16",
        choices=list(AVAILABLE_TEMPLATES.keys()),
    )
    _add_design_arguments(p_sc, default_design=DEFAULT_DESIGN)
    p_sc.add_argument("--title", help="Título del video")
    p_sc.add_argument("--duration", type=float, help="Duración en segundos")
    p_sc.add_argument("-f", "--force", action="store_true", help="Sobrescribir")

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
    _add_design_arguments(p_st, default_design=None)
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

    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        sys.exit(0)

    if args.subcommand == "produce":
        parsed_overrides = parse_set_overrides(args.overrides)
        produce_pipeline(
            input_media=args.input,
            project_name=args.project,
            template=args.template,
            design=args.design,
            style=args.style,
            layout=args.layout,
            chrome=args.chrome,
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
        )
    elif args.subcommand == "cut":
        dur = get_media_duration(args.input)
        sil = detect_silence(args.input, args.noise_db, args.min_silence)
        keep = compute_keep_intervals(dur, sil)
        cut_and_concat(args.input, args.output, keep)
    elif args.subcommand == "transcribe":
        transcribe(args.input, args.output, args.model, args.language)
    elif args.subcommand == "captions":
        t_data = load_transcript(Path(args.input))
        w_list = extract_word_list(t_data)
        grps = group_words(w_list)
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
            chrome=args.chrome,
            motion=args.motion,
            caption_style=args.caption_style,
            overrides=parsed_overrides,
        )
    elif args.subcommand == "style":
        if args.list or not args.project:
            print_catalog(as_json=args.json)
        elif args.inspect:
            import json

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
                chrome_slug=args.chrome,
                motion_slug=args.motion,
                overrides=parsed_overrides,
                reset_overrides=args.reset_overrides,
            )
    elif args.subcommand == "check":
        p_dir = (
            Path("projects") / args.project
            if not Path(args.project).exists()
            else Path(args.project)
        )
        run_command([resolve_pnpm(), "exec", "hyperframes", "check", str(p_dir)])
    elif args.subcommand == "render":
        p_dir = (
            Path("projects") / args.project
            if not Path(args.project).exists()
            else Path(args.project)
        )
        out = args.output or str(p_dir / f"video_{p_dir.name}.mp4")
        run_command([resolve_pnpm(), "exec", "hyperframes", "render", str(p_dir), "-o", out])
    elif args.subcommand == "storyboard":
        p_dir = (
            Path("projects") / args.project
            if not Path(args.project).exists()
            else Path(args.project)
        )
        spec_path = Path(args.spec) if args.spec else p_dir / "storyboard.json"
        html_path = p_dir / "index.html"
        sb = load_storyboard(spec_path)
        inject_storyboard_into_html(html_path, sb)
        print(f"Storyboard inyectado en {html_path} ({len(sb.scenes)} escenas)")
        if args.mix_sfx:
            events = extract_sfx_events(sb)
            voice_path = Path(args.audio) if args.audio else None
            mixed_wav = mix_storyboard_audio(
                project_dir=p_dir,
                events=events,
                total_duration=sb.duration,
                voice_path=voice_path,
            )
            attach_audio_track_to_html(html_path, mixed_wav.name, sb.duration)
            print(f"Audio mezclado en {mixed_wav} ({len(events)} eventos SFX)")


if __name__ == "__main__":
    main()
