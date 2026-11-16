"""
Pruebas unitarias para generación procedural de SFX y mezcla de audio con FFmpeg.
"""

from pathlib import Path

from core.audio_mix import build_sfx_mix_command
from core.generate_sfx import SFX_GENERATORS, ensure_sfx_assets


def test_ensure_sfx_assets_generates_all_wavs(tmp_path: Path):
    assets = ensure_sfx_assets(tmp_path)
    expected_keys = {
        "whoosh",
        "pop",
        "click",
        "chime",
        "beep",
        "sub_hit",
        "glitch",
        "scan",
        "drone",
    }
    assert set(assets.keys()) == expected_keys
    assert set(SFX_GENERATORS.keys()) == expected_keys

    for name, wav_path in assets.items():
        assert wav_path.exists(), f"Falta archivo WAV para {name}"
        assert wav_path.stat().st_size > 1000


def test_build_sfx_mix_command_without_voice(tmp_path: Path):
    sfx_a = tmp_path / "sub_hit.wav"
    sfx_b = tmp_path / "whoosh.wav"
    out = tmp_path / "audio_mix.wav"

    cmd = build_sfx_mix_command(
        voice_path=None,
        events=[
            (sfx_a, 0.0, 0.45),
            (sfx_b, 2.5, 0.35),
        ],
        total_duration=8.0,
        output_wav=out,
        ffmpeg_bin="ffmpeg",
    )

    assert cmd[0] == "ffmpeg"
    assert "anullsrc=r=48000:cl=stereo" in cmd
    assert "-filter_complex" in cmd
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "adelay=2500|2500" in fc
    assert "amix=inputs=3" in fc
    assert str(out) == cmd[-1]


def test_build_sfx_mix_command_with_voice(tmp_path: Path):
    voice = tmp_path / "voice.wav"
    sfx_a = tmp_path / "pop.wav"
    out = tmp_path / "audio_mix.wav"

    cmd = build_sfx_mix_command(
        voice_path=voice,
        events=[(sfx_a, 1.25, 0.5)],
        total_duration=5.0,
        output_wav=out,
        ffmpeg_bin="ffmpeg",
    )

    assert str(voice) in cmd
    assert "anullsrc=r=48000:cl=stereo" not in cmd
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "adelay=1250|1250" in fc
    assert "amix=inputs=2" in fc


def test_build_sfx_mix_command_with_music_ducking(tmp_path: Path):
    voice = tmp_path / "voice.wav"
    music = tmp_path / "drone.wav"
    sfx_a = tmp_path / "scan.wav"
    out = tmp_path / "audio_mix.wav"

    cmd = build_sfx_mix_command(
        voice_path=voice,
        events=[(sfx_a, 0.8, 0.4)],
        total_duration=6.0,
        output_wav=out,
        ffmpeg_bin="ffmpeg",
        music_path=music,
        music_volume=0.15,
    )

    assert "-stream_loop" in cmd
    assert str(music) in cmd
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "asplit=2[base][sc]" in fc
    assert "sidechaincompress=" in fc
    assert "amix=inputs=3" in fc
