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


def generate_scan(path: Path) -> None:
    """Genera un barrido electrónico limpio para escáneres láser, radares y rayos X."""
    duration = 0.34
    num_samples = int(SAMPLE_RATE * duration)
    samples: list[float] = []
    phase = 0.0
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        freq = 340.0 + 680.0 * math.sin(math.pi * (t / duration))
        phase += 2.0 * math.pi * freq / SAMPLE_RATE
        mod = 0.75 + 0.25 * math.sin(2.0 * math.pi * 28.0 * t)
        env = math.sin(math.pi * (t / duration)) ** 1.4
        samples.append(math.sin(phase) * mod * env * 0.48)
    write_wav(path, samples)


def generate_drone(path: Path) -> None:
    """Genera una cama ambiental grave cinemática (4.0s, ciclo exacto loopable sin clics)."""
    duration = 4.0
    num_samples = int(SAMPLE_RATE * duration)
    samples: list[float] = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        # Frecuencias múltiplo exacto de 0.25Hz para fase continua en loop de 4.0s
        f1 = math.sin(2.0 * math.pi * 55.0 * t) * 0.52
        f2 = math.sin(2.0 * math.pi * 110.0 * t) * 0.28
        f3 = math.sin(2.0 * math.pi * 165.0 * t) * 0.12
        lfo = 0.72 + 0.28 * math.sin(2.0 * math.pi * 0.5 * t)
        samples.append((f1 + f2 + f3) * lfo * 0.55)
    write_wav(path, samples)


def generate_shutter(path: Path) -> None:
    """Genera un doble clic mecánico de obturador de cámara para capturas de pantalla."""
    duration = 0.14
    num_samples = int(SAMPLE_RATE * duration)
    samples: list[float] = []
    rng = random.Random(77)
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        burst1 = math.exp(-(((t - 0.015) / 0.008) ** 2))
        burst2 = math.exp(-(((t - 0.068) / 0.010) ** 2)) * 0.85
        noise = rng.uniform(-1.0, 1.0)
        metallic = (
            math.sin(2.0 * math.pi * 2600.0 * t) * 0.35
            + math.sin(2.0 * math.pi * 1150.0 * t) * 0.25
        )
        samples.append((noise * 0.65 + metallic) * (burst1 + burst2) * 0.72)
    write_wav(path, samples)


def generate_riser(path: Path) -> None:
    """Genera un ascenso de tensión filtrado (1.1s) para revelaciones narrativas."""
    duration = 1.10
    num_samples = int(SAMPLE_RATE * duration)
    samples: list[float] = []
    rng = random.Random(303)
    phase = 0.0
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        p = t / duration
        freq = 110.0 + 720.0 * (p**2.2)
        phase += 2.0 * math.pi * freq / SAMPLE_RATE
        env = (p**1.6) * min(1.0, (duration - t) / 0.04)
        noise = rng.uniform(-1.0, 1.0) * 0.32 * p
        samples.append((math.sin(phase) * 0.68 + noise) * env * 0.62)
    write_wav(path, samples)


def generate_boom(path: Path) -> None:
    """Genera un sub-impacto cinematográfico grave (0.85s) para titulares o giros clave."""
    duration = 0.85
    num_samples = int(SAMPLE_RATE * duration)
    samples: list[float] = []
    phase = 0.0
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        freq = 28.0 + 68.0 * math.exp(-7.5 * t)
        phase += 2.0 * math.pi * freq / SAMPLE_RATE
        attack = min(1.0, t / 0.006)
        env = attack * math.exp(-3.8 * t)
        punch = math.sin(2.0 * math.pi * 140.0 * t) * math.exp(-32.0 * t) * 0.35
        samples.append(math.tanh((math.sin(phase) + punch) * 1.5) * env * 0.88)
    write_wav(path, samples)


def generate_keyclick(path: Path) -> None:
    """Genera una pulsación mecánica nítida de teclado (0.045s)."""
    duration = 0.045
    num_samples = int(SAMPLE_RATE * duration)
    samples: list[float] = []
    rng = random.Random(909)
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = math.exp(-95.0 * t)
        body = math.sin(2.0 * math.pi * 1850.0 * t) * 0.45
        tick = rng.uniform(-1.0, 1.0) * 0.55
        samples.append((body + tick) * env * 0.68)
    write_wav(path, samples)


def generate_powerdown(path: Path) -> None:
    """Genera una caída de tono tipo apagón CRT o reinicio forzado de sistema (0.55s)."""
    duration = 0.55
    num_samples = int(SAMPLE_RATE * duration)
    samples: list[float] = []
    phase = 0.0
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        p = t / duration
        freq = 540.0 * ((1.0 - p) ** 2.4) + 38.0
        phase += 2.0 * math.pi * freq / SAMPLE_RATE
        env = min(1.0, t / 0.01) * ((1.0 - p) ** 0.85)
        samples.append(math.sin(phase) * env * 0.62)
    write_wav(path, samples)


def generate_alarm(path: Path) -> None:
    """Genera un doble pulso táctico de advertencia/alerta de sistema (0.36s)."""
    duration = 0.36
    num_samples = int(SAMPLE_RATE * duration)
    samples: list[float] = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        in_p1 = 0.0 <= t < 0.13
        in_p2 = 0.19 <= t < 0.34
        if not (in_p1 or in_p2):
            samples.append(0.0)
            continue
        local_t = t if in_p1 else (t - 0.19)
        env = min(1.0, local_t / 0.008) * math.exp(-6.0 * local_t)
        val = (
            math.sin(2.0 * math.pi * 880.0 * t) * 0.6 + math.sin(2.0 * math.pi * 1320.0 * t) * 0.25
        )
        samples.append(val * env * 0.55)
    write_wav(path, samples)


def generate_music_tension_pulse(path: Path) -> None:
    """Cama musical procedural oscura (8.0s loopable, 120 BPM) para ciberseguridad e investigación."""
    duration = 8.0
    num_samples = int(SAMPLE_RATE * duration)
    samples: list[float] = []
    # Progresión de bajos (múltiplos exactos de 0.125Hz para loop sin clics)
    bass_notes = [55.0, 55.0, 44.0, 49.0]  # A1, A1, F1 aprox, G1 aprox
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        bar_idx = int(t // 2.0) % len(bass_notes)
        f_bass = bass_notes[bar_idx]
        beat_phase = (t % 0.5) / 0.5
        pulse_env = math.exp(-5.5 * beat_phase)
        bass = (
            math.sin(2.0 * math.pi * f_bass * t) * 0.55
            + math.sin(2.0 * math.pi * (f_bass * 2.0) * t) * 0.22
        ) * (0.45 + 0.55 * pulse_env)
        pad = (
            math.sin(2.0 * math.pi * 220.0 * t) * 0.14
            + math.sin(2.0 * math.pi * 262.0 * t) * 0.10
            + math.sin(2.0 * math.pi * 330.0 * t) * 0.08
        ) * (0.75 + 0.25 * math.sin(2.0 * math.pi * 0.25 * t))
        tick = math.sin(2.0 * math.pi * 1600.0 * t) * math.exp(-65.0 * beat_phase) * 0.08
        samples.append((bass + pad + tick) * 0.55)
    write_wav(path, samples)


def generate_music_tech_minimal(path: Path) -> None:
    """Cama musical limpia y minimalista (8.0s loopable) para arquitectura, código y tutoriales."""
    duration = 8.0
    num_samples = int(SAMPLE_RATE * duration)
    samples: list[float] = []
    roots = [65.0, 73.0, 82.0, 73.0]
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        root = roots[int(t // 2.0) % len(roots)]
        fifth = root * 1.5
        beat_p = (t % 0.5) / 0.5
        soft_pulse = 0.65 + 0.35 * math.exp(-4.0 * beat_p)
        val = (
            math.sin(2.0 * math.pi * root * t) * 0.42
            + math.sin(2.0 * math.pi * fifth * t) * 0.24
            + math.sin(2.0 * math.pi * (root * 4.0) * t) * 0.10 * math.exp(-7.0 * beat_p)
        )
        samples.append(val * soft_pulse * 0.52)
    write_wav(path, samples)


def generate_music_editorial_warm(path: Path) -> None:
    """Cama ambiental cálida y sobria (8.0s loopable) para ensayos, historia y documentales."""
    duration = 8.0
    num_samples = int(SAMPLE_RATE * duration)
    samples: list[float] = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        swell = 0.72 + 0.28 * math.sin(2.0 * math.pi * 0.125 * t)
        chord = (
            math.sin(2.0 * math.pi * 130.0 * t) * 0.36
            + math.sin(2.0 * math.pi * 195.0 * t) * 0.24
            + math.sin(2.0 * math.pi * 260.0 * t) * 0.18
            + math.sin(2.0 * math.pi * 325.0 * t) * 0.12
        )
        samples.append(chord * swell * 0.48)
    write_wav(path, samples)


SFX_GENERATORS = {
    "whoosh": generate_whoosh,
    "pop": generate_pop,
    "click": generate_click,
    "chime": generate_chime,
    "beep": generate_beep,
    "sub_hit": generate_sub_hit,
    "glitch": generate_glitch,
    "scan": generate_scan,
    "drone": generate_drone,
    "shutter": generate_shutter,
    "riser": generate_riser,
    "boom": generate_boom,
    "keyclick": generate_keyclick,
    "powerdown": generate_powerdown,
    "alarm": generate_alarm,
}

MUSIC_GENERATORS = {
    "tension_pulse": generate_music_tension_pulse,
    "tech_minimal": generate_music_tech_minimal,
    "editorial_warm": generate_music_editorial_warm,
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


def ensure_music_assets(music_dir: Path | None = None) -> dict[str, Path]:
    """Garantiza que las bases musicales procedurales del catálogo existan en assets/music/."""
    target_dir = music_dir or (Path(__file__).resolve().parent.parent / "assets" / "music")
    target_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for slug, generator in MUSIC_GENERATORS.items():
        wav_path = target_dir / f"{slug}.wav"
        if not wav_path.exists():
            generator(wav_path)
        paths[slug] = wav_path
    return paths


def resolve_music_source(
    music_spec: str | Path | None, music_dir: Path | None = None
) -> Path | None:
    """Resuelve un preset musical (ej. 'tension_pulse') o una ruta local de archivo de audio."""
    if not music_spec:
        return None
    raw = str(music_spec).strip()
    if not raw or raw.lower() == "none":
        return None
    key = raw.lower().removesuffix(".wav")
    if key in MUSIC_GENERATORS:
        return ensure_music_assets(music_dir)[key]
    candidate = Path(raw)
    if candidate.exists():
        return candidate
    assets_candidate = (
        music_dir or (Path(__file__).resolve().parent.parent / "assets" / "music")
    ) / raw
    if assets_candidate.exists():
        return assets_candidate
    raise FileNotFoundError(
        f"No se encontró la pista musical '{music_spec}'. Presets disponibles: {', '.join(MUSIC_GENERATORS)}"
    )


def main():
    audio_dir = Path(__file__).resolve().parent.parent / "assets" / "audio"
    for slug, generator in SFX_GENERATORS.items():
        generator(audio_dir / f"{slug}.wav")
    music_dir = Path(__file__).resolve().parent.parent / "assets" / "music"
    for slug, generator in MUSIC_GENERATORS.items():
        generator(music_dir / f"{slug}.wav")


if __name__ == "__main__":
    main()
