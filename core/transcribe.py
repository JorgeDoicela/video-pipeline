#!/usr/bin/env python3
"""
Script de transcripción local con marcas de tiempo a nivel de palabra.
Utiliza faster-whisper (CTranslate2) para ejecución eficiente en CPU/GPU.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core._runtime import ensure_local_venv, ensure_repo_root_on_path  # noqa: E402

ensure_repo_root_on_path()


def parse_replacements(raw_pairs: list[str] | None) -> dict[str, str]:
    """Convierte pares 'incorrecto=Correcto' en un diccionario de correcciones fonéticas."""
    if not raw_pairs:
        return {}
    mapping: dict[str, str] = {}
    for pair in raw_pairs:
        if "=" not in pair:
            raise ValueError(
                f"Formato inválido en --replace '{pair}'. Use 'termino_erroneo=TerminoCorrecto'."
            )
        src, dst = pair.split("=", 1)
        src_clean = src.strip()
        dst_clean = dst.strip()
        if src_clean and dst_clean:
            mapping[src_clean] = dst_clean
    return mapping


_EDGE_PUNCT_RE = re.compile(r"^([^\w]*)(.*?)([^\w]*)$", flags=re.UNICODE)


def _split_edge_punct(token: str) -> tuple[str, str, str]:
    match = _EDGE_PUNCT_RE.match(token)
    if not match:
        return "", token, ""
    return match.group(1), match.group(2), match.group(3)


def _replace_word_sequence(
    words: list[dict[str, Any]], src_tokens: list[str], dst_tokens: list[str]
) -> list[dict[str, Any]]:
    """Reemplaza secuencias contiguas de 1 o más palabras preservando puntuación y timestamps."""
    n_src = len(src_tokens)
    n_dst = len(dst_tokens)
    if n_src == 0 or n_dst == 0 or len(words) < n_src:
        return words

    src_lower = [t.lower() for t in src_tokens]
    result: list[dict[str, Any]] = []
    idx = 0
    total = len(words)

    while idx < total:
        if idx + n_src <= total:
            window = words[idx : idx + n_src]
            split_win = [_split_edge_punct(str(w.get("word", ""))) for w in window]
            if [core.lower() for _, core, _ in split_win] == src_lower:
                lead_punct = split_win[0][0]
                trail_punct = split_win[-1][2]
                t_start = float(window[0].get("start", 0.0))
                t_end = float(window[-1].get("end", t_start))
                avg_prob = round(sum(float(w.get("probability", 1.0)) for w in window) / n_src, 4)

                if n_dst == n_src:
                    for offset, dst_tok in enumerate(dst_tokens):
                        prefix = lead_punct if offset == 0 else ""
                        suffix = trail_punct if offset == n_dst - 1 else ""
                        result.append(
                            {
                                **window[offset],
                                "word": f"{prefix}{dst_tok}{suffix}",
                            }
                        )
                else:
                    span = max(0.0, t_end - t_start)
                    step = span / n_dst
                    for offset, dst_tok in enumerate(dst_tokens):
                        prefix = lead_punct if offset == 0 else ""
                        suffix = trail_punct if offset == n_dst - 1 else ""
                        w_start = round(t_start + offset * step, 3)
                        w_end = round(
                            t_end if offset == n_dst - 1 else t_start + (offset + 1) * step, 3
                        )
                        result.append(
                            {
                                "word": f"{prefix}{dst_tok}{suffix}",
                                "start": w_start,
                                "end": w_end,
                                "probability": avg_prob,
                            }
                        )
                idx += n_src
                continue

        result.append(words[idx])
        idx += 1

    return result


def apply_vocabulary_replacements(
    data: dict[str, Any], replacements: dict[str, str] | None
) -> dict[str, Any]:
    """
    Reemplaza de forma determinista términos o frases cortas mal transcritas
    (ej. 'lidis' -> 'Redis', 'lo sabrás' -> 'los abras') tanto en el texto de
    cada segmento como en los tokens individuales, preservando puntuación y timestamps.
    """
    if not replacements:
        return data

    ordered_pairs = sorted(
        (
            (src.strip(), dst.strip())
            for src, dst in replacements.items()
            if src.strip() and dst.strip()
        ),
        key=lambda item: len(item[0].split()),
        reverse=True,
    )
    patterns: list[tuple[re.Pattern[str], str]] = [
        (re.compile(rf"(?<!\w){re.escape(src)}(?!\w)", flags=re.IGNORECASE), dst)
        for src, dst in ordered_pairs
    ]
    token_rules: list[tuple[list[str], list[str]]] = [
        (src.split(), dst.split()) for src, dst in ordered_pairs
    ]

    for seg in data.get("segments", []):
        seg_text = str(seg.get("text", ""))
        for pat, dst in patterns:
            seg_text = pat.sub(lambda _, d=dst: d, seg_text)
        seg["text"] = seg_text

        seg_words = seg.get("words")
        if isinstance(seg_words, list) and seg_words:
            updated_words = list(seg_words)
            for src_tokens, dst_tokens in token_rules:
                updated_words = _replace_word_sequence(updated_words, src_tokens, dst_tokens)
            # Reemplazo de respaldo para sub-tokens con guiones/apóstrofes
            for w in updated_words:
                w_text = str(w.get("word", ""))
                for pat, dst in patterns:
                    if " " not in dst:
                        w_text = pat.sub(lambda _, d=dst: d, w_text)
                w["word"] = w_text
            seg["words"] = updated_words

    return data


def transcribe(
    audio_path: str,
    output_path: str,
    model_size: str = "base",
    language: str = "es",
    device: str = "cpu",
    initial_prompt: str | None = None,
    hotwords: str | None = None,
    replacements: dict[str, str] | None = None,
):
    input_file = Path(audio_path)
    if not input_file.exists():
        print(f"Error: El archivo de entrada '{audio_path}' no existe.", file=sys.stderr)
        sys.exit(1)

    print(
        f"[Whisper] Cargando modelo '{model_size}' en dispositivo '{device}' (compute_type=int8)..."
    )
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device=device, compute_type="int8")

    print(f"[Whisper] Transcribiendo archivo: {input_file.name} (idioma={language})...")
    transcribe_kwargs: dict[str, Any] = {
        "language": language if language != "auto" else None,
        "word_timestamps": True,
        "vad_filter": True,
    }
    if initial_prompt:
        transcribe_kwargs["initial_prompt"] = initial_prompt
    if hotwords:
        transcribe_kwargs["hotwords"] = hotwords

    segments, info = model.transcribe(str(input_file), **transcribe_kwargs)

    data = {
        "file": str(input_file.resolve()),
        "language": info.language,
        "language_probability": round(info.language_probability, 4),
        "duration": round(info.duration, 3),
        "segments": [],
    }

    word_count = 0
    for segment in segments:
        seg_data = {
            "id": segment.id,
            "start": round(segment.start, 3),
            "end": round(segment.end, 3),
            "text": segment.text.strip(),
            "words": [],
        }
        if segment.words:
            for word in segment.words:
                seg_data["words"].append(
                    {
                        "word": word.word.strip(),
                        "start": round(word.start, 3),
                        "end": round(word.end, 3),
                        "probability": round(word.probability, 4),
                    }
                )
                word_count += 1
        data["segments"].append(seg_data)

    if replacements:
        apply_vocabulary_replacements(data, replacements)

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[Whisper] Éxito: {len(data['segments'])} segmentos, {word_count} palabras transcritas.")
    print(f"[Whisper] Guardado en: {out_file.resolve()}")


def register_transcribe_arguments(parser: argparse.ArgumentParser) -> None:
    """Registra los argumentos CLI de transcripción en el parser indicado."""
    parser.add_argument("-i", "--input", required=True, help="Ruta al archivo de audio o video")
    parser.add_argument("-o", "--output", required=True, help="Ruta al archivo JSON de salida")
    parser.add_argument(
        "-m",
        "--model",
        default="base",
        choices=["tiny", "base", "small", "medium", "large-v3"],
        help="Tamaño del modelo Whisper",
    )
    parser.add_argument("-l", "--language", default="es", help="Código de idioma (es, en, auto)")
    parser.add_argument(
        "-d", "--device", default="cpu", choices=["cpu", "cuda"], help="Dispositivo de cómputo"
    )
    parser.add_argument(
        "--prompt",
        help="Prompt inicial con vocabulario técnico para guiar a Whisper (ej. 'Redis, Kubernetes, PostgreSQL')",
    )
    parser.add_argument(
        "--hotwords",
        help="Lista de palabras clave técnicas prioritarias separadas por coma",
    )
    parser.add_argument(
        "--replace",
        dest="replacements",
        action="append",
        metavar="ERRONEO=CORRECTO",
        help="Reemplazo determinista post-transcripción (ej. --replace lidis=Redis)",
    )


def main() -> None:
    ensure_local_venv()
    parser = argparse.ArgumentParser(description="Transcripción local con word-level timestamps")
    register_transcribe_arguments(parser)
    args = parser.parse_args()

    transcribe(
        args.input,
        args.output,
        args.model,
        args.language,
        args.device,
        initial_prompt=args.prompt,
        hotwords=args.hotwords,
        replacements=parse_replacements(args.replacements),
    )


if __name__ == "__main__":
    main()
