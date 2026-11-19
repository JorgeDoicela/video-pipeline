#!/usr/bin/env python3
"""
Mezclador determinista de pista de voz y efectos de sonido (SFX) mediante FFmpeg.
Posiciona cada efecto de sonido en el milisegundo exacto de su evento GSAP con limitación de picos.
"""

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from core.generate_sfx import ensure_sfx_assets, resolve_music_source


@dataclass(frozen=True)
class SfxEvent:
    """Representa un disparo de efecto de sonido en un instante exacto del timeline."""

    sfx: str
    time_sec: float
    volume: float = 0.35


def resolve_ffmpeg() -> str:
    """Resuelve el binario ffmpeg disponible en el sistema."""
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        raise FileNotFoundError(
            "No se encontró 'ffmpeg' en PATH. Instala FFmpeg para mezclar pistas de audio y SFX."
        )
    return ffmpeg_bin


def build_sfx_mix_command(
    voice_path: Path | None,
    events: list[tuple[Path, float, float]],
    total_duration: float,
    output_wav: Path,
    ffmpeg_bin: str = "ffmpeg",
    music_path: Path | None = None,
    music_volume: float = 0.14,
) -> list[str]:
    """
    Construye el comando FFmpeg con filter_complex para mezclar voz (o silencio base),
    cama musical/ambiental opcional con ducking dinámico (sidechaincompress) y
    múltiples eventos SFX posicionados con adelay y protección anti-clipping (alimiter).
    """
    if total_duration <= 0:
        raise ValueError(f"La duración total debe ser positiva (recibido: {total_duration}).")

    cmd: list[str] = [ffmpeg_bin, "-y"]
    filter_parts: list[str] = []

    if voice_path is not None:
        cmd.extend(["-i", str(voice_path)])
        if music_path is not None:
            filter_parts.append(
                "[0:a]aresample=48000,aformat=channel_layouts=stereo,"
                f"apad=whole_dur={total_duration:.3f},atrim=0:{total_duration:.3f},"
                "volume=1.0,asplit=2[base][sc]"
            )
        else:
            filter_parts.append(
                "[0:a]aresample=48000,aformat=channel_layouts=stereo,"
                f"apad=whole_dur={total_duration:.3f},atrim=0:{total_duration:.3f},"
                "volume=1.0[base]"
            )
    else:
        cmd.extend(
            ["-f", "lavfi", "-t", f"{total_duration:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
        )
        filter_parts.append("[0:a]acopy[base]")

    mix_labels = ["[base]"]
    next_input_idx = 1

    if music_path is not None:
        cmd.extend(["-stream_loop", "-1", "-i", str(music_path)])
        m_idx = next_input_idx
        next_input_idx += 1
        fade_out_st = max(0.0, total_duration - 0.5)
        if voice_path is not None:
            filter_parts.append(
                f"[{m_idx}:a]aresample=48000,aformat=channel_layouts=stereo,"
                f"atrim=0:{total_duration:.3f},afade=t=in:st=0:d=0.35,"
                f"afade=t=out:st={fade_out_st:.3f}:d=0.5,volume={music_volume:.2f}[music_raw]"
            )
            filter_parts.append(
                "[music_raw][sc]sidechaincompress="
                "threshold=0.025:ratio=5:attack=20:release=280[music_bed]"
            )
        else:
            filter_parts.append(
                f"[{m_idx}:a]aresample=48000,aformat=channel_layouts=stereo,"
                f"atrim=0:{total_duration:.3f},afade=t=in:st=0:d=0.35,"
                f"afade=t=out:st={fade_out_st:.3f}:d=0.5,volume={music_volume:.2f}[music_bed]"
            )
        mix_labels.append("[music_bed]")

    valid_events = [
        (wav_path, max(0.0, t_sec), vol)
        for wav_path, t_sec, vol in events
        if 0.0 <= t_sec < total_duration
    ]

    for offset, (wav_path, t_sec, vol) in enumerate(valid_events):
        in_idx = next_input_idx + offset
        cmd.extend(["-i", str(wav_path)])
        delay_ms = int(round(t_sec * 1000))
        label = f"sfx_{offset + 1}"
        filter_parts.append(
            f"[{in_idx}:a]aresample=48000,aformat=channel_layouts=stereo,"
            f"volume={vol:.2f},adelay={delay_ms}|{delay_ms}[{label}]"
        )
        mix_labels.append(f"[{label}]")

    if len(mix_labels) == 1:
        filter_parts.append("[base]alimiter=limit=0.95[out]")
    else:
        inputs_str = "".join(mix_labels)
        filter_parts.append(
            f"{inputs_str}amix=inputs={len(mix_labels)}:duration=first:"
            "dropout_transition=0:normalize=0,alimiter=limit=0.95[out]"
        )

    cmd.extend(
        [
            "-filter_complex",
            ";".join(filter_parts),
            "-map",
            "[out]",
            "-t",
            f"{total_duration:.3f}",
            "-c:a",
            "pcm_s16le",
            "-ar",
            "48000",
            "-ac",
            "2",
            str(output_wav),
        ]
    )
    return cmd


def mix_storyboard_audio(
    project_dir: Path,
    events: list[SfxEvent],
    total_duration: float,
    voice_path: Path | None = None,
    output_name: str = "audio_mix.wav",
    music_path: Path | str | None = None,
    music_volume: float = 0.14,
    ambient_bed: bool = False,
) -> Path:
    """Genera los SFX faltantes y mezcla la pista de audio final (voz + cama + SFX) en el proyecto."""
    sfx_map = ensure_sfx_assets()
    resolved_events: list[tuple[Path, float, float]] = []
    for ev in events:
        if ev.sfx not in sfx_map:
            print(
                f"[AudioMix] Advertencia: SFX '{ev.sfx}' no reconocido, omitido.", file=sys.stderr
            )
            continue
        resolved_events.append((sfx_map[ev.sfx], ev.time_sec, ev.volume))

    effective_music = resolve_music_source(music_path)
    if effective_music is None and ambient_bed and "drone" in sfx_map:
        effective_music = sfx_map["drone"]

    output_wav = project_dir / output_name
    ffmpeg_bin = resolve_ffmpeg()
    cmd = build_sfx_mix_command(
        voice_path=voice_path,
        events=resolved_events,
        total_duration=total_duration,
        output_wav=output_wav,
        ffmpeg_bin=ffmpeg_bin,
        music_path=effective_music,
        music_volume=music_volume,
    )
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    bed_info = f" + cama ({effective_music.name})" if effective_music else ""
    print(f"[AudioMix] Mezcla generada ({len(resolved_events)} SFX{bed_info}) -> {output_wav.name}")
    return output_wav
