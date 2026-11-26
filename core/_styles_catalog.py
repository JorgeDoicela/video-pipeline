"""
Catálogo declarativo de tokens y variantes para el sistema de diseño en 3 niveles:
  - Nivel 1: Diseños Macro (DESIGN_SYSTEMS: 3 diseños canónicos)
  - Nivel 2: Temas cromáticos (THEMES: 3 paletas WCAG AA), Layouts (LAYOUT_VARIANTS: 3),
             Perfiles GSAP (MOTION_PROFILES: 3) y Subtítulos (CAPTION_STYLES: 1)
  - Nivel 3: Claves configurables mediante --set (OVERRIDABLE_KEYS)
"""

from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class VisualTheme:
    """Especificación inmutable de paleta y tokens cromáticos/tipográficos (WCAG AA >= 4.5:1)."""

    slug: str
    name: str
    description: str
    color_scheme: str
    bg: str
    bg_gradient: str
    surface: str
    surface_elevated: str
    border: str
    border_strong: str
    divider: str
    shadow: str
    panel_highlight: str
    panel_sheen: str
    headline_shadow: str
    text_primary: str
    text_secondary: str
    text_muted: str
    title_gradient: str
    font_display: str
    font_sans: str
    font_mono: str
    accent_primary: str
    accent_primary_soft: str
    accent_primary_glow: str
    accent_secondary: str
    accent_secondary_soft: str
    accent_tertiary: str
    accent_warning: str
    accent_danger: str
    node_fill: str
    cable_idle: str
    caption_bg: str
    caption_text: str
    caption_active: str
    caption_shadow: str
    caption_glow: str


@dataclass(frozen=True)
class DesignSystem:
    """
    Nivel 1 (Diseño Macro): Define de forma declarativa la geometría, modo de sombra,
    reglas CSS estructurales y opciones de Nivel 2 por defecto.
    """

    slug: str
    name: str
    description: str
    default_theme: str
    default_motion: str
    default_caption_style: str
    radius_lg: str
    radius_md: str
    radius_sm: str
    border_width: str
    panel_backdrop: str
    shadow_mode: str = "theme"  # "theme" | "none"
    structural_css: tuple[str, ...] = ()


@dataclass(frozen=True)
class LayoutVariant:
    """Nivel 2 (Opción interna de Layout): Controla proporciones, espaciados y alineaciones."""

    slug: str
    name: str
    description: str
    stage_padding: str
    stage_gap: str
    split_columns: str
    header_align: str
    lower_third_side: str
    caption_bottom: str
    caption_size: str


@dataclass(frozen=True)
class MotionProfile:
    """Nivel 2 (Opción interna de Animación GSAP): Controla curvas de aceleración y tiempos."""

    slug: str
    name: str
    description: str
    entry_ease: str
    panel_ease: str
    entry_duration: float
    stagger: float


@dataclass(frozen=True)
class CaptionStyle:
    """Nivel 2 (Opción interna de Subtítulos Cinéticos): Estilo visual y animación de palabras."""

    slug: str
    name: str
    description: str
    word_inactive_opacity: float
    active_css: tuple[str, ...]


DEFAULT_DESIGN = "cinematic"
DEFAULT_THEME = "dark_violet"
DEFAULT_LAYOUT = "standard"
DEFAULT_MOTION = "smooth"
DEFAULT_CAPTION_STYLE = "minimal_clean"

# =====================================================================
# NIVEL 1: CATÁLOGO DE DISEÑOS MACRO (3 DISEÑOS CANÓNICOS)
# =====================================================================
DESIGN_SYSTEMS: dict[str, DesignSystem] = {
    "cinematic": DesignSystem(
        slug="cinematic",
        name="Cinematic (Oscuro Premium)",
        description="Superficie obsidiana con iluminación volumétrica, tipografía display nítida, vidrio oscuro y bordes hairline simétricos.",
        default_theme="dark_violet",
        default_motion="smooth",
        default_caption_style="minimal_clean",
        radius_lg="28px",
        radius_md="18px",
        radius_sm="999px",
        border_width="1px",
        panel_backdrop="blur(24px)",
        shadow_mode="theme",
        structural_css=(
            "#root {",
            "  background: var(--bg-gradient), var(--bg);",
            "}",
            "#progress-bar {",
            "  height: 3px;",
            "  background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));",
            "  opacity: 0.85;",
            "}",
            "#atmosphere-rays {",
            "  background:",
            "    radial-gradient(ellipse 46% 38% at 32% 28%, var(--accent-primary-glow) 0%, transparent 68%),",
            "    radial-gradient(ellipse 42% 36% at 70% 66%, var(--accent-secondary-soft) 0%, transparent 70%);",
            "  filter: blur(72px);",
            "  opacity: 0.72;",
            "}",
            "#atmosphere-grid {",
            "  background-size: 64px 64px;",
            "  -webkit-mask-image: radial-gradient(ellipse 78% 66% at 50% 46%, rgba(0, 0, 0, 0.85) 0%, transparent 78%);",
            "  mask-image: radial-gradient(ellipse 78% 66% at 50% 46%, rgba(0, 0, 0, 0.85) 0%, transparent 78%);",
            "}",
            ".panel, #main-card {",
            "  background: var(--panel-sheen), var(--surface);",
            "  border: var(--border-width) solid var(--border);",
            "  box-shadow: var(--shadow), inset 0 1px 0 var(--panel-highlight);",
            "}",
            ".hook-badge {",
            "  font-size: 28px;",
            "  font-weight: 700;",
            "  letter-spacing: 0.22em;",
            "  color: var(--accent-primary);",
            "}",
            ".scene-headline {",
            "  font-size: 64px;",
            "  font-weight: 800;",
            "  line-height: 1.06;",
            "  letter-spacing: -0.035em;",
            "  text-transform: none;",
            "  max-width: 880px;",
            "  text-wrap: balance;",
            "  color: var(--text-primary);",
            "  text-shadow: var(--headline-shadow);",
            "}",
            '#root[data-width="1920"] .scene-headline {',
            "  font-size: 60px;",
            "  max-width: 1120px;",
            "}",
        ),
    ),
    "editorial": DesignSystem(
        slug="editorial",
        name="Editorial (Marfil y Latón)",
        description="Estética cálida y serena inspirada en marfil, lino arena y latón dorado con curvas suaves y luz difusa.",
        default_theme="paper_warm",
        default_motion="minimal",
        default_caption_style="minimal_clean",
        radius_lg="20px",
        radius_md="14px",
        radius_sm="8px",
        border_width="1px",
        panel_backdrop="blur(16px)",
        shadow_mode="theme",
        structural_css=(
            ".panel, #main-card {",
            "  background: var(--surface);",
            "  border: 1px solid var(--border);",
            "  box-shadow: var(--shadow);",
            "}",
            "#progress-bar, #brand-bar {",
            "  display: none !important;",
            "}",
            ".scene-headline {",
            "  font-size: 56px;",
            "  font-weight: 700;",
            "  text-transform: none;",
            "  letter-spacing: -0.025em;",
            "  max-width: 780px;",
            "  text-wrap: balance;",
            "  text-shadow: none;",
            "}",
            '#root[data-width="1920"] .scene-headline {',
            "  font-size: 54px;",
            "  max-width: 1020px;",
            "}",
            "h1, .main-title {",
            "  font-weight: 700;",
            "  letter-spacing: -0.025em;",
            "  text-wrap: balance;",
            "}",
        ),
    ),
    "clean": DesignSystem(
        slug="clean",
        name="Clean (Claro Minimalista)",
        description="Diseño luminoso con sombras suaves multicapa, tarjetas blancas puras y estética minimalista.",
        default_theme="clean_light",
        default_motion="smooth",
        default_caption_style="minimal_clean",
        radius_lg="24px",
        radius_md="16px",
        radius_sm="999px",
        border_width="1px",
        panel_backdrop="blur(24px)",
        shadow_mode="theme",
        structural_css=(
            ".panel, #main-card {",
            "  background: var(--surface);",
            "  border: 1px solid var(--border);",
            "  box-shadow: var(--shadow), inset 0 1px 0 var(--divider);",
            "  backdrop-filter: var(--panel-backdrop);",
            "  -webkit-backdrop-filter: var(--panel-backdrop);",
            "}",
        ),
    ),
}

# =====================================================================
# NIVEL 2A: CATÁLOGO DE TEMAS VISUALES (3 PALETAS WCAG AA)
# =====================================================================
THEMES: dict[str, VisualTheme] = {
    "dark_violet": VisualTheme(
        slug="dark_violet",
        name="Dark Violet (Obsidiana y Cristal)",
        description="Superficie obsidiana profunda con iluminación volumétrica violeta/esmeralda, vidrio oscuro y alto contraste.",
        color_scheme="dark",
        bg="#06060a",
        bg_gradient=(
            "radial-gradient(ellipse 85% 50% at 50% -10%, rgba(139, 92, 246, 0.26) 0%, transparent 62%), "
            "radial-gradient(ellipse 65% 45% at 85% 88%, rgba(52, 211, 153, 0.11) 0%, transparent 60%), "
            "radial-gradient(ellipse 60% 40% at 15% 70%, rgba(167, 139, 250, 0.08) 0%, transparent 55%)"
        ),
        surface="rgba(17, 17, 24, 0.86)",
        surface_elevated="rgba(255, 255, 255, 0.05)",
        border="rgba(255, 255, 255, 0.11)",
        border_strong="rgba(167, 139, 250, 0.48)",
        divider="rgba(255, 255, 255, 0.06)",
        shadow="0 32px 80px rgba(0, 0, 0, 0.78)",
        panel_highlight="rgba(255, 255, 255, 0.09)",
        panel_sheen="linear-gradient(180deg, rgba(255, 255, 255, 0.04) 0%, rgba(255, 255, 255, 0.01) 100%)",
        headline_shadow="0 4px 30px rgba(0, 0, 0, 0.65)",
        text_primary="#f8fafc",
        text_secondary="#cbd5e1",
        text_muted="#94a3b8",
        title_gradient="linear-gradient(135deg, #f8fafc 40%, #a78bfa 100%)",
        font_display="'Plus Jakarta Sans', 'Inter', sans-serif",
        font_sans="'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        font_mono="'JetBrains Mono', monospace",
        accent_primary="#a78bfa",
        accent_primary_soft="rgba(167, 139, 250, 0.15)",
        accent_primary_glow="rgba(139, 92, 246, 0.34)",
        accent_secondary="#34d399",
        accent_secondary_soft="rgba(52, 211, 153, 0.14)",
        accent_tertiary="#f472b6",
        accent_warning="#fbbf24",
        accent_danger="#fb7185",
        node_fill="#111118",
        cable_idle="#334155",
        caption_bg="transparent",
        caption_text="#f8fafc",
        caption_active="#a78bfa",
        caption_shadow="0 4px 20px rgba(0, 0, 0, 0.9)",
        caption_glow="0 0 16px #a78bfa",
    ),
    "paper_warm": VisualTheme(
        slug="paper_warm",
        name="Paper Warm (Marfil, Arena y Latón)",
        description="Fondo marfil luminoso con lino arena, tinta café carbón, acentos en latón dorado y carmesí terracota.",
        color_scheme="light",
        bg="#f5f1ea",
        bg_gradient="radial-gradient(circle at 50% 18%, rgba(186, 147, 89, 0.14) 0%, transparent 68%)",
        surface="rgba(255, 253, 249, 0.94)",
        surface_elevated="#ebe4d8",
        border="rgba(135, 92, 34, 0.20)",
        border_strong="rgba(135, 92, 34, 0.50)",
        divider="rgba(43, 35, 29, 0.10)",
        shadow="0 20px 48px rgba(43, 35, 29, 0.08)",
        panel_highlight="rgba(255, 255, 255, 0.65)",
        panel_sheen="linear-gradient(180deg, rgba(255, 255, 255, 0.45) 0%, rgba(255, 255, 255, 0.0) 100%)",
        headline_shadow="none",
        text_primary="#2b231d",
        text_secondary="#4a3f35",
        text_muted="#63564b",
        title_gradient="linear-gradient(135deg, #2b231d 42%, #875c22 100%)",
        font_display="'Poppins', 'Inter', sans-serif",
        font_sans="'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        font_mono="'JetBrains Mono', monospace",
        accent_primary="#875c22",
        accent_primary_soft="rgba(135, 92, 34, 0.10)",
        accent_primary_glow="rgba(186, 147, 89, 0.28)",
        accent_secondary="#8c2d19",
        accent_secondary_soft="rgba(140, 45, 25, 0.10)",
        accent_tertiary="#7c4d3a",
        accent_warning="#8f5410",
        accent_danger="#a32f2f",
        node_fill="#fffdf9",
        cable_idle="#b8aa96",
        caption_bg="transparent",
        caption_text="#2b231d",
        caption_active="#875c22",
        caption_shadow="0 2px 10px rgba(43, 35, 29, 0.12)",
        caption_glow="none",
    ),
    "clean_light": VisualTheme(
        slug="clean_light",
        name="Clean Light (Blanco Neutro)",
        description="Superficie blanca limpia de alto contraste con acentos azul cobalto y esmeralda.",
        color_scheme="light",
        bg="#f8fafc",
        bg_gradient="radial-gradient(circle at 50% 20%, rgba(3, 105, 161, 0.08) 0%, transparent 70%)",
        surface="rgba(255, 255, 255, 0.95)",
        surface_elevated="#f1f5f9",
        border="rgba(15, 23, 42, 0.15)",
        border_strong="rgba(3, 105, 161, 0.60)",
        divider="rgba(15, 23, 42, 0.10)",
        shadow="0 20px 45px rgba(15, 23, 42, 0.08)",
        panel_highlight="rgba(255, 255, 255, 0.85)",
        panel_sheen="linear-gradient(180deg, rgba(255, 255, 255, 0.70) 0%, rgba(255, 255, 255, 0.0) 100%)",
        headline_shadow="none",
        text_primary="#0f172a",
        text_secondary="#1e293b",
        text_muted="#475569",
        title_gradient="linear-gradient(135deg, #0f172a 40%, #334155 100%)",
        font_display="'Plus Jakarta Sans', 'Inter', sans-serif",
        font_sans="'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        font_mono="'JetBrains Mono', monospace",
        accent_primary="#0369a1",
        accent_primary_soft="rgba(3, 105, 161, 0.10)",
        accent_primary_glow="rgba(3, 105, 161, 0.25)",
        accent_secondary="#047857",
        accent_secondary_soft="rgba(4, 120, 87, 0.10)",
        accent_tertiary="#6d28d9",
        accent_warning="#b45309",
        accent_danger="#be123c",
        node_fill="#ffffff",
        cable_idle="#94a3b8",
        caption_bg="transparent",
        caption_text="#0f172a",
        caption_active="#0369a1",
        caption_shadow="0 2px 10px rgba(15, 23, 42, 0.12)",
        caption_glow="none",
    ),
}

# =====================================================================
# NIVEL 2B: VARIANTES DE LAYOUT INTERNO (--layout)
# =====================================================================
LAYOUT_VARIANTS: dict[str, LayoutVariant] = {
    "standard": LayoutVariant(
        slug="standard",
        name="Standard Balanced",
        description="Distribución equilibrada por defecto con dos columnas simétricas y lower-third a la izquierda.",
        stage_padding="80px 100px",
        stage_gap="40px",
        split_columns="1fr 1fr",
        header_align="left",
        lower_third_side="left",
        caption_bottom="220px",
        caption_size="52px",
    ),
    "asymmetric_focus": LayoutVariant(
        slug="asymmetric_focus",
        name="Asymmetric Focus (60/40 + Lower-Third Derecha)",
        description="Columna principal destacada (1.35fr / 0.85fr) y tarjeta lower-third posicionada a la derecha.",
        stage_padding="72px 96px",
        stage_gap="48px",
        split_columns="1.35fr 0.85fr",
        header_align="left",
        lower_third_side="right",
        caption_bottom="200px",
        caption_size="50px",
    ),
    "stacked": LayoutVariant(
        slug="stacked",
        name="Vertical Stacked (Filas Apiladas)",
        description="Convierte paneles divididos en bloques apilados verticalmente a ancho completo.",
        stage_padding="64px 120px",
        stage_gap="24px",
        split_columns="1fr",
        header_align="center",
        lower_third_side="left",
        caption_bottom="240px",
        caption_size="54px",
    ),
}

# =====================================================================
# NIVEL 2C: PERFILES DE MOVIMIENTO GSAP (--motion)
# =====================================================================
MOTION_PROFILES: dict[str, MotionProfile] = {
    "smooth": MotionProfile(
        slug="smooth",
        name="Smooth Editorial (Fluido)",
        description="Desplazamientos desacelerados limpios para tono cinematográfico, documental o corporativo.",
        entry_ease="power2.out",
        panel_ease="power3.out",
        entry_duration=0.95,
        stagger=0.18,
    ),
    "snappy": MotionProfile(
        slug="snappy",
        name="Snappy High-Energy (Rápido)",
        description="Transiciones rápidas y directas ideales para Shorts y Reels.",
        entry_ease="power4.out",
        panel_ease="back.out(2.0)",
        entry_duration=0.45,
        stagger=0.1,
    ),
    "minimal": MotionProfile(
        slug="minimal",
        name="Minimal Fade (Sobrio)",
        description="Apariciones rápidas y discretas con mínima traslación para lectura tranquila.",
        entry_ease="power1.out",
        panel_ease="power1.out",
        entry_duration=0.35,
        stagger=0.08,
    ),
}

# =====================================================================
# NIVEL 2E: ESTILO CANÓNICO DE SUBTÍTULOS CINÉTICOS (CERO PASTILLAS)
# =====================================================================
CAPTION_STYLES: dict[str, CaptionStyle] = {
    "minimal_clean": CaptionStyle(
        slug="minimal_clean",
        name="Minimal Clean (Editorial Sobrio)",
        description="Tipografía pura sin cajas ni pastillas; resalta la palabra activa mediante color, opacidad y sombra sutil.",
        word_inactive_opacity=0.40,
        active_css=(
            "opacity: 1;",
            "color: var(--caption-active);",
            "text-shadow: var(--caption-shadow);",
        ),
    ),
}

# Propiedades permitidas en Nivel 3 (--set clave=valor)
OVERRIDABLE_KEYS: set[str] = {
    "bg",
    "bg_gradient",
    "surface",
    "surface_elevated",
    "border",
    "border_strong",
    "divider",
    "shadow",
    "panel_highlight",
    "panel_sheen",
    "headline_shadow",
    "text_primary",
    "text_secondary",
    "text_muted",
    "title_gradient",
    "font_display",
    "font_sans",
    "font_mono",
    "accent_primary",
    "accent_primary_soft",
    "accent_primary_glow",
    "accent_secondary",
    "accent_secondary_soft",
    "accent_tertiary",
    "accent_warning",
    "accent_danger",
    "node_fill",
    "cable_idle",
    "caption_bg",
    "caption_text",
    "caption_active",
    "caption_shadow",
    "caption_glow",
    "radius_lg",
    "radius_md",
    "radius_sm",
    "border_width",
    "panel_backdrop",
    "stage_padding",
    "stage_gap",
    "split_columns",
    "header_align",
    "lower_third_side",
    "caption_bottom",
    "caption_size",
}


def _get_entry(mapping: dict[str, T], slug: str, label: str) -> T:
    if slug not in mapping:
        available = ", ".join(mapping.keys())
        raise ValueError(f"{label} '{slug}' no existe. Opciones válidas: {available}")
    return mapping[slug]


def get_design_system(slug: str) -> DesignSystem:
    return _get_entry(DESIGN_SYSTEMS, slug, "El diseño macro")


def get_theme(slug: str) -> VisualTheme:
    return _get_entry(THEMES, slug, "El estilo visual")


def get_layout_variant(slug: str) -> LayoutVariant:
    return _get_entry(LAYOUT_VARIANTS, slug, "La variante de layout")


def get_motion_profile(slug: str) -> MotionProfile:
    return _get_entry(MOTION_PROFILES, slug, "El perfil de movimiento")


def get_caption_style(slug: str) -> CaptionStyle:
    return _get_entry(CAPTION_STYLES, slug, "El estilo de subtítulos")
