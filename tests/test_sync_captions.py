"""
Pruebas unitarias para el motor de subtítulos cinéticos y exportación SRT/VTT.
"""

from core.sync_captions import (
    export_srt,
    export_vtt,
    extract_word_list,
    format_timestamp_srt,
    format_timestamp_vtt,
    generate_html_and_gsap,
    group_words,
)


def test_format_timestamps():
    seconds = 3661.125  # 1h 1m 1s 125ms
    assert format_timestamp_srt(seconds) == "01:01:01,125"
    assert format_timestamp_vtt(seconds) == "01:01:01.125"

    short = 4.050
    assert format_timestamp_srt(short) == "00:00:04,050"
    assert format_timestamp_vtt(short) == "00:00:04.050"


def test_extract_word_list():
    sample_data = {
        "segments": [
            {
                "words": [
                    {"word": " Hola ", "start": 0.5, "end": 0.8},
                    {"word": " mundo ", "start": 0.85, "end": 1.2},
                ]
            }
        ]
    }
    words = extract_word_list(sample_data)
    assert len(words) == 2
    assert words[0]["word"] == "Hola"
    assert words[1]["word"] == "mundo"


def test_group_words():
    words = [
        {"word": "Arquitectura", "start": 1.0, "end": 1.5},
        {"word": "de", "start": 1.55, "end": 1.7},
        {"word": "software", "start": 1.75, "end": 2.2},
        {"word": "en", "start": 2.25, "end": 2.4},
        # Pausa larga aquí (3.2 - 2.4 = 0.8s > 0.4s)
        {"word": "producción", "start": 3.2, "end": 3.8},
    ]

    groups = group_words(words, words_per_group=3, pause_threshold=0.4)
    assert len(groups) == 3
    assert len(groups[0]) == 3  # "Arquitectura", "de", "software"
    assert len(groups[1]) == 1  # "en"
    assert len(groups[2]) == 1  # "producción"


def test_export_srt_and_vtt(tmp_path):
    groups = [
        [
            {"word": "Hola", "start": 1.0, "end": 1.4},
            {"word": "comunidad", "start": 1.45, "end": 2.0},
        ]
    ]
    srt_file = tmp_path / "subtitles.srt"
    vtt_file = tmp_path / "subtitles.vtt"

    export_srt(groups, srt_file)
    export_vtt(groups, vtt_file)

    assert srt_file.exists()
    assert vtt_file.exists()

    srt_text = srt_file.read_text(encoding="utf-8")
    assert "00:00:01,000 --> 00:00:02,000" in srt_text
    assert "Hola comunidad" in srt_text

    vtt_text = vtt_file.read_text(encoding="utf-8")
    assert "WEBVTT" in vtt_text
    assert "00:00:01.000 --> 00:00:02.000" in vtt_text


def test_generate_html_and_gsap():
    groups = [
        [
            {"word": "Docker", "start": 0.5, "end": 0.9},
            {"word": "Containers", "start": 0.95, "end": 1.4},
        ]
    ]
    html_code, gsap_code = generate_html_and_gsap(groups)

    assert '<div id="captions-container" class="caption-bar">' in html_code
    assert '<span id="cw_0_0" class="word">Docker</span>' in html_code
    assert '<span id="cw_0_1" class="word">Containers</span>' in html_code

    assert 'tl.set("#cg_0", { display: "block", opacity: 1 }, 0.500);' in gsap_code
    assert 'tl.to("#cw_0_0", { className: "word active", duration: 0.04 }, 0.500);' in gsap_code
    assert 'tl.set("#cg_0", { opacity: 0, display: "none" }, 1.550);' in gsap_code
