"""
Pruebas unitarias para el algoritmo de recorte y cálculo de intervalos de silencio.
"""

from core.cut_silence import compute_keep_intervals


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
