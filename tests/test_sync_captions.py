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
    inject_into_html,
)


def test_format_timestamps():
    seconds = 3661.125  # 1h 1m 1s 125ms
    assert format_timestamp_srt(seconds) == "01:01:01,125"
    assert format_timestamp_vtt(seconds) == "01:01:01.125"

    short = 4.050
    assert format_timestamp_srt(short) == "00:00:04,050"
    assert format_timestamp_vtt(short) == "00:00:04.050"

    # Evitar overflow a 1000ms al redondear cerca del siguiente segundo
    boundary = 1.9999
    assert format_timestamp_srt(boundary) == "00:00:02,000"
    assert format_timestamp_vtt(boundary) == "00:00:02.000"


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


def test_generate_html_and_gsap_styles():
    groups = [
        [
            {"word": "Docker", "start": 0.5, "end": 0.9},
            {"word": "Containers", "start": 0.95, "end": 1.4},
        ]
    ]
    html_code, gsap_code = generate_html_and_gsap(groups, caption_style="minimal_clean")

    assert '<div id="captions-container" class="caption-bar">' in html_code
    assert '<span id="cw_0_0" class="word">Docker</span>' in html_code
    assert '<span id="cw_0_1" class="word">Containers</span>' in html_code

    assert 'tl.set("#cg_0", { display: "inline-block", opacity: 1 }, 0.500);' in gsap_code
    assert 'tl.to("#cw_0_0", { className: "word active", duration: 0.04 }, 0.500);' in gsap_code
    assert 'tl.set("#cg_0", { opacity: 0, display: "none" }, 1.550);' in gsap_code
    assert "scale:" not in gsap_code


def test_idempotent_inject_into_html(tmp_path):
    html_file = tmp_path / "index.html"
    html_file.write_text(
        """<!doctype html>
<html>
  <head><style>:root { --bg: #000; }</style></head>
  <body>
    <div id="root" data-composition-id="main">
      <!-- Subtítulos Cinéticos -->
      <div class="caption-bar">
        <span id="w1" class="word">Demo</span>
      </div>
    </div>
    <script>
      const tl = gsap.timeline({ paused: true });
      tl.to("#w1", { className: "word active", duration: 0.05 }, 1.0);
      window.__timelines = window.__timelines || {};
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>""",
        encoding="utf-8",
    )

    groups_1 = [[{"word": "Primera", "start": 0.2, "end": 0.6}]]
    h1, g1 = generate_html_and_gsap(groups_1, caption_style="minimal_clean")
    inject_into_html(html_file, h1, g1, caption_style="minimal_clean")

    groups_2 = [[{"word": "Segunda", "start": 0.4, "end": 0.9}]]
    h2, g2 = generate_html_and_gsap(groups_2, caption_style="minimal_clean")
    inject_into_html(html_file, h2, g2, caption_style="minimal_clean")

    result = html_file.read_text(encoding="utf-8")
    assert "Segunda" in result
    assert "Primera" not in result
    assert "#w1" not in result
    assert result.count('id="captions-container"') == 1
    assert result.count("// @captions-gsap:start") == 1


def test_inject_handles_backslashes_html_escape_and_nested_divs(tmp_path):
    html_file = tmp_path / "index.html"
    html_file.write_text(
        """<!doctype html>
<html>
  <head><style>:root { --bg: #000; }</style></head>
  <body>
    <div id="root" data-composition-id="main">
      <div id="captions-container" class="caption-bar">
        <div id="cg_0" class="caption-phrase"><span class="word">Viejo</span></div>
        <div id="cg_1" class="caption-phrase"><span class="word">Texto</span></div>
      </div>
    </div>
    <script>
      const tl = gsap.timeline({ paused: true });
      window.__timelines = window.__timelines || {};
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>""",
        encoding="utf-8",
    )

    groups = [[{"word": r"C:\ruta & <tag>", "start": 0.1, "end": 0.5}]]
    h_code, g_code = generate_html_and_gsap(groups)
    inject_into_html(html_file, h_code, g_code)

    result = html_file.read_text(encoding="utf-8")
    assert r"C:\ruta &amp; &lt;tag&gt;" in result
    assert "Viejo" not in result
    assert "Texto" not in result
    assert result.count('id="captions-container"') == 1


def test_group_words_splits_on_punctuation_and_emphasis_words():
    words = [
        {"word": "Estado.", "start": 0.0, "end": 0.4},
        {"word": "Y", "start": 0.45, "end": 0.55},
        {"word": "ver", "start": 0.55, "end": 0.75},
        {"word": "Pegasus", "start": 0.75, "end": 1.2},
    ]
    groups = group_words(words, words_per_group=4, pause_threshold=0.4)
    assert len(groups) == 2
    assert [w["word"] for w in groups[0]] == ["Estado."]
    assert [w["word"] for w in groups[1]] == ["Y", "ver", "Pegasus"]

    html_out, gsap_out = generate_html_and_gsap(
        groups, caption_style="minimal_clean", emphasis_words=["Pegasus"]
    )
    assert 'class="word word-emphasis">Pegasus</span>' in html_out
    assert 'className: "word word-emphasis active"' in gsap_out


def test_consecutive_groups_never_overlap_in_time_and_default_words_per_group():
    words = [
        {"word": "y", "start": 18.0, "end": 18.2},
        {"word": "ninguna", "start": 18.2, "end": 18.6},
        {"word": "cantidad", "start": 18.6, "end": 19.1},
        {"word": "de", "start": 19.1, "end": 19.3},
        {"word": "buenas", "start": 19.3, "end": 19.6},
        {"word": "obras", "start": 19.6, "end": 19.9},
        {"word": "puede", "start": 19.9, "end": 20.2},
        {"word": "borrar", "start": 20.2, "end": 20.6},
    ]
    # Con el valor por defecto words_per_group=6, agrupa en bloques balanceados de hasta 6 palabras (1-2 líneas)
    groups = group_words(words, pause_threshold=0.4)
    assert len(groups) == 2
    assert len(groups[0]) == 6
    assert len(groups[1]) == 2
    _, gsap_code = generate_html_and_gsap(groups, caption_style="minimal_clean")

    # El grupo cg_0 debe ocultarse exactamente en 19.900 (cuando empieza cg_1), nunca en 20.050
    assert 'tl.set("#cg_0", { opacity: 0, display: "none" }, 19.900);' in gsap_code
    assert 'tl.set("#cg_1", { display: "inline-block", opacity: 1 }, 19.900);' in gsap_code
