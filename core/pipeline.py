#!/usr/bin/env python3
"""
Orquestador CLI Unificado para el Pipeline de Video Programático con IA.
Encadena corte de silencios, transcripción, scaffolding, sincronización de subtítulos,
auditoría de estándares y renderizado con un único comando unificado.
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

# Auto-ejecución con el entorno virtual local si no está activo
_REPO_ROOT = Path(__file__).resolve().parent.parent
_VENV_DIR = _REPO_ROOT / ".venv"
_VENV_PY = _VENV_DIR / "bin" / "python"
if _VENV_PY.exists() and sys.prefix != str(_VENV_DIR):
    os.execv(str(_VENV_PY), [str(_VENV_PY), *sys.argv])

try:
    from core.create_project import create_project
    from core.cut_silence import (
        compute_keep_intervals,
        cut_and_concat,
        detect_silence,
        get_media_duration,
    )
    from core.sync_captions import (
        export_srt,
        export_vtt,
        extract_word_list,
        generate_html_and_gsap,
        group_words,
        inject_into_html,
        load_transcript,
    )
    from core.transcribe import transcribe
except ModuleNotFoundError:
    from create_project import create_project  # type: ignore
    from cut_silence import (  # type: ignore
        compute_keep_intervals,
        cut_and_concat,
        detect_silence,
        get_media_duration,
    )
    from sync_captions import (  # type: ignore
        export_srt,
        export_vtt,
        extract_word_list,
        generate_html_and_gsap,
        group_words,
        inject_into_html,
        load_transcript,
    )
    from transcribe import transcribe  # type: ignore


def run_command(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Ejecuta un comando del sistema informando el binario invocado."""
    print(f"[Exec] {' '.join(cmd)}")
    return subprocess.run(cmd, check=check)


def produce_pipeline(
    input_media: str,
    project_name: str,
    template: str = "talking_head",
    title: str | None = None,
    whisper_model: str = "base",
    language: str = "es",
    noise_db: float = -30.0,
    min_silence: float = 0.45,
    auto_render: bool = False,
    force: bool = False,
):
    """Ejecuta la tubería de producción completa de extremo a extremo."""
    start_time = time.time()
    input_path = Path(input_media).resolve()
    if not input_path.exists():
        print(f"Error: El archivo de entrada '{input_path}' no existe.", file=sys.stderr)
        sys.exit(1)

    print("\n" + "=" * 65)
    print(" INICIANDO PIPELINE DE PRODUCCIÓN AUDIOVISUAL PROGRAMÁTICA")
    print("=" * 65)
    print(f"  Archivo de entrada: {input_path}")
    print(f"  Nombre del proyecto: {project_name}")
    print(f"  Plantilla base:     {template}")
    print("=" * 65 + "\n")

    # 1. Scaffolding del Proyecto
    print("--> [Paso 1/5] Inicializando estructura del proyecto...")
    project_dir = create_project(
        name=project_name,
        template=template,
        title=title,
        force=force,
    )

    # 2. Recorte Algorítmico de Silencios con FFmpeg
    cut_video_path = project_dir / "cut.mp4"
    print("\n--> [Paso 2/5] Analizando pausas y recortando silencios...")
    total_dur = get_media_duration(str(input_path))
    silences = detect_silence(str(input_path), noise_db=noise_db, min_duration=min_silence)
    keep_intervals = compute_keep_intervals(total_dur, silences)
    cut_and_concat(str(input_path), str(cut_video_path), keep_intervals)

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
        html_code, gsap_code = generate_html_and_gsap(groups)
        inject_into_html(project_dir / "index.html", html_code, gsap_code)
    else:
        print(
            "[Captions] No se detectó habla en la pista de audio; omitiendo subtítulos cinéticos."
        )

    # 5. Auditoría de Estándares HyperFrames (WCAG AA, Motion, Layout)
    print("\n--> [Paso 5/5] Auditando estándares con hyperframes check...")
    try:
        run_command(["pnpm", "exec", "hyperframes", "check", str(project_dir)])
    except subprocess.CalledProcessError:
        print("\nAdvertencia: El linter de HyperFrames reportó observaciones en el proyecto.")

    # 6. Renderizado de Producción (Opcional)
    final_output = project_dir / f"video_{project_name}.mp4"
    if auto_render:
        print("\n--> Compilando MP4 final con aceleración GPU...")
        run_command(
            [
                "pnpm",
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
    print(f"  - Escena Web: {project_dir / 'index.html'}")
    print(f"  - Video Cortado: {cut_video_path}")
    print(f"  - Transcripción: {transcript_path}")
    print(f"  - Subtítulos: {project_dir / 'subtitles.srt'}")
    if auto_render:
        print(f"  - Archivo Final: {final_output}")
    else:
        print("\nComando para previsualizar:")
        print(f"  pnpm exec hyperframes preview {project_dir}")
        print("Comando para renderizar MP4:")
        print(f"  pnpm exec hyperframes render {project_dir} -o {final_output}")
    print("=" * 65 + "\n")


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
        default="talking_head",
        choices=["portrait_9_16", "landscape_16_9", "square_1_1", "talking_head", "tech_explainer"],
        help="Plantilla base para el proyecto",
    )
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
        default="portrait_9_16",
        choices=["portrait_9_16", "landscape_16_9", "square_1_1", "talking_head", "tech_explainer"],
    )
    p_sc.add_argument("--title", help="Título del video")
    p_sc.add_argument("--duration", type=float, help="Duración en segundos")
    p_sc.add_argument("-f", "--force", action="store_true", help="Sobrescribir")

    # Subcomando: check
    p_chk = subparsers.add_parser("check", help="Auditar proyecto con HyperFrames linter")
    p_chk.add_argument("project", help="Ruta o nombre del proyecto")

    # Subcomando: render
    p_rnd = subparsers.add_parser("render", help="Renderizar proyecto a MP4")
    p_rnd.add_argument("project", help="Ruta o nombre del proyecto")
    p_rnd.add_argument("-o", "--output", help="Ruta del video MP4 de salida")

    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        sys.exit(0)

    if args.subcommand == "produce":
        produce_pipeline(
            input_media=args.input,
            project_name=args.project,
            template=args.template,
            title=args.title,
            whisper_model=args.model,
            language=args.language,
            noise_db=args.noise_db,
            min_silence=args.min_silence,
            auto_render=args.auto_render,
            force=args.force,
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
        h_code, g_code = generate_html_and_gsap(grps)
        if args.inject:
            inject_into_html(Path(args.inject), h_code, g_code)
    elif args.subcommand == "scaffold":
        create_project(args.name, args.template, args.title, args.duration, args.force)
    elif args.subcommand == "check":
        p_dir = (
            Path("projects") / args.project
            if not Path(args.project).exists()
            else Path(args.project)
        )
        run_command(["pnpm", "exec", "hyperframes", "check", str(p_dir)])
    elif args.subcommand == "render":
        p_dir = (
            Path("projects") / args.project
            if not Path(args.project).exists()
            else Path(args.project)
        )
        out = args.output or f"{p_dir}/video_{p_dir.name}.mp4"
        run_command(["pnpm", "exec", "hyperframes", "render", str(p_dir), "-o", str(out)])


if __name__ == "__main__":
    main()
