"""
Motor de renderizado CSS, inyección idempotente en HTML y persistencia de diseño en 3 niveles.
"""

import json
import re
import sys
from dataclasses import asdict
from pathlib import Path

from core._runtime import resolve_project_dir
from core._styles_catalog import (
    CAPTION_STYLES,
    DEFAULT_CAPTION_STYLE,
    DEFAULT_DESIGN,
    DEFAULT_LAYOUT,
    DEFAULT_MOTION,
    DEFAULT_THEME,
    DESIGN_SYSTEMS,
    LAYOUT_VARIANTS,
    MOTION_PROFILES,
    OVERRIDABLE_KEYS,
    THEMES,
    CaptionStyle,
    DesignSystem,
    LayoutVariant,
    VisualTheme,
    get_caption_style,
    get_design_system,
    get_layout_variant,
    get_motion_profile,
    get_theme,
)


def parse_set_overrides(raw_pairs: list[str] | None) -> dict[str, str]:
    """Valida y convierte pares 'clave=valor' del Nivel 3 en un diccionario tipado."""
    if not raw_pairs:
        return {}
    parsed: dict[str, str] = {}
    for item in raw_pairs:
        if "=" not in item:
            raise ValueError(
                f"Formato inválido en --set '{item}'. Use 'clave=valor' (ej. accent_primary=#ff5500)."
            )
        key, val = item.split("=", 1)
        key = key.strip().replace("-", "_")
        val = val.strip()
        if key not in OVERRIDABLE_KEYS:
            valid = ", ".join(sorted(OVERRIDABLE_KEYS))
            raise ValueError(
                f"La propiedad '{key}' no es configurable vía --set. Propiedades válidas: {valid}"
            )
        parsed[key] = val
    return parsed


def build_root_css_block(
    theme: VisualTheme,
    design: DesignSystem,
    layout: LayoutVariant,
    overrides: dict[str, str] | None = None,
) -> str:
    """
    Construye el bloque :root combinando el Diseño Macro (Nivel 1),
    el Tema y Layout (Nivel 2) y los Overrides granulares (Nivel 3).
    """
    ov = overrides or {}

    def pick(key: str, default_val: str) -> str:
        return ov.get(key, default_val)

    card_shadow = "none" if design.shadow_mode == "none" else pick("shadow", theme.shadow)

    lines = [
        "      /* @theme:start */",
        f"      /* Design: {design.slug} | Theme: {theme.slug} | Layout: {layout.slug} */",
        "      :root {",
        f'        --design-slug: "{design.slug}";',
        f'        --theme-slug: "{theme.slug}";',
        f'        --layout-slug: "{layout.slug}";',
        f"        --bg: {pick('bg', theme.bg)};",
        f"        --bg-gradient: {theme.bg_gradient};",
        f"        --surface: {pick('surface', theme.surface)};",
        f"        --surface-elevated: {pick('surface_elevated', theme.surface_elevated)};",
        f"        --border: {pick('border', theme.border)};",
        f"        --border-strong: {pick('border_strong', theme.border_strong)};",
        f"        --divider: {pick('divider', theme.divider)};",
        f"        --shadow: {card_shadow};",
        f"        --text-primary: {pick('text_primary', theme.text_primary)};",
        f"        --text-secondary: {pick('text_secondary', theme.text_secondary)};",
        f"        --text-muted: {pick('text_muted', theme.text_muted)};",
        f"        --title-gradient: {theme.title_gradient};",
        f"        --font-display: {pick('font_display', theme.font_display)};",
        f"        --font-sans: {pick('font_sans', theme.font_sans)};",
        f"        --font-mono: {pick('font_mono', theme.font_mono)};",
        f"        --accent-primary: {pick('accent_primary', theme.accent_primary)};",
        f"        --accent-primary-soft: {theme.accent_primary_soft};",
        f"        --accent-primary-glow: {theme.accent_primary_glow};",
        f"        --accent-secondary: {pick('accent_secondary', theme.accent_secondary)};",
        f"        --accent-secondary-soft: {theme.accent_secondary_soft};",
        f"        --accent-tertiary: {pick('accent_tertiary', theme.accent_tertiary)};",
        f"        --accent-warning: {pick('accent_warning', theme.accent_warning)};",
        f"        --accent-danger: {pick('accent_danger', theme.accent_danger)};",
        f"        --node-fill: {pick('node_fill', theme.node_fill)};",
        f"        --cable-idle: {pick('cable_idle', theme.cable_idle)};",
        f"        --caption-bg: {pick('caption_bg', theme.caption_bg)};",
        f"        --caption-text: {pick('caption_text', theme.caption_text)};",
        f"        --caption-active: {pick('caption_active', theme.caption_active)};",
        f"        --caption-shadow: {theme.caption_shadow};",
        f"        --caption-glow: {theme.caption_glow};",
        "        /* Tokens estructurales de Diseño Macro y Layout */",
        f"        --radius-lg: {pick('radius_lg', design.radius_lg)};",
        f"        --radius-md: {pick('radius_md', design.radius_md)};",
        f"        --radius-sm: {pick('radius_sm', design.radius_sm)};",
        f"        --border-width: {pick('border_width', design.border_width)};",
        f"        --panel-backdrop: {design.panel_backdrop};",
        f"        --stage-padding: {pick('stage_padding', layout.stage_padding)};",
        f"        --stage-gap: {pick('stage_gap', layout.stage_gap)};",
        f"        --split-columns: {pick('split_columns', layout.split_columns)};",
        f"        --header-align: {pick('header_align', layout.header_align)};",
        f"        --caption-bottom: {pick('caption_bottom', layout.caption_bottom)};",
        f"        --caption-size: {pick('caption_size', layout.caption_size)};",
        "        /* Alias de compatibilidad con plantillas existentes */",
        "        --card: var(--surface);",
        "        --card-bg: var(--surface);",
        "        --panel-bg: var(--surface);",
        "        --border-color: var(--border);",
        "        --card-border: var(--border);",
        "        --panel-border: var(--border);",
        "        --text: var(--text-primary);",
        "        --text-sub: var(--text-muted);",
        "        --text-code: var(--text-secondary);",
        "        --cyan: var(--accent-primary);",
        "        --cyan-glow: var(--accent-primary-glow);",
        "        --green: var(--accent-secondary);",
        "        --purple: var(--accent-tertiary);",
        "        --gold: var(--accent-warning);",
        "        --red: var(--accent-danger);",
        "      }",
        "      /* @theme:end */",
    ]
    return "\n".join(lines)


def generate_design_structural_css(
    design: DesignSystem,
    layout: LayoutVariant,
    overrides: dict[str, str] | None = None,
) -> str:
    """
    Genera de forma declarativa el bloque de reglas estructurales CSS combinando
    el Diseño Macro (Nivel 1), el Layout (Nivel 2) y los Overrides (Nivel 3).
    """
    ov = overrides or {}
    lower_side = ov.get("lower_third_side", layout.lower_third_side)

    lines = [
        "      /* @design-system:start */",
        f"      /* Macro Design: {design.slug} | Layout: {layout.slug} */",
        "      h1, h2, .main-title, .scene-headline, .ng-quote-text, .quote-text {",
        "        font-family: var(--font-display);",
        "      }",
        "      .panel, #main-card {",
        "        border-radius: var(--radius-lg);",
        "        border: var(--border-width) solid var(--border);",
        "        box-shadow: var(--shadow);",
        "        backdrop-filter: var(--panel-backdrop);",
        "      }",
        "      .badge, .hook-badge {",
        "        display: inline-flex;",
        "        align-items: center;",
        "        gap: 8px;",
        "        background: transparent;",
        "        border: none;",
        "        padding: 0;",
        "        color: var(--accent-primary);",
        "        font-weight: 800;",
        "        letter-spacing: 0.15em;",
        "        text-transform: uppercase;",
        "      }",
        "      .badge svg, .hook-badge svg {",
        "        background: transparent;",
        "        border: none;",
        "        padding: 0;",
        "      }",
        "      .split-stage {",
        "        grid-template-columns: var(--split-columns);",
        "        gap: var(--stage-gap);",
        "      }",
        "      .caption-bar {",
        "        bottom: var(--caption-bottom);",
        "        font-size: var(--caption-size);",
        "      }",
    ]

    lines.extend(f"      {rule}" for rule in design.structural_css)

    if lower_side == "right":
        lines.extend(
            [
                "      .lower-third {",
                "        left: auto;",
                "        right: 80px;",
                "        border: var(--border-width) solid var(--border);",
                "        border-radius: var(--radius-md);",
                "      }",
            ]
        )
    else:
        lines.extend(
            [
                "      .lower-third {",
                "        left: 80px;",
                "        right: auto;",
                "        border: var(--border-width) solid var(--border);",
                "        border-radius: var(--radius-md);",
                "      }",
            ]
        )

    lines.append("      /* @design-system:end */")
    return "\n".join(lines)


def generate_caption_css(caption_style: CaptionStyle) -> str:
    """Genera las reglas CSS deterministas para el estilo de subtítulos seleccionado."""
    lines = [
        "      /* @caption-style:start */",
        f"      /* Caption Style: {caption_style.slug} */",
        "      .caption-phrase {",
        "        display: inline-block;",
        "        max-width: 780px;",
        "        text-wrap: balance;",
        "        background: transparent;",
        "        padding: 0;",
        "        border: none;",
        "      }",
        "      .word {",
        "        display: inline-block;",
        f"        opacity: {caption_style.word_inactive_opacity};",
        "        color: var(--caption-text);",
        "        margin: 0 4px;",
        "      }",
        "      .word.active {",
        *[f"        {rule}" for rule in caption_style.active_css],
        "      }",
        "      .word.word-emphasis.active {",
        "        color: var(--accent-secondary);",
        "        opacity: 1;",
        "        background: transparent;",
        "        border: none;",
        "        padding: 0;",
        "        text-shadow: var(--caption-shadow);",
        "      }",
        "      /* @caption-style:end */",
    ]
    return "\n".join(lines)


def upsert_marked_css_block(content: str, marker_name: str, css_block: str) -> str:
    """Inserta o reemplaza de forma idempotente un bloque CSS delimitado por /* @marker:start/end */."""
    start_tag = f"/* @{marker_name}:start */"
    end_tag = f"/* @{marker_name}:end */"
    if start_tag in content and end_tag in content:
        pattern = rf"\s*{re.escape(start_tag)}.*?{re.escape(end_tag)}"
        return re.sub(pattern, lambda _: "\n" + css_block, content, count=1, flags=re.DOTALL)
    if marker_name == "theme" and ":root" in content:
        return re.sub(
            r"\s*:root\s*\{[^}]*\}", lambda _: "\n" + css_block, content, count=1, flags=re.DOTALL
        )
    if "</style>" in content:
        return content.replace("</style>", f"{css_block}\n    </style>", 1)
    return content


def apply_style_to_html(
    html_path: Path,
    theme_slug: str = DEFAULT_THEME,
    caption_style_slug: str | None = None,
    design_slug: str = DEFAULT_DESIGN,
    layout_slug: str = DEFAULT_LAYOUT,
    motion_slug: str = DEFAULT_MOTION,
    overrides: dict[str, str] | None = None,
) -> None:
    """
    Aplica de forma idempotente y no destructiva los 3 niveles de diseño sobre index.html.
    """
    if not html_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo HTML: {html_path}")

    design = get_design_system(design_slug)
    theme = get_theme(theme_slug)
    layout = get_layout_variant(layout_slug)
    motion = get_motion_profile(motion_slug)

    content = html_path.read_text(encoding="utf-8")
    css_vars_block = build_root_css_block(theme, design, layout, overrides=overrides)
    design_css_block = generate_design_structural_css(design, layout, overrides=overrides)

    content = upsert_marked_css_block(content, "theme", css_vars_block)
    content = upsert_marked_css_block(content, "design-system", design_css_block)

    if caption_style_slug is not None:
        cap_style = get_caption_style(caption_style_slug)
        content = upsert_marked_css_block(content, "caption-style", generate_caption_css(cap_style))

    def _replace_motion_props(match: re.Match[str], ease_val: str) -> str:
        block = match.group(0)
        block = re.sub(r"(duration:\s*)[0-9.]+", rf"\g<1>{motion.entry_duration}", block)
        block = re.sub(r'(ease:\s*")[a-zA-Z0-9.()]+(")', rf"\g<1>{ease_val}\g<2>", block)
        return block

    content = re.sub(
        r'tl\.(?:from|fromTo)\("#header",\s*\{[^}]*\}(?:\s*,\s*\{[^}]*\})?',
        lambda m: _replace_motion_props(m, motion.entry_ease),
        content,
    )
    content = re.sub(
        r'tl\.(?:from|fromTo)\("(?:\.panel|#main-card)",\s*\{[^}]*\}(?:\s*,\s*\{[^}]*\})?',
        lambda m: _replace_motion_props(m, motion.panel_ease),
        content,
    )

    attrs = {
        "data-design": design.slug,
        "data-style": theme.slug,
        "data-layout": layout.slug,
        "data-motion": motion.slug,
    }
    if caption_style_slug is not None:
        attrs["data-caption-style"] = caption_style_slug

    if 'data-composition-id="main"' in content:
        for attr_name, attr_val in attrs.items():
            if f"{attr_name}=" in content:
                content = re.sub(
                    rf'{attr_name}="[^"]*"',
                    f'{attr_name}="{attr_val}"',
                    content,
                    count=1,
                )
            else:
                content = re.sub(
                    r'(data-composition-id="main")',
                    rf'\g<1>\n      {attr_name}="{attr_val}"',
                    content,
                    count=1,
                )

    html_path.write_text(content, encoding="utf-8")


def _resolve_project_html(project_or_html: str | Path) -> Path:
    target = Path(project_or_html)
    if target.is_file():
        return target
    proj_dir = resolve_project_dir(project_or_html)
    html_file = proj_dir / "index.html"
    if not html_file.exists():
        raise FileNotFoundError(f"No se encontró index.html en '{proj_dir}'.")
    return html_file


def inspect_project_design(project_or_html: str | Path) -> dict:
    """Inspecciona y devuelve la configuración de los 3 niveles activa en un proyecto."""
    html_file = _resolve_project_html(project_or_html)
    pkg_file = html_file.parent / "package.json"
    if pkg_file.exists():
        try:
            pkg_data = json.loads(pkg_file.read_text(encoding="utf-8"))
            if "videoDesign" in pkg_data:
                return pkg_data["videoDesign"]
        except (OSError, json.JSONDecodeError):
            pass

    content = html_file.read_text(encoding="utf-8")

    def extract_attr(attr: str, default: str) -> str:
        m = re.search(rf'{attr}="([^"]+)"', content)
        return m.group(1) if m else default

    return {
        "design": extract_attr("data-design", DEFAULT_DESIGN),
        "style": extract_attr("data-style", DEFAULT_THEME),
        "layout": extract_attr("data-layout", DEFAULT_LAYOUT),
        "motion": extract_attr("data-motion", DEFAULT_MOTION),
        "captionStyle": extract_attr("data-caption-style", DEFAULT_CAPTION_STYLE),
        "overrides": {},
    }


def apply_style_to_project(
    project_or_html: str | Path,
    theme_slug: str | None = None,
    caption_style_slug: str | None = None,
    design_slug: str | None = None,
    layout_slug: str | None = None,
    motion_slug: str | None = None,
    overrides: dict[str, str] | None = None,
    reset_overrides: bool = False,
) -> Path:
    """
    Aplica o actualiza cualquier combinación de Nivel 1, Nivel 2 o Nivel 3 sobre un proyecto,
    preservando la configuración previa de los niveles no modificados.
    """
    html_file = _resolve_project_html(project_or_html)
    pkg_file = html_file.parent / "package.json"
    pkg_data: dict = {}
    saved_state: dict = {}
    if pkg_file.exists():
        try:
            pkg_data = json.loads(pkg_file.read_text(encoding="utf-8"))
            saved_state = pkg_data.get("videoDesign", {})
        except (OSError, json.JSONDecodeError):
            pkg_data = {}

    design_changed = design_slug is not None and design_slug != saved_state.get("design")
    resolved_design_slug = design_slug or saved_state.get("design", DEFAULT_DESIGN)
    design_obj = get_design_system(resolved_design_slug)

    resolved_theme = theme_slug or (
        design_obj.default_theme
        if design_changed
        else saved_state.get("style", pkg_data.get("videoStyle", design_obj.default_theme))
    )
    resolved_layout = layout_slug or saved_state.get("layout", DEFAULT_LAYOUT)
    resolved_motion = motion_slug or (
        design_obj.default_motion
        if design_changed
        else saved_state.get("motion", design_obj.default_motion)
    )
    resolved_caption = caption_style_slug or (
        design_obj.default_caption_style
        if design_changed
        else saved_state.get(
            "captionStyle", pkg_data.get("captionStyle", design_obj.default_caption_style)
        )
    )

    merged_overrides: dict[str, str] = (
        {} if (reset_overrides or design_changed) else dict(saved_state.get("overrides", {}))
    )
    if overrides:
        merged_overrides.update(overrides)

    apply_style_to_html(
        html_file,
        theme_slug=resolved_theme,
        caption_style_slug=resolved_caption,
        design_slug=resolved_design_slug,
        layout_slug=resolved_layout,
        motion_slug=resolved_motion,
        overrides=merged_overrides,
    )

    if pkg_file.exists():
        try:
            pkg_data["videoStyle"] = resolved_theme
            pkg_data["captionStyle"] = resolved_caption
            pkg_data["videoDesign"] = {
                "design": resolved_design_slug,
                "style": resolved_theme,
                "layout": resolved_layout,
                "motion": resolved_motion,
                "captionStyle": resolved_caption,
                "overrides": merged_overrides,
            }
            pkg_file.write_text(json.dumps(pkg_data, indent=2) + "\n", encoding="utf-8")
        except OSError as exc:
            print(f"Advertencia: no se pudo persistir package.json: {exc}", file=sys.stderr)

    print(
        f"[Design] Aplicado Diseño='{resolved_design_slug}' | Tema='{resolved_theme}' | "
        f"Layout='{resolved_layout}' | Motion='{resolved_motion}' | "
        f"Captions='{resolved_caption}'"
        + (f" | Overrides={merged_overrides}" if merged_overrides else "")
        + f" -> {html_file.resolve()}"
    )
    return html_file


def print_catalog(as_json: bool = False) -> None:
    """Imprime el catálogo jerárquico de 3 niveles: Diseños Macro, Variantes Internas y Overrides."""
    if as_json:
        payload = {
            "designs": {k: asdict(v) for k, v in DESIGN_SYSTEMS.items()},
            "themes": {k: asdict(v) for k, v in THEMES.items()},
            "layouts": {k: asdict(v) for k, v in LAYOUT_VARIANTS.items()},
            "motions": {k: asdict(v) for k, v in MOTION_PROFILES.items()},
            "caption_styles": {k: asdict(v) for k, v in CAPTION_STYLES.items()},
            "overridable_keys": sorted(OVERRIDABLE_KEYS),
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    print("\n=== NIVEL 1: DISEÑOS MACRO (--design / -d) ===")
    for slug, d in DESIGN_SYSTEMS.items():
        default_tag = " [POR DEFECTO]" if slug == DEFAULT_DESIGN else ""
        print(f"  * {slug:<20} : {d.name}{default_tag}")
        print(
            f"    Preset nativo        : style={d.default_theme}, motion={d.default_motion}, captions={d.default_caption_style}"
        )
        print(f"    Descripción          : {d.description}")

    print("\n=== NIVEL 2A: TEMAS CROMÁTICOS Y TIPOGRÁFICOS (--style / -s) ===")
    for slug, t in THEMES.items():
        default_tag = " [POR DEFECTO]" if slug == DEFAULT_THEME else ""
        print(f"  * {slug:<20} : {t.name}{default_tag}")
        print(
            f"    Esquema              : {t.color_scheme} | Fondo: {t.bg} | Acento: {t.accent_primary}"
        )
        print(f"    Descripción          : {t.description}")

    print("\n=== NIVEL 2B: VARIANTES DE LAYOUT INTERNO (--layout) ===")
    for slug, ly in LAYOUT_VARIANTS.items():
        print(f"  * {slug:<20} : {ly.name} — {ly.description}")

    print("\n=== NIVEL 2C: PERFILES DE ANIMACIÓN GSAP (--motion) ===")
    for slug, mo in MOTION_PROFILES.items():
        print(f"  * {slug:<20} : {mo.name} — {mo.description}")

    print("\n=== NIVEL 2D: ESTILOS DE SUBTÍTULOS CINÉTICOS (--caption-style) ===")
    for slug, c in CAPTION_STYLES.items():
        print(f"  * {slug:<20} : {c.name} — {c.description}")

    print("\n=== NIVEL 3: PROPIEDADES AJUSTABLES POR DISEÑO (--set clave=valor) ===")
    print("  " + ", ".join(sorted(OVERRIDABLE_KEYS)))
    print()
