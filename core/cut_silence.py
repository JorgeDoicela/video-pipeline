#!/usr/bin/env python3
"""
Script de recorte algorítmico de silencios en video/audio usando FFmpeg.
Detecta pausas por debajo de un umbral de decibeles y duración mínima,
ensamblando un video continuo sin pausas muertas.
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


def detect_silence(input_file: str, noise_db: float = -30.0, min_duration: float = 0.5):
    """
    Ejecuta ffmpeg con el filtro silencedetect y extrae los intervalos de silencio.
    """
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-i",
        input_file,
        "-af",
        f"silencedetect=noise={noise_db}dB:d={min_duration}",
        "-f",
        "null",
        "-",
    ]

    print(f"[FFmpeg] Detectando silencios (ruido < {noise_db}dB, duracion > {min_duration}s)...")
    res = subprocess.run(cmd, check=True, stderr=subprocess.PIPE, text=True)

    silence_starts = []
    silence_ends = []

    for line in res.stderr.splitlines():
        start_match = re.search(r"silence_start:\s*([0-9.]+)", line)
        if start_match:
            silence_starts.append(float(start_match.group(1)))

        end_match = re.search(r"silence_end:\s*([0-9.]+)", line)
        if end_match:
            silence_ends.append(float(end_match.group(1)))

    # Emparejar silencios
    intervals = []
    for s, e in zip(silence_starts, silence_ends, strict=False):
        if e > s:
            intervals.append((s, e))

    return intervals


def get_media_duration(input_file: str) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        input_file,
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, text=True, check=True)
    return float(res.stdout.strip())


def compute_keep_intervals(total_duration: float, silence_intervals: list, padding: float = 0.08):
    """
    Invierte los intervalos de silencio para obtener los tramos de voz útil,
    dejando un pequeño margen (padding) para no cortar respiraciones o inicios de palabra.
    """
    keep = []
    current_pos = 0.0

    for s_start, s_end in silence_intervals:
        # Añadir padding para transiciones naturales
        cut_start = min(s_start + padding, s_end)
        cut_end = max(s_end - padding, cut_start)

        if cut_start > current_pos:
            keep.append((current_pos, cut_start))
        current_pos = cut_end

    if current_pos < total_duration:
        keep.append((current_pos, total_duration))

    # Filtrar intervalos demasiado cortos (< 0.1s)
    return [k for k in keep if (k[1] - k[0]) > 0.1]


def cut_and_concat(input_file: str, output_file: str, keep_intervals: list):
    """
    Construye el filtro complejo de FFmpeg para extraer y concatenar los segmentos.
    """
    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not keep_intervals:
        print(
            "[FFmpeg] No se detectaron pausas para recortar o el audio es continuo. Copiando archivo original.",
            file=sys.stderr,
        )
        shutil.copy2(input_file, out_path)
        return

    filter_parts = []
    concat_inputs = []

    for idx, (start, end) in enumerate(keep_intervals):
        v_tag = f"v{idx}"
        a_tag = f"a{idx}"
        filter_parts.append(
            f"[0:v]trim=start={start:.3f}:end={end:.3f},setpts=PTS-STARTPTS[{v_tag}];"
            f"[0:a]atrim=start={start:.3f}:end={end:.3f},asetpts=PTS-STARTPTS[{a_tag}];"
        )
        concat_inputs.append(f"[{v_tag}][{a_tag}]")

    concat_filter = (
        "".join(filter_parts)
        + "".join(concat_inputs)
        + f"concat=n={len(keep_intervals)}:v=1:a=1[outv][outa]"
    )

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-i",
        input_file,
        "-filter_complex",
        concat_filter,
        "-map",
        "[outv]",
        "-map",
        "[outa]",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "18",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(out_path),
    ]

    print(f"[FFmpeg] Ensamblando video sin silencios ({len(keep_intervals)} tomas útiles)...")
    subprocess.run(cmd, check=True)
    print(f"[FFmpeg] Video exportado con éxito a: {out_path.resolve()}")


def main():
    parser = argparse.ArgumentParser(
        description="Recorte de pausas y silencios en video/audio con FFmpeg"
    )
    parser.add_argument("-i", "--input", required=True, help="Ruta al video/audio crudo")
    parser.add_argument("-o", "--output", required=True, help="Ruta al video recortado de salida")
    parser.add_argument(
        "--noise-db", type=float, default=-30.0, help="Umbral de ruido en dB (por defecto -30.0)"
    )
    parser.add_argument(
        "--min-silence",
        type=float,
        default=0.45,
        help="Duración mínima de pausa a recortar en segundos (por defecto 0.45)",
    )
    args = parser.parse_args()

    total_dur = get_media_duration(args.input)
    silences = detect_silence(args.input, args.noise_db, args.min_silence)
    keep = compute_keep_intervals(total_dur, silences)

    saved_time = total_dur - sum(e - s for s, e in keep)
    print(
        f"[FFmpeg] Duración original: {total_dur:.2f}s | Tiempo recortado: {saved_time:.2f}s | Duración final: {total_dur - saved_time:.2f}s"
    )

    cut_and_concat(args.input, args.output, keep)


if __name__ == "__main__":
    main()
