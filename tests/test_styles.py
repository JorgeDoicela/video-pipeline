"""
Pruebas unitarias para la arquitectura jerárquica de diseño en 3 niveles:
  - Nivel 1: Diseños Macro (DESIGN_SYSTEMS: cinematic, editorial, clean, terminal)
  - Nivel 2: Variantes internas (THEMES, LAYOUT_VARIANTS, CHROME_VARIANTS, MOTION_PROFILES, CAPTION_STYLES)
  - Nivel 3: Overrides granulares (--set clave=valor)
"""

import json

import pytest

from core.styles import (
    CAPTION_STYLES,
    CHROME_VARIANTS,
    DEFAULT_CAPTION_STYLE,
    DEFAULT_DESIGN,
    DEFAULT_THEME,
    DESIGN_SYSTEMS,
    LAYOUT_VARIANTS,
    MOTION_PROFILES,
    THEMES,
    apply_style_to_html,
    apply_style_to_project,
    get_caption_style,
    get_design_system,
    get_theme,
    inspect_project_design,
    parse_set_overrides,
)


def test_catalog_3_levels_integrity():
    assert DEFAULT_DESIGN == "cinematic"
    assert DEFAULT_THEME == "dark_violet"
    assert DEFAULT_CAPTION_STYLE == "minimal_clean"

    assert {"cinematic", "editorial", "clean", "terminal"} == set(DESIGN_SYSTEMS.keys())
    assert {"dark_violet", "paper_warm", "clean_light", "terminal_green"} == set(THEMES.keys())
    assert {"standard", "asymmetric_focus", "stacked"} == set(LAYOUT_VARIANTS.keys())
    assert {"auto", "hidden", "minimal_line", "terminal_bar"} == set(CHROME_VARIANTS.keys())
    assert {"smooth", "snappy", "minimal"} == set(MOTION_PROFILES.keys())
    assert {"highlight_pill", "minimal_clean"} == set(CAPTION_STYLES.keys())


def test_invalid_identifiers_and_overrides():
    with pytest.raises(ValueError, match="no existe"):
        get_design_system("diseno_invalido")

    with pytest.raises(ValueError, match="no existe"):
        get_theme("estilo_inexistente")

    with pytest.raises(ValueError, match="no existe"):
        get_caption_style("subtitulo_inexistente")

    with pytest.raises(ValueError, match="Formato inválido"):
        parse_set_overrides(["clave_sin_igual"])

    with pytest.raises(ValueError, match="no es configurable"):
        parse_set_overrides(["propiedad_inventada=123"])


def test_level1_macro_design_switching(tmp_path):
    """
    Nivel 1: Verifica que cambiar entre los 4 Diseños Macro transforme la geometría,
    sombras, bordes, preset cromático y coreografía GSAP sin perder el contenido del proyecto.
    """
    html_file = tmp_path / "index.html"
    pkg_file = tmp_path / "package.json"
    pkg_file.write_text('{"name": "test-macro"}', encoding="utf-8")

    html_file.write_text(
        """<!doctype html>
<html lang="es">
  <head><style>:root { --bg: #09090b; }</style></head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="10" data-width="1920" data-height="1080">
      <header id="header"><h1>Título Intacto</h1></header>
      <div class="panel">Contenido Técnico</div>
    </div>
    <script>
      const tl = gsap.timeline({ paused: true });
      tl.from("#header", { opacity: 0, y: -20, duration: 0.8, ease: "power2.out" }, 0.2);
      tl.from(".panel", { opacity: 0, y: 30, stagger: 0.2, duration: 0.8, ease: "power3.out" }, 0.4);
      window.__timelines = { main: tl };
    </script>
  </body>
</html>""",
        encoding="utf-8",
    )

    # 1. Cambiar a Diseño Macro editorial
    apply_style_to_project(tmp_path, design_slug="editorial")
    html_ed = html_file.read_text(encoding="utf-8")
    assert 'data-design="editorial"' in html_ed
    assert 'data-style="paper_warm"' in html_ed
    assert "--radius-lg: 4px;" in html_ed
    assert "border-top: 3px solid" not in html_ed
    assert "border: 2px solid var(--text-primary);" in html_ed
    assert "<h1>Título Intacto</h1>" in html_ed

    # 2. Cambiar a Diseño Macro terminal
    apply_style_to_project(tmp_path, design_slug="terminal")
    html_term = html_file.read_text(encoding="utf-8")
    assert 'data-design="terminal"' in html_term
    assert 'data-style="terminal_green"' in html_term
    assert "--radius-lg: 0px;" in html_term
    assert "8px 8px 0px" in html_term
    assert 'ease: "back.out(2.0)"' in html_term

    # 3. Cambiar a Diseño Macro cinematic
    apply_style_to_project(tmp_path, design_slug="cinematic")
    html_cinema = html_file.read_text(encoding="utf-8")
    assert 'data-design="cinematic"' in html_cinema
    assert 'data-style="dark_violet"' in html_cinema
    assert "--radius-lg: 28px;" in html_cinema
    assert "border-left: 6px solid" not in html_cinema
    assert ".badge, .hook-badge {" in html_cinema

    # 4. Cambiar a Diseño Macro clean
    apply_style_to_project(tmp_path, design_slug="clean")
    html_clean = html_file.read_text(encoding="utf-8")
    assert 'data-design="clean"' in html_clean
    assert 'data-style="clean_light"' in html_clean
    assert "--radius-lg: 24px;" in html_clean

    # 5. Inspeccionar estado efectivo del proyecto
    inspected = inspect_project_design(tmp_path)
    assert inspected["design"] == "clean"
    assert inspected["style"] == "clean_light"


def test_level2_intra_design_options_and_level3_overrides(tmp_path):
    """
    Nivel 2 y Nivel 3: Verifica que dentro de un mismo Diseño Macro se puedan
    modificar opciones internas (layout, chrome, motion, style) y overrides puntuales (--set)
    sin perder el Diseño Macro seleccionado.
    """
    html_file = tmp_path / "index.html"
    pkg_file = tmp_path / "package.json"
    pkg_file.write_text('{"name": "test-intra"}', encoding="utf-8")
    html_file.write_text(
        '<style>:root { --bg: #000; }</style><div id="root" data-composition-id="main"><h1>Video</h1></div>',
        encoding="utf-8",
    )

    apply_style_to_project(tmp_path, design_slug="editorial")

    apply_style_to_project(
        tmp_path,
        theme_slug="clean_light",
        layout_slug="asymmetric_focus",
        chrome_slug="minimal_line",
    )
    pkg_data = json.loads(pkg_file.read_text(encoding="utf-8"))
    assert pkg_data["videoDesign"]["design"] == "editorial"
    assert pkg_data["videoDesign"]["style"] == "clean_light"
    assert pkg_data["videoDesign"]["layout"] == "asymmetric_focus"
    assert pkg_data["videoDesign"]["chrome"] == "minimal_line"

    overrides = parse_set_overrides(["accent_primary=#ff5500", "stage_gap=64px"])
    apply_style_to_project(tmp_path, overrides=overrides)

    updated_html = html_file.read_text(encoding="utf-8")
    assert "--accent-primary: #ff5500;" in updated_html
    assert "--stage-gap: 64px;" in updated_html
    assert 'data-design="editorial"' in updated_html

    apply_style_to_project(tmp_path, reset_overrides=True)
    reset_html = html_file.read_text(encoding="utf-8")
    assert "--accent-primary: #0369a1;" in reset_html
    assert 'data-design="editorial"' in reset_html


def test_apply_style_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        apply_style_to_html(tmp_path / "no-existe.html", "dark_violet")


def test_motion_updates_from_to_and_reordered_props(tmp_path):
    html_file = tmp_path / "index.html"
    html_file.write_text(
        """<!doctype html>
<html>
  <head><style>:root { --bg: #000; }</style></head>
  <body>
    <div id="root" data-composition-id="main"></div>
    <script>
      const tl = gsap.timeline({ paused: true });
      tl.fromTo("#header", { opacity: 0 }, { opacity: 1, ease: "power1.out", duration: 0.2 }, 0.1);
      tl.fromTo(".panel", { y: 20 }, { y: 0, ease: "power1.out", duration: 0.2 }, 0.2);
      window.__timelines = { main: tl };
    </script>
  </body>
</html>""",
        encoding="utf-8",
    )
    apply_style_to_html(html_file, motion_slug="snappy")
    updated = html_file.read_text(encoding="utf-8")
    assert 'ease: "power4.out"' in updated
    assert 'ease: "back.out(2.0)"' in updated
    assert "duration: 0.45" in updated
