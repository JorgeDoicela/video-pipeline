#!/usr/bin/env python3
"""
Motor de sincronización y generación de subtítulos cinéticos.
Convierte transcripciones de Whisper (con marcas temporales palabra por palabra)
en elementos HTML y código de animación GSAP determinista, además de exportar a SRT y VTT.
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from core.styles import (
        CAPTION_STYLES,
        DEFAULT_CAPTION_STYLE,
        generate_caption_css,
        get_caption_style,
    )
except ModuleNotFoundError:
    from styles import (  # type: ignore
        CAPTION_STYLES,
        DEFAULT_CAPTION_STYLE,
        generate_caption_css,
        get_caption_style,
    )


def load_transcript(json_path: Path) -> dict:
    if not json_path.exists():
        print(f"Error: El archivo de transcripción '{json_path}' no existe.", file=sys.stderr)
        sys.exit(1)
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


def format_timestamp_srt(seconds: float) -> str:
    """Convierte segundos a formato SRT (HH:MM:SS,mmm)."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def format_timestamp_vtt(seconds: float) -> str:
    """Convierte segundos a formato WebVTT (HH:MM:SS.mmm)."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    return f"{hrs:02d}:{mins:02d}:{secs:02d}.{millis:03d}"


def extract_word_list(transcript_data: dict) -> list[dict]:
    """Extrae una lista lineal y limpia de todas las palabras con sus marcas de tiempo."""
    words = []
    for segment in transcript_data.get("segments", []):
        for w in segment.get("words", []):
            word_text = w.get("word", "").strip()
            if word_text:
                words.append(
                    {
                        "word": word_text,
                        "start": float(w.get("start", 0.0)),
                        "end": float(w.get("end", 0.0)),
                    }
                )
    return words


def group_words(
    words: list[dict], words_per_group: int = 4, pause_threshold: float = 0.4
) -> list[list[dict]]:
    """
    Agrupa palabras en bloques legibles de 2 a 5 palabras,
    cortando de inmediato si se detecta una pausa superior a pause_threshold.
    """
    if not words:
        return []

    groups = []
    current_group = []

    for w in words:
        if not current_group:
            current_group.append(w)
            continue

        prev_w = current_group[-1]
        pause = w["start"] - prev_w["end"]

        # Cortar si excede el tamaño máximo o si hubo una pausa natural notable
        if len(current_group) >= words_per_group or pause >= pause_threshold:
            groups.append(current_group)
            current_group = [w]
        else:
            current_group.append(w)

    if current_group:
        groups.append(current_group)

    return groups


def export_srt(groups: list[list[dict]], output_path: Path):
    """Genera archivo de subtítulos estándar SRT."""
    lines = []
    for idx, group in enumerate(groups, start=1):
        start_ts = format_timestamp_srt(group[0]["start"])
        end_ts = format_timestamp_srt(group[-1]["end"])
        text = " ".join(w["word"] for w in group)
        lines.append(f"{idx}\n{start_ts} --> {end_ts}\n{text}\n")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[Captions] Subtítulos SRT exportados a: {output_path.resolve()}")


def export_vtt(groups: list[list[dict]], output_path: Path):
    """Genera archivo de subtítulos estándar WebVTT."""
    lines = ["WEBVTT\n"]
    for idx, group in enumerate(groups, start=1):
        start_ts = format_timestamp_vtt(group[0]["start"])
        end_ts = format_timestamp_vtt(group[-1]["end"])
        text = " ".join(w["word"] for w in group)
        lines.append(f"{idx}\n{start_ts} --> {end_ts}\n{text}\n")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[Captions] Subtítulos WebVTT exportados a: {output_path.resolve()}")


def generate_html_and_gsap(
    groups: list[list[dict]],
    caption_style: str = DEFAULT_CAPTION_STYLE,
) -> tuple[str, str]:
    """
    Genera el bloque HTML de subtítulos agrupados y el código JavaScript para la línea de tiempo GSAP.
    Soporta variantes de estilo de subtítulos cinéticos registradas en core.styles.
    """
    style_cfg = get_caption_style(caption_style)

    html_parts = [
        "<!-- @captions:start -->",
        '<div id="captions-container" class="caption-bar">',
    ]
    gsap_lines = [
        "// @captions-gsap:start",
        "// --- Subtítulos Cinéticos Sincronizados ---",
    ]

    for g_idx, group in enumerate(groups):
        g_start = group[0]["start"]
        g_end = group[-1]["end"]
        group_id = f"cg_{g_idx}"

        # Grupo contenedor en HTML oculto por defecto
        html_parts.append(
            f'  <div id="{group_id}" class="caption-phrase" style="opacity: 0; display: none;">'
        )

        for w_idx, w in enumerate(group):
            word_id = f"cw_{g_idx}_{w_idx}"
            word_text = w["word"].replace("<", "&lt;").replace(">", "&gt;")
            html_parts.append(f'    <span id="{word_id}" class="word">{word_text}</span>')

        html_parts.append("  </div>")

        # GSAP Timeline: Aparece el contenedor de frase
        gsap_lines.append(
            f'tl.set("#{group_id}", {{ display: "inline-block", opacity: 1 }}, {g_start:.3f});'
        )

        # GSAP Timeline: Se iluminan las palabras individualmente
        for w_idx, w in enumerate(group):
            word_id = f"cw_{g_idx}_{w_idx}"
            w_start = w["start"]
            w_end = w["end"]
            gsap_lines.append(
                f'tl.to("#{word_id}", {{ className: "word active", duration: 0.04 }}, {w_start:.3f});'
            )
            if style_cfg.use_scale_pop:
                pop_dur = min(0.12, max(0.04, (w_end - w_start) * 0.5))
                gsap_lines.append(
                    f'tl.fromTo("#{word_id}", {{ scale: 1.14 }}, {{ scale: 1.0, duration: {pop_dur:.3f}, ease: "back.out(2)" }}, {w_start:.3f});'
                )

        # GSAP Timeline: Desaparece la frase al terminar el bloque
        gsap_lines.append(
            f'tl.set("#{group_id}", {{ opacity: 0, display: "none" }}, {g_end + 0.15:.3f});'
        )

    html_parts.append("</div>")
    html_parts.append("<!-- @captions:end -->")
    gsap_lines.append("// @captions-gsap:end")

    return "\n".join(html_parts), "\n".join(gsap_lines)


def inject_into_html(
    html_path: Path,
    html_snippet: str,
    gsap_snippet: str,
    caption_style: str | None = None,
):
    """
    Inyecta de forma idempotente el contenedor HTML y las llamadas GSAP dentro del index.html.
    """
    if not html_path.exists():
        print(f"Error: No se encontró el archivo HTML destino '{html_path}'.", file=sys.stderr)
        sys.exit(1)

    content = html_path.read_text(encoding="utf-8")

    # 0. Si se especificó un estilo de subtítulos, inyectar sus reglas CSS deterministas
    if caption_style is not None:
        style_cfg = get_caption_style(caption_style)
        cap_css = generate_caption_css(style_cfg)
        if "/* @caption-style:start */" in content and "/* @caption-style:end */" in content:
            content = re.sub(
                r"\s*/\* @caption-style:start \*/.*?/\* @caption-style:end \*/",
                "\n" + cap_css,
                content,
                count=1,
                flags=re.DOTALL,
            )
        elif "</style>" in content:
            content = content.replace("</style>", f"{cap_css}\n    </style>", 1)

    # 1. Reemplazar contenedor de subtítulos existente de manera determinista
    if "<!-- @captions:start -->" in content and "<!-- @captions:end -->" in content:
        content = re.sub(
            r"<!-- @captions:start -->.*?<!-- @captions:end -->",
            html_snippet,
            content,
            flags=re.DOTALL,
            count=1,
        )
    elif '<div id="caption-zone">' in content:
        content = re.sub(
            r'(<div id="caption-zone">\s*).*?(\s*</div>)',
            rf"\g<1>{html_snippet}\g<2>",
            content,
            flags=re.DOTALL,
            count=1,
        )
    elif '<div class="caption-bar">' in content or '<div id="captions-container"' in content:
        content = re.sub(
            r'(<!-- Subtítulos Cinéticos -->\s*)?<div (?:id="captions-container"|class="caption-bar")[^>]*>.*?</div>',
            f"<!-- Subtítulos Cinéticos -->\n      {html_snippet}",
            content,
            flags=re.DOTALL,
            count=1,
        )
    else:
        # Insertar justo antes del cierre del contenedor #root
        content = re.sub(
            r"(</div>\s*<script>)",
            rf"      {html_snippet}\n    \g<1>",
            content,
            count=1,
        )

    # 2. Inyectar o reemplazar el bloque de timeline GSAP
    if "// @captions-gsap:start" in content and "// @captions-gsap:end" in content:
        content = re.sub(
            r"// @captions-gsap:start.*?// @captions-gsap:end",
            gsap_snippet,
            content,
            flags=re.DOTALL,
            count=1,
        )
    elif "window.__timelines" in content:
        # Limpiar líneas de demostración estáticas (#w1..#w6) si existían en la plantilla
        content = re.sub(
            r'\s*tl\.to\("#w[0-9]+",\s*\{[^}]*\},\s*[0-9.]+\);',
            "",
            content,
        )
        content = re.sub(
            r"(window\.__timelines\s*=\s*window\.__timelines\s*\|\|\s*\{\};)",
            rf"{gsap_snippet}\n\n      \g<1>",
            content,
            count=1,
        )

    html_path.write_text(content, encoding="utf-8")
    print(f"[Captions] Subtítulos inyectados exitosamente en: {html_path.resolve()}")


def main():
    parser = argparse.ArgumentParser(
        description="Generador y sincronizador de subtítulos cinéticos desde transcript.json"
    )
    parser.add_argument(
        "-i", "--input", required=True, help="Ruta al archivo transcript.json de Whisper"
    )
    parser.add_argument("--inject", help="Ruta al index.html donde inyectar el código HTML y GSAP")
    parser.add_argument("--export-srt", help="Ruta donde exportar archivo de subtítulos .srt")
    parser.add_argument("--export-vtt", help="Ruta donde exportar archivo de subtítulos .vtt")
    parser.add_argument(
        "--caption-style",
        default=DEFAULT_CAPTION_STYLE,
        choices=list(CAPTION_STYLES.keys()),
        help=f"Estilo visual y de animación para subtítulos (defecto: {DEFAULT_CAPTION_STYLE})",
    )
    parser.add_argument(
        "--words-per-group",
        type=int,
        default=4,
        help="Número máximo de palabras por frase visible (defecto: 4)",
    )
    parser.add_argument(
        "--pause-threshold",
        type=float,
        default=0.4,
        help="Umbral de pausa en segundos para forzar cambio de frase (defecto: 0.4s)",
    )

    args = parser.parse_args()

    transcript_path = Path(args.input)
    data = load_transcript(transcript_path)

    words = extract_word_list(data)
    if not words:
        print("[Captions] No se encontraron palabras en la transcripción.", file=sys.stderr)
        sys.exit(0)

    groups = group_words(
        words, words_per_group=args.words_per_group, pause_threshold=args.pause_threshold
    )
    print(f"[Captions] Procesadas {len(words)} palabras en {len(groups)} grupos de subtítulos.")

    if args.export_srt:
        export_srt(groups, Path(args.export_srt))

    if args.export_vtt:
        export_vtt(groups, Path(args.export_vtt))

    html_code, gsap_code = generate_html_and_gsap(groups, caption_style=args.caption_style)

    if args.inject:
        inject_into_html(
            Path(args.inject),
            html_code,
            gsap_code,
            caption_style=args.caption_style,
        )
    elif not args.export_srt and not args.export_vtt:
        print("\n--- Código HTML Generado ---")
        print(html_code)
        print("\n--- Código GSAP Generado ---")
        print(gsap_code)


if __name__ == "__main__":
    main()
