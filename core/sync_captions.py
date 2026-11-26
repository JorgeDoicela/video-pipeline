#!/usr/bin/env python3
"""
Motor de sincronización y generación de subtítulos cinéticos.
Convierte transcripciones de Whisper (con marcas temporales palabra por palabra)
en elementos HTML y código de animación GSAP determinista, además de exportar a SRT y VTT.
"""

import argparse
import html
import json
import re
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core._runtime import (  # noqa: E402
    ensure_local_venv,
    ensure_repo_root_on_path,
    normalize_token,
)

ensure_repo_root_on_path()

from core.styles import (  # noqa: E402
    CAPTION_STYLES,
    DEFAULT_CAPTION_STYLE,
    generate_caption_css,
    get_caption_style,
    upsert_marked_css_block,
)


def load_transcript(json_path: Path) -> dict:
    if not json_path.exists():
        print(f"Error: El archivo de transcripción '{json_path}' no existe.", file=sys.stderr)
        sys.exit(1)
    with open(json_path, encoding="utf-8-sig") as f:
        return json.load(f)


def _split_timestamp(seconds: float) -> tuple[int, int, int, int]:
    """Descompone segundos en (horas, minutos, segundos, milisegundos) sin overflow a 1000ms."""
    total_ms = max(0, round(seconds * 1000))
    total_secs, millis = divmod(total_ms, 1000)
    mins, secs = divmod(total_secs, 60)
    hrs, mins = divmod(mins, 60)
    return hrs, mins, secs, millis


def format_timestamp_srt(seconds: float) -> str:
    """Convierte segundos a formato SRT (HH:MM:SS,mmm)."""
    hrs, mins, secs, millis = _split_timestamp(seconds)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def format_timestamp_vtt(seconds: float) -> str:
    """Convierte segundos a formato WebVTT (HH:MM:SS.mmm)."""
    hrs, mins, secs, millis = _split_timestamp(seconds)
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


_STRONG_PUNCT_END = (".", "?", "!", ":", ";")


def group_words(
    words: list[dict],
    words_per_group: int = 6,
    pause_threshold: float = 0.4,
    split_on_punctuation: bool = True,
    max_chars: int = 0,
) -> list[list[dict]]:
    """
    Agrupa palabras en bloques legibles de 1 o 2 líneas balanceadas (por defecto hasta
    words_per_group palabras), cortando ante pausas superiores a pause_threshold y respetando
    cierres naturales de frase (puntuación fuerte o coma tras >= 2 palabras).
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
        prev_text = str(prev_w.get("word", "")).strip()
        next_text = str(w.get("word", "")).strip()
        pause = w["start"] - prev_w["end"]

        current_chars = sum(len(str(item.get("word", "")).strip()) for item in current_group) + (
            len(current_group) - 1
        )
        exceeds_chars = max_chars > 0 and (current_chars + 1 + len(next_text)) > max_chars

        ends_sentence = split_on_punctuation and prev_text.endswith(_STRONG_PUNCT_END)
        ends_clause = split_on_punctuation and prev_text.endswith(",") and len(current_group) >= 2

        # Cortar si excede tamaño máximo, ancho de línea, pausa notable o cierre natural de cláusula/frase
        if (
            len(current_group) >= words_per_group
            or exceeds_chars
            or pause >= pause_threshold
            or ends_sentence
            or ends_clause
        ):
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
    emphasis_words: list[str] | set[str] | None = None,
) -> tuple[str, str]:
    """
    Genera el bloque HTML de subtítulos agrupados y el código JavaScript para la línea de tiempo GSAP.
    Soporta variantes de estilo de subtítulos cinéticos registradas en core.styles y énfasis
    tipográfico limpio (sin cajas ni pastillas) sobre palabras clave.
    """
    get_caption_style(caption_style)
    emphasis_set: set[str] = set()
    if emphasis_words:
        for entry in emphasis_words:
            for tok in str(entry).split():
                norm = normalize_token(tok)
                if norm:
                    emphasis_set.add(norm)

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

        word_classes: list[str] = []
        for w_idx, w in enumerate(group):
            word_id = f"cw_{g_idx}_{w_idx}"
            word_text = html.escape(w["word"], quote=False)
            is_emph = bool(emphasis_set) and normalize_token(w["word"]) in emphasis_set
            base_cls = "word word-emphasis" if is_emph else "word"
            word_classes.append(base_cls)
            html_parts.append(f'    <span id="{word_id}" class="{base_cls}">{word_text}</span>')

        html_parts.append("  </div>")

        # GSAP Timeline: Aparece el contenedor de frase
        gsap_lines.append(
            f'tl.set("#{group_id}", {{ display: "inline-block", opacity: 1 }}, {g_start:.3f});'
        )

        # GSAP Timeline: Se iluminan las palabras individualmente
        for w_idx, w in enumerate(group):
            word_id = f"cw_{g_idx}_{w_idx}"
            w_start = w["start"]
            active_cls = f"{word_classes[w_idx]} active"
            gsap_lines.append(
                f'tl.to("#{word_id}", {{ className: "{active_cls}", duration: 0.04 }}, {w_start:.3f});'
            )

        # GSAP Timeline: Desaparece la frase exactamente antes o al iniciar el siguiente bloque
        # para impedir que dos grupos coexistan en pantalla y provoquen saltos de línea dobles.
        next_start = groups[g_idx + 1][0]["start"] if g_idx + 1 < len(groups) else None
        hide_time = min(g_end + 0.15, next_start) if next_start is not None else (g_end + 0.15)
        hide_time = max(g_start + 0.02, hide_time)
        gsap_lines.append(
            f'tl.set("#{group_id}", {{ opacity: 0, display: "none" }}, {hide_time:.3f});'
        )

    html_parts.append("</div>")
    html_parts.append("<!-- @captions:end -->")
    gsap_lines.append("// @captions-gsap:end")

    return "\n".join(html_parts), "\n".join(gsap_lines)


def _replace_balanced_div(
    content: str, open_tag_pattern: str, replacement: str
) -> tuple[str, bool]:
    """Reemplaza un bloque <div>...</div> balanceando etiquetas <div> anidadas."""
    match = re.search(open_tag_pattern, content)
    if not match:
        return content, False

    start_idx = match.start()
    pos = match.end()
    depth = 1
    tag_iter = re.finditer(r"<div\b[^>]*>|</div>", content[pos:], flags=re.IGNORECASE)
    for tag_match in tag_iter:
        if tag_match.group(0).lower().startswith("</div"):
            depth -= 1
            if depth == 0:
                end_idx = pos + tag_match.end()
                return content[:start_idx] + replacement + content[end_idx:], True
        else:
            depth += 1

    return content, False


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
        content = upsert_marked_css_block(content, "caption-style", cap_css)

    # 1. Reemplazar contenedor de subtítulos existente de manera determinista
    if "<!-- @captions:start -->" in content and "<!-- @captions:end -->" in content:
        content = re.sub(
            r"<!-- @captions:start -->.*?<!-- @captions:end -->",
            lambda _: html_snippet,
            content,
            flags=re.DOTALL,
            count=1,
        )
    elif '<div id="caption-zone">' in content:
        content, replaced = _replace_balanced_div(
            content,
            r'<div id="caption-zone"[^>]*>',
            f'<div id="caption-zone">\n      {html_snippet}\n    </div>',
        )
        if not replaced:
            content = re.sub(
                r'(<div id="caption-zone">\s*).*?(\s*</div>)',
                lambda m: f"{m.group(1)}{html_snippet}{m.group(2)}",
                content,
                flags=re.DOTALL,
                count=1,
            )
    elif '<div class="caption-bar">' in content or '<div id="captions-container"' in content:
        content, replaced = _replace_balanced_div(
            content,
            r'(?:<!-- Subtítulos Cinéticos -->\s*)?<div (?:id="captions-container"|class="caption-bar")[^>]*>',
            f"<!-- Subtítulos Cinéticos -->\n      {html_snippet}",
        )
        if not replaced:
            content = re.sub(
                r'(<!-- Subtítulos Cinéticos -->\s*)?<div (?:id="captions-container"|class="caption-bar")[^>]*>.*?</div>',
                lambda _: f"<!-- Subtítulos Cinéticos -->\n      {html_snippet}",
                content,
                flags=re.DOTALL,
                count=1,
            )
    else:
        # Insertar justo antes del cierre del contenedor #root
        content = re.sub(
            r"(</div>\s*<script>)",
            lambda m: f"      {html_snippet}\n    {m.group(1)}",
            content,
            count=1,
        )

    # 2. Inyectar o reemplazar el bloque de timeline GSAP
    if "// @captions-gsap:start" in content and "// @captions-gsap:end" in content:
        content = re.sub(
            r"// @captions-gsap:start.*?// @captions-gsap:end",
            lambda _: gsap_snippet,
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
            lambda m: f"{gsap_snippet}\n\n      {m.group(1)}",
            content,
            count=1,
        )

    # 3. Asegurar visibilidad del bloque de subtítulos si #root tenía data-has-captions="false"
    if 'data-has-captions="false"' in content and "<span" in html_snippet:
        content = content.replace('data-has-captions="false"', 'data-has-captions="true"', 1)

    html_path.write_text(content, encoding="utf-8")
    print(f"[Captions] Subtítulos inyectados exitosamente en: {html_path.resolve()}")


def clear_captions_in_html(html_path: Path) -> None:
    """
    Limpia subtítulos placeholder y tweens GSAP asociados cuando no se detecta habla,
    evitando texto residual de plantilla o referencias a nodos inexistentes.
    """
    if not html_path.exists():
        return

    content = html_path.read_text(encoding="utf-8")
    empty_html = (
        "<!-- @captions:start -->\n"
        '<div id="captions-container" class="caption-bar"></div>\n'
        "<!-- @captions:end -->"
    )
    empty_gsap = "// @captions-gsap:start\n// Sin habla detectada en la pista de audio\n// @captions-gsap:end"

    if "<!-- @captions:start -->" in content and "<!-- @captions:end -->" in content:
        content = re.sub(
            r"<!-- @captions:start -->.*?<!-- @captions:end -->",
            lambda _: empty_html,
            content,
            flags=re.DOTALL,
            count=1,
        )
    if "// @captions-gsap:start" in content and "// @captions-gsap:end" in content:
        content = re.sub(
            r"// @captions-gsap:start.*?// @captions-gsap:end",
            lambda _: empty_gsap,
            content,
            flags=re.DOTALL,
            count=1,
        )
    if 'data-has-captions="true"' in content:
        content = content.replace('data-has-captions="true"', 'data-has-captions="false"', 1)

    html_path.write_text(content, encoding="utf-8")


def register_captions_arguments(parser: argparse.ArgumentParser) -> None:
    """Registra los argumentos CLI de sincronización de subtítulos en el parser indicado."""
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
        default=6,
        help="Número máximo de palabras por frase visible de 1-2 líneas balanceadas (defecto: 6)",
    )
    parser.add_argument(
        "--pause-threshold",
        type=float,
        default=0.4,
        help="Umbral de pausa en segundos para forzar cambio de frase (defecto: 0.4s)",
    )


def main() -> None:
    ensure_local_venv()
    parser = argparse.ArgumentParser(
        description="Generador y sincronizador de subtítulos cinéticos desde transcript.json"
    )
    register_captions_arguments(parser)
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
