#!/usr/bin/env python3
"""
Script de transcripción local con marcas de tiempo a nivel de palabra.
Utiliza faster-whisper (CTranslate2) para ejecución eficiente en CPU/GPU.
"""

import argparse
import json
import sys
from pathlib import Path


def transcribe(audio_path: str, output_path: str, model_size: str = "base", language: str = "es", device: str = "cpu"):
    input_file = Path(audio_path)
    if not input_file.exists():
        print(f"Error: El archivo de entrada '{audio_path}' no existe.", file=sys.stderr)
        sys.exit(1)

    print(f"[Whisper] Cargando modelo '{model_size}' en dispositivo '{device}' (compute_type=int8)...")
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device=device, compute_type="int8")

    print(f"[Whisper] Transcribiendo archivo: {input_file.name} (idioma={language})...")
    segments, info = model.transcribe(
        str(input_file),
        language=language if language != "auto" else None,
        word_timestamps=True,
        vad_filter=True, # Filtro de detección de actividad vocal
    )

    data = {
        "file": str(input_file.resolve()),
        "language": info.language,
        "language_probability": round(info.language_probability, 4),
        "duration": round(info.duration, 3),
        "segments": []
    }

    word_count = 0
    for segment in segments:
        seg_data = {
            "id": segment.id,
            "start": round(segment.start, 3),
            "end": round(segment.end, 3),
            "text": segment.text.strip(),
            "words": []
        }
        if segment.words:
            for word in segment.words:
                seg_data["words"].append({
                    "word": word.word.strip(),
                    "start": round(word.start, 3),
                    "end": round(word.end, 3),
                    "probability": round(word.probability, 4)
                })
                word_count += 1
        data["segments"].append(seg_data)

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
    parser.add_argument("-m", "--model", default="base", choices=["tiny", "base", "small", "medium", "large-v3"], help="Tamaño del modelo Whisper")
    parser.add_argument("-l", "--language", default="es", help="Código de idioma (es, en, auto)")
    parser.add_argument("-d", "--device", default="cpu", choices=["cpu", "cuda"], help="Dispositivo de cómputo")
    args = parser.parse_args()

    transcribe(args.input, args.output, args.model, args.language, args.device)


if __name__ == "__main__":
    main()
