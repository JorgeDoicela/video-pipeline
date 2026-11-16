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

_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from core._runtime import ensure_local_venv  # noqa: E402

ensure_local_venv()


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


def apply_vocabulary_replacements(
    data: dict[str, Any], replacements: dict[str, str] | None
) -> dict[str, Any]:
    """
    Reemplaza de forma determinista términos mal transcritos (ej. 'lidis' -> 'Redis')
    tanto en el texto de cada segmento como en los tokens individuales preservando puntuación.
    """
    if not replacements:
        return data

    patterns: list[tuple[re.Pattern[str], str]] = [
        (re.compile(rf"(?<!\w){re.escape(src)}(?!\w)", flags=re.IGNORECASE), dst)
        for src, dst in replacements.items()
        if src
    ]

    for seg in data.get("segments", []):
        seg_text = str(seg.get("text", ""))
        for pat, dst in patterns:
            seg_text = pat.sub(lambda _, d=dst: d, seg_text)
        seg["text"] = seg_text

        for w in seg.get("words", []):
            w_text = str(w.get("word", ""))
            for pat, dst in patterns:
                w_text = pat.sub(lambda _, d=dst: d, w_text)
            w["word"] = w_text

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


def main():
    parser = argparse.ArgumentParser(description="Transcripción local con word-level timestamps")
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
