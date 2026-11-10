"""
Pruebas unitarias para la arquitectura jerárquica de diseño en 3 niveles:
  - Nivel 1: Diseños Macro (DESIGN_SYSTEMS: cyber_glass, swiss_editorial, brutalist_terminal, cinematic_studio)
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
    assert DEFAULT_DESIGN == "cyber_glass"
    assert DEFAULT_THEME == "cyber_dark"
    assert DEFAULT_CAPTION_STYLE == "karaoke_glow"

    assert {
        "cyber_glass",
        "clean_studio",
        "swiss_editorial",
        "brutalist_terminal",
        "cinematic_studio",
        "bento_grid",
        "academic_paper",
    } == set(DESIGN_SYSTEMS.keys())
    assert {
        "cyber_dark",
        "minimal_light",
        "terminal_hacker",
        "linear_violet",
        "blueprint_cad",
        "dracula_pro",
        "solarized_sand",
        "crimson_ops",
    } == set(THEMES.keys())
    assert {"standard", "asymmetric_focus", "stacked", "compact_hud"} == set(LAYOUT_VARIANTS.keys())
    assert {"auto", "macos_dots", "terminal_bar", "minimal_line", "hidden"} == set(
        CHROME_VARIANTS.keys()
    )
    assert {"dynamic", "smooth", "snappy", "minimal"} == set(MOTION_PROFILES.keys())
    assert {
        "karaoke_glow",
        "highlight_pill",
        "pop_scale",
        "minimal_clean",
        "underline_bar",
        "box_invert",
    } == set(CAPTION_STYLES.keys())


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
    Nivel 1: Verifica que cambiar entre Diseños Macro transforme la geometría,
    sombras, bordes, preset cromático y coreografía GSAP sin perder el contenido del proyecto.
    """
    html_file = tmp_path / "index.html"
    pkg_file = tmp_path / "package.json"
    pkg_file.write_text('{"name": "test-macro"}', encoding="utf-8")

    html_file.write_text(
        """<!doctype html>
<html lang="es">
  <head><style>:root { --bg: #070b14; }</style></head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="10" data-width="1920" data-height="1080">
      <header id="header"><h1>Título Intacto</h1></header>
      <div class="panel">Contenido Técnico</div>
    </div>
    <script>
      const tl = gsap.timeline({ paused: true });
      tl.from("#header", { opacity: 0, y: -20, duration: 0.8, ease: "power2.out" }, 0.2);
      tl.from(".panel", { opacity: 0, y: 30, stagger: 0.2, duration: 0.8, ease: "back.out(1.5)" }, 0.4);
      window.__timelines = { main: tl };
    </script>
  </body>
</html>""",
        encoding="utf-8",
    )

    # 1. Cambiar a Diseño Macro swiss_editorial
    apply_style_to_project(tmp_path, design_slug="swiss_editorial")
    html_swiss = html_file.read_text(encoding="utf-8")
    assert 'data-design="swiss_editorial"' in html_swiss
    assert 'data-style="minimal_light"' in html_swiss
    assert "--radius-lg: 2px;" in html_swiss
    assert "border-top: 4px solid var(--text-primary);" in html_swiss
    assert "<h1>Título Intacto</h1>" in html_swiss

    # 2. Cambiar a Diseño Macro brutalist_terminal
    apply_style_to_project(tmp_path, design_slug="brutalist_terminal")
    html_brutal = html_file.read_text(encoding="utf-8")
    assert 'data-design="brutalist_terminal"' in html_brutal
    assert 'data-style="terminal_hacker"' in html_brutal
    assert "--radius-lg: 0px;" in html_brutal
    assert "8px 8px 0px" in html_brutal
    assert 'ease: "back.out(2.0)"' in html_brutal

    # 3. Cambiar a Diseño Macro cinematic_studio
    apply_style_to_project(tmp_path, design_slug="cinematic_studio")
    html_cinema = html_file.read_text(encoding="utf-8")
    assert 'data-design="cinematic_studio"' in html_cinema
    assert 'data-style="linear_violet"' in html_cinema
    assert "--radius-lg: 28px;" in html_cinema
    assert "border-left: 6px solid var(--accent-primary);" in html_cinema

    # 4. Cambiar a Diseño Macro bento_grid
    apply_style_to_project(tmp_path, design_slug="bento_grid")
    html_bento = html_file.read_text(encoding="utf-8")
    assert 'data-design="bento_grid"' in html_bento
    assert 'data-style="dracula_pro"' in html_bento
    assert "--radius-lg: 24px;" in html_bento

    # 5. Cambiar a Diseño Macro academic_paper
    apply_style_to_project(tmp_path, design_slug="academic_paper")
    html_paper = html_file.read_text(encoding="utf-8")
    assert 'data-design="academic_paper"' in html_paper
    assert 'data-style="solarized_sand"' in html_paper
    assert "--radius-lg: 4px;" in html_paper
    assert "border-top: 3px solid var(--text-primary);" in html_paper

    # 6. Cambiar a Diseño Macro clean_studio
    apply_style_to_project(tmp_path, design_slug="clean_studio")
    html_clean = html_file.read_text(encoding="utf-8")
    assert 'data-design="clean_studio"' in html_clean
    assert 'data-style="minimal_light"' in html_clean
    assert "--radius-lg: 28px;" in html_clean

    # 7. Inspeccionar estado efectivo del proyecto
    inspected = inspect_project_design(tmp_path)
    assert inspected["design"] == "clean_studio"
    assert inspected["style"] == "minimal_light"


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

    # Fijar Diseño Macro swiss_editorial
    apply_style_to_project(tmp_path, design_slug="swiss_editorial")

    # Nivel 2: Cambiar solo el layout y la paleta dentro de swiss_editorial
    apply_style_to_project(
        tmp_path,
        theme_slug="blueprint_cad",
        layout_slug="asymmetric_focus",
        chrome_slug="hidden",
    )
    pkg_data = json.loads(pkg_file.read_text(encoding="utf-8"))
    assert pkg_data["videoDesign"]["design"] == "swiss_editorial"
    assert pkg_data["videoDesign"]["style"] == "blueprint_cad"
    assert pkg_data["videoDesign"]["layout"] == "asymmetric_focus"
    assert pkg_data["videoDesign"]["chrome"] == "hidden"

    # Nivel 3: Aplicar override puntual solo en este diseño
    overrides = parse_set_overrides(["accent_primary=#ff5500", "stage_gap=64px"])
    apply_style_to_project(tmp_path, overrides=overrides)

    updated_html = html_file.read_text(encoding="utf-8")
    assert "--accent-primary: #ff5500;" in updated_html
    assert "--stage-gap: 64px;" in updated_html
    assert 'data-design="swiss_editorial"' in updated_html

    # Resetear overrides conservando el diseño y sus opciones de Nivel 2
    apply_style_to_project(tmp_path, reset_overrides=True)
    reset_html = html_file.read_text(encoding="utf-8")
    assert "--accent-primary: #64ffda;" in reset_html
    assert 'data-design="swiss_editorial"' in reset_html


def test_apply_style_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        apply_style_to_html(tmp_path / "no-existe.html", "cyber_dark")
