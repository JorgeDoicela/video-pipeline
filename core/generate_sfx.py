#!/usr/bin/env python3
"""
Generador procedural de efectos de sonido (SFX) en formato WAV PCM 48kHz 16-bit.
Crea activos de audio limpios sin dependencias externas para transiciones de GSAP.
"""

import math
import random
import struct
import wave
from pathlib import Path

SAMPLE_RATE = 48000


def write_wav(path: Path, samples: list[float]):
    """Escribe una lista de floats en [-1.0, 1.0] a un archivo WAV PCM 16-bit estéreo."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as wav_file:
        wav_file.setnchannels(2)  # Stereo
        wav_file.setsampwidth(2)  # 16 bits
        wav_file.setframerate(SAMPLE_RATE)

        raw_bytes = bytearray()
        for s in samples:
            # Clamping
            clamped = max(-1.0, min(1.0, s))
            val = int(clamped * 32767.0)
            frame = struct.pack("<hh", val, val)
            raw_bytes.extend(frame)

        wav_file.writeframes(raw_bytes)
    print(f"[SFX] Generado: {path.name} ({len(samples) / SAMPLE_RATE:.2f}s)")


def generate_pop(path: Path):
    duration = 0.09
    num_samples = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        # Frecuencia cae de 700Hz a 160Hz
        freq = 160.0 + 540.0 * math.exp(-35.0 * t)
        phase = 2.0 * math.pi * freq * t
        env = math.exp(-28.0 * t)
        val = math.sin(phase) * env * 0.75
        samples.append(val)
    write_wav(path, samples)


def generate_click(path: Path):
    duration = 0.03
    num_samples = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        freq = 1400.0 * math.exp(-80.0 * t)
        phase = 2.0 * math.pi * freq * t
        env = math.exp(-120.0 * t)
        val = math.sin(phase) * env * 0.65
        samples.append(val)
    write_wav(path, samples)


def generate_beep(path: Path):
    duration = 0.08
    num_samples = int(SAMPLE_RATE * duration)
    samples = []
    freq = 920.0
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        # Envelope con ataque y caída suaves
        attack = min(1.0, t / 0.008)
        decay = min(1.0, (duration - t) / 0.015)
        env = attack * decay
        val = math.sin(2.0 * math.pi * freq * t) * env * 0.45
        samples.append(val)
    write_wav(path, samples)


def generate_chime(path: Path):
    duration = 0.85
    num_samples = int(SAMPLE_RATE * duration)
    samples = []
    # Acorde mayor brillante: C5, E5, G5, C6
    notes = [523.25, 659.25, 783.99, 1046.50]
    weights = [0.25, 0.22, 0.20, 0.18]

    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = math.exp(-4.5 * t)
        val = 0.0
        for f, w in zip(notes, weights, strict=False):
            val += math.sin(2.0 * math.pi * f * t) * w
        samples.append(val * env * 0.8)
    write_wav(path, samples)


def generate_whoosh(path: Path):
    duration = 0.38
    num_samples = int(SAMPLE_RATE * duration)
    samples = []
    random.seed(42)

    # Ruido filtrado y moldeado con envolvente Gaussiana
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        # Campana centrada en 0.18s
        env = math.exp(-pow((t - 0.18) / 0.085, 2))
        noise = random.uniform(-1.0, 1.0)
        # Tono armónico barriendo
        sweep_freq = 280.0 + 900.0 * math.sin(math.pi * (t / duration))
        sweep = math.sin(2.0 * math.pi * sweep_freq * t) * 0.4
        val = (noise * 0.5 + sweep) * env * 0.65
        samples.append(val)
    write_wav(path, samples)


def generate_sub_hit(path: Path) -> None:
    """Genera un impacto grave cinematográfico (85Hz -> 32Hz) para transiciones de alto impacto."""
    duration = 0.55
    num_samples = int(SAMPLE_RATE * duration)
    samples: list[float] = []
    phase = 0.0
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        freq = 32.0 + 53.0 * math.exp(-10.0 * t)
        phase += 2.0 * math.pi * freq / SAMPLE_RATE
        attack = min(1.0, t / 0.008)
        env = attack * math.exp(-5.5 * t)
        val = math.tanh(math.sin(phase) * 1.4) * env * 0.85
        samples.append(val)
    write_wav(path, samples)


def generate_glitch(path: Path) -> None:
    """Genera un pulso digital corto tipo interferencia/alerta para terminales."""
    duration = 0.16
    num_samples = int(SAMPLE_RATE * duration)
    samples: list[float] = []
    rng = random.Random(108)
    held = 0.0
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        if i % 140 == 0:
            held = rng.uniform(-1.0, 1.0)
        carrier = 1.0 if math.sin(2.0 * math.pi * 240.0 * t) >= 0 else -1.0
        env = math.exp(-14.0 * t) * (1.0 if (i // 1200) % 2 == 0 else 0.45)
        samples.append((held * 0.65 + carrier * 0.35) * env * 0.55)
    write_wav(path, samples)


SFX_GENERATORS = {
    "whoosh": generate_whoosh,
    "pop": generate_pop,
    "click": generate_click,
    "chime": generate_chime,
    "beep": generate_beep,
    "sub_hit": generate_sub_hit,
    "glitch": generate_glitch,
}


def ensure_sfx_assets(audio_dir: Path | None = None) -> dict[str, Path]:
    """Garantiza que todos los efectos WAV del catálogo existan en disco y devuelve su mapa de rutas."""
    target_dir = audio_dir or (Path(__file__).resolve().parent.parent / "assets" / "audio")
    target_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for slug, generator in SFX_GENERATORS.items():
        wav_path = target_dir / f"{slug}.wav"
        if not wav_path.exists():
            generator(wav_path)
        paths[slug] = wav_path
    return paths


def main():
    audio_dir = Path(__file__).resolve().parent.parent / "assets" / "audio"
    for slug, generator in SFX_GENERATORS.items():
        generator(audio_dir / f"{slug}.wav")


if __name__ == "__main__":
    main()
