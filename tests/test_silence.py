"""
Pruebas unitarias para el algoritmo de recorte y cálculo de intervalos de silencio.
"""

from core.cut_silence import build_concat_filter, compute_keep_intervals, cut_and_concat


def test_compute_keep_intervals_no_silence():
    total_dur = 10.0
    silences = []
    keep = compute_keep_intervals(total_dur, silences, padding=0.08)
    assert len(keep) == 1
    assert keep[0] == (0.0, 10.0)


def test_compute_keep_intervals_middle_silence():
    total_dur = 10.0
    # Silencio de 4.0s a 6.0s
    silences = [(4.0, 6.0)]
    keep = compute_keep_intervals(total_dur, silences, padding=0.1)

    assert len(keep) == 2
    # Tramo 1: desde 0.0 hasta 4.0 + 0.1 = 4.1
    assert abs(keep[0][0] - 0.0) < 1e-4
    assert abs(keep[0][1] - 4.1) < 1e-4

    # Tramo 2: desde 6.0 - 0.1 = 5.9 hasta 10.0
    assert abs(keep[1][0] - 5.9) < 1e-4
    assert abs(keep[1][1] - 10.0) < 1e-4


def test_compute_keep_intervals_start_and_end_silence():
    total_dur = 12.0
    # Silencio al inicio (0.0 - 2.0s) y al final (10.0 - 12.0s)
    silences = [(0.0, 2.0), (10.0, 12.0)]
    keep = compute_keep_intervals(total_dur, silences, padding=0.05)

    assert len(keep) == 1
    # Tramo central útil
    assert abs(keep[0][0] - 1.95) < 1e-4
    assert abs(keep[0][1] - 10.05) < 1e-4


def test_compute_keep_intervals_discards_micro_segments():
    total_dur = 5.0
    # Silencio casi continuo con un tramo microscópico de 0.02s
    silences = [(0.0, 2.0), (2.02, 5.0)]
    keep = compute_keep_intervals(total_dur, silences, padding=0.0)

    # El intervalo de 0.02s debe ser descartado (< 0.1s)
    assert len(keep) == 0


def test_build_concat_filter_video_and_audio_only():
    keep = [(0.0, 2.0), (3.5, 5.0)]
    f_av = build_concat_filter(keep, include_video=True)
    assert "[0:v]trim=" in f_av
    assert "[0:a]atrim=" in f_av
    assert "concat=n=2:v=1:a=1[outv][outa]" in f_av

    f_a = build_concat_filter(keep, include_video=False)
    assert "[0:v]" not in f_a
    assert "[0:a]atrim=" in f_a
    assert "concat=n=2:v=0:a=1[outa]" in f_a


def test_cut_and_concat_empty_intervals_respects_format(tmp_path, monkeypatch):
    # Misma extensión: copia directa sin invocar FFmpeg
    src_wav = tmp_path / "in.wav"
    src_wav.write_bytes(b"RIFFdemo")
    dst_wav = tmp_path / "out.wav"
    cut_and_concat(str(src_wav), str(dst_wav), [])
    assert dst_wav.read_bytes() == b"RIFFdemo"

    # Extensión distinta (.mp3 -> .wav): debe invocar FFmpeg en vez de copiar bytes crudos
    src_mp3 = tmp_path / "in.mp3"
    src_mp3.write_bytes(b"ID3demo")
    dst_conv = tmp_path / "conv.wav"
    captured_cmds: list[list[str]] = []

    def fake_run(cmd, check=True):
        captured_cmds.append(cmd)
        dst_conv.write_bytes(b"RIFFconverted")

    monkeypatch.setattr("core.cut_silence._resolve_media_bin", lambda name: name)
    monkeypatch.setattr("core.cut_silence.subprocess.run", fake_run)

    cut_and_concat(str(src_mp3), str(dst_conv), [])
    assert len(captured_cmds) == 1
    assert "pcm_s16le" in captured_cmds[0]
    assert dst_conv.read_bytes() == b"RIFFconverted"
