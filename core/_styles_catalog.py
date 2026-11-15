"""
Catálogo declarativo de tokens y variantes para el sistema de diseño en 3 niveles:
  - Nivel 1: Diseños Macro (DESIGN_SYSTEMS: 4 estilos canónicos)
  - Nivel 2: Temas cromáticos (THEMES: 4 paletas WCAG AA), Layouts (LAYOUT_VARIANTS: 3),
             Marcos (CHROME_VARIANTS: 4), Perfiles GSAP (MOTION_PROFILES: 3) y Subtítulos (CAPTION_STYLES: 2)
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
    text_primary: str
    text_secondary: str
    text_muted: str
    title_gradient: str
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
    default_chrome: str
    default_motion: str
    default_caption_style: str
    radius_lg: str
    radius_md: str
    radius_sm: str
    border_width: str
    panel_backdrop: str
    badge_radius: str
    shadow_mode: str = "theme"  # "theme" | "hard" | "none"
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
class ChromeVariant:
    """Nivel 2 (Opción interna de Marco/Ventana): Controla la decoración de cabeceras de tarjetas."""

    slug: str
    name: str
    description: str
    css_rules: tuple[str, ...] = ()


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
DEFAULT_CHROME = "auto"
DEFAULT_MOTION = "smooth"
DEFAULT_CAPTION_STYLE = "minimal_clean"

# =====================================================================
# NIVEL 1: CATÁLOGO DE DISEÑOS MACRO (4 DISEÑOS CANÓNICOS)
# =====================================================================
DESIGN_SYSTEMS: dict[str, DesignSystem] = {
    "cinematic": DesignSystem(
        slug="cinematic",
        name="Cinematic (Oscuro Premium)",
        description="Superficie oscura con curvas amplias, desenfoque suave, bordes simétricos y alto impacto visual.",
        default_theme="dark_violet",
        default_chrome="hidden",
        default_motion="smooth",
        default_caption_style="minimal_clean",
        radius_lg="28px",
        radius_md="16px",
        radius_sm="999px",
        border_width="1px",
        panel_backdrop="blur(24px)",
        badge_radius="0px",
        shadow_mode="theme",
        structural_css=(),
    ),
    "editorial": DesignSystem(
        slug="editorial",
        name="Editorial (Cálido / Pergamino)",
        description="Formato clásico de lectura y ensayo con fondo cálido antirreflejo, filetes sobrios y alto contraste.",
        default_theme="paper_warm",
        default_chrome="hidden",
        default_motion="minimal",
        default_caption_style="minimal_clean",
        radius_lg="4px",
        radius_md="4px",
        radius_sm="2px",
        border_width="1px",
        panel_backdrop="none",
        badge_radius="0px",
        shadow_mode="none",
        structural_css=(
            ".panel, #main-card {",
            "  border: 2px solid var(--text-primary);",
            "}",
            "header {",
            "  border-top: 3px solid var(--text-primary);",
            "  border-bottom: 1px solid var(--text-primary);",
            "  padding: 14px 0;",
            "}",
        ),
    ),
    "clean": DesignSystem(
        slug="clean",
        name="Clean (Claro Minimalista)",
        description="Diseño luminoso con sombras suaves multicapa, tarjetas blancas puras y estética minimalista.",
        default_theme="clean_light",
        default_chrome="hidden",
        default_motion="smooth",
        default_caption_style="minimal_clean",
        radius_lg="24px",
        radius_md="16px",
        radius_sm="999px",
        border_width="1px",
        panel_backdrop="blur(24px)",
        badge_radius="0px",
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
    "terminal": DesignSystem(
        slug="terminal",
        name="Terminal (Brutalismo Técnico TUI)",
        description="Estética de consola técnica con esquinas a 90 grados, bordes marcados y sombra dura desplazada.",
        default_theme="terminal_green",
        default_chrome="terminal_bar",
        default_motion="snappy",
        default_caption_style="minimal_clean",
        radius_lg="0px",
        radius_md="0px",
        radius_sm="0px",
        border_width="2px",
        panel_backdrop="none",
        badge_radius="0px",
        shadow_mode="hard",
        structural_css=(
            ".panel, #main-card, .lower-third {",
            "  border: 2px solid var(--accent-primary);",
            "  box-shadow: var(--shadow);",
            "}",
            ".badge, .hook-badge {",
            "  background: var(--accent-primary);",
            "  color: var(--bg);",
            "  border: 2px solid var(--accent-primary);",
            "}",
        ),
    ),
}

# =====================================================================
# NIVEL 2A: CATÁLOGO DE TEMAS VISUALES (4 PALETAS WCAG AA)
# =====================================================================
THEMES: dict[str, VisualTheme] = {
    "dark_violet": VisualTheme(
        slug="dark_violet",
        name="Dark Violet (Obsidiana y Cristal)",
        description="Superficie obsidiana oscura con acentos violeta, esmeralda y alto contraste.",
        color_scheme="dark",
        bg="#09090b",
        bg_gradient="radial-gradient(circle at 50% 20%, rgba(167, 139, 250, 0.14) 0%, transparent 70%)",
        surface="rgba(24, 24, 27, 0.90)",
        surface_elevated="rgba(255, 255, 255, 0.04)",
        border="rgba(167, 139, 250, 0.26)",
        border_strong="rgba(167, 139, 250, 0.65)",
        divider="rgba(255, 255, 255, 0.08)",
        shadow="0 20px 50px rgba(0, 0, 0, 0.75)",
        text_primary="#fafafa",
        text_secondary="#e4e4e7",
        text_muted="#a1a1aa",
        title_gradient="linear-gradient(135deg, #fafafa 40%, #a78bfa 100%)",
        font_sans="-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif",
        font_mono="'JetBrains Mono', monospace",
        accent_primary="#a78bfa",
        accent_primary_soft="rgba(167, 139, 250, 0.14)",
        accent_primary_glow="rgba(167, 139, 250, 0.35)",
        accent_secondary="#34d399",
        accent_secondary_soft="rgba(52, 211, 153, 0.14)",
        accent_tertiary="#f472b6",
        accent_warning="#fbbf24",
        accent_danger="#fb7185",
        node_fill="#18181b",
        cable_idle="#3f3f46",
        caption_bg="transparent",
        caption_text="#fafafa",
        caption_active="#a78bfa",
        caption_shadow="0 4px 20px rgba(0, 0, 0, 0.9)",
        caption_glow="0 0 16px #a78bfa",
    ),
    "paper_warm": VisualTheme(
        slug="paper_warm",
        name="Paper Warm (Pergamino Cálido)",
        description="Fondo crema cálido de baja fatiga visual con tinta azul petróleo y acentos cobalto.",
        color_scheme="light",
        bg="#fdf6e3",
        bg_gradient="radial-gradient(circle at 50% 20%, rgba(3, 105, 161, 0.06) 0%, transparent 70%)",
        surface="rgba(255, 252, 240, 0.96)",
        surface_elevated="#eee8d5",
        border="rgba(7, 54, 66, 0.18)",
        border_strong="rgba(3, 105, 161, 0.60)",
        divider="rgba(7, 54, 66, 0.12)",
        shadow="0 16px 40px rgba(7, 54, 66, 0.08)",
        text_primary="#073642",
        text_secondary="#1e293b",
        text_muted="#475569",
        title_gradient="linear-gradient(135deg, #073642 40%, #0369a1 100%)",
        font_sans="-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Georgia, serif",
        font_mono="'JetBrains Mono', monospace",
        accent_primary="#0369a1",
        accent_primary_soft="rgba(3, 105, 161, 0.10)",
        accent_primary_glow="rgba(3, 105, 161, 0.25)",
        accent_secondary="#047857",
        accent_secondary_soft="rgba(4, 120, 87, 0.10)",
        accent_tertiary="#6d28d9",
        accent_warning="#b45309",
        accent_danger="#be123c",
        node_fill="#fffdf7",
        cable_idle="#94a3b8",
        caption_bg="rgba(253, 246, 227, 0.94)",
        caption_text="#073642",
        caption_active="#0369a1",
        caption_shadow="0 2px 8px rgba(7, 54, 66, 0.12)",
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
        text_primary="#0f172a",
        text_secondary="#1e293b",
        text_muted="#475569",
        title_gradient="linear-gradient(135deg, #0f172a 40%, #334155 100%)",
        font_sans="-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif",
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
        caption_bg="rgba(255, 255, 255, 0.92)",
        caption_text="#0f172a",
        caption_active="#0369a1",
        caption_shadow="0 2px 10px rgba(15, 23, 42, 0.12)",
        caption_glow="none",
    ),
    "terminal_green": VisualTheme(
        slug="terminal_green",
        name="Terminal Green (Consola CRT)",
        description="Estética de consola de bajo nivel con negro profundo, verde fósforo y ámbar técnico.",
        color_scheme="dark",
        bg="#050a06",
        bg_gradient="radial-gradient(circle at 50% 20%, rgba(34, 197, 94, 0.12) 0%, transparent 70%)",
        surface="rgba(9, 20, 12, 0.92)",
        surface_elevated="rgba(34, 197, 94, 0.05)",
        border="rgba(34, 197, 94, 0.28)",
        border_strong="rgba(34, 197, 94, 0.70)",
        divider="rgba(34, 197, 94, 0.14)",
        shadow="0 20px 50px rgba(0, 0, 0, 0.80)",
        text_primary="#ecfdf5",
        text_secondary="#a7f3d0",
        text_muted="#6ee7b7",
        title_gradient="linear-gradient(135deg, #ecfdf5 35%, #22c55e 100%)",
        font_sans="'JetBrains Mono', monospace",
        font_mono="'JetBrains Mono', monospace",
        accent_primary="#22c55e",
        accent_primary_soft="rgba(34, 197, 94, 0.14)",
        accent_primary_glow="rgba(34, 197, 94, 0.35)",
        accent_secondary="#f59e0b",
        accent_secondary_soft="rgba(245, 158, 11, 0.14)",
        accent_tertiary="#38bdf8",
        accent_warning="#facc15",
        accent_danger="#f43f5e",
        node_fill="#09140c",
        cable_idle="#14532d",
        caption_bg="transparent",
        caption_text="#ecfdf5",
        caption_active="#22c55e",
        caption_shadow="0 4px 20px rgba(0, 0, 0, 0.95)",
        caption_glow="0 0 16px #22c55e",
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
# NIVEL 2C: VARIANTES DE MARCO / VENTANA (--chrome)
# =====================================================================
CHROME_VARIANTS: dict[str, ChromeVariant] = {
    "auto": ChromeVariant(
        slug="auto",
        name="Auto (Heredado del Diseño Macro)",
        description="Utiliza el marco de ventana nativo del Diseño Macro seleccionado.",
    ),
    "hidden": ChromeVariant(
        slug="hidden",
        name="Clean Card (Sin Barra de Ventana)",
        description="Oculta por completo la barra superior de ventana dejando tarjetas puras.",
        css_rules=(
            ".window-header {",
            "  display: none;",
            "}",
        ),
    ),
    "minimal_line": ChromeVariant(
        slug="minimal_line",
        name="Minimal Editorial Line",
        description="Oculta los botones de ventana y deja únicamente la barra tipográfica limpia.",
        css_rules=(
            ".window-dots {",
            "  display: none;",
            "}",
        ),
    ),
    "terminal_bar": ChromeVariant(
        slug="terminal_bar",
        name="Terminal TUI Block",
        description="Controles cuadrados angulares tipo terminal técnica con borde superior marcado.",
        css_rules=(
            ".dot {",
            "  border-radius: 0px;",
            "  width: 12px;",
            "  height: 12px;",
            "}",
            ".window-header {",
            "  border-bottom: 2px solid var(--accent-primary);",
            "}",
        ),
    ),
}

# =====================================================================
# NIVEL 2D: PERFILES DE MOVIMIENTO GSAP (--motion)
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
        description="Transiciones rápidas y directas ideales para Shorts, Reels y terminal.",
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
# NIVEL 2E: ESTILOS DE SUBTÍTULOS CINÉTICOS (2 ESTILOS GANADORES)
# =====================================================================
CAPTION_STYLES: dict[str, CaptionStyle] = {
    "highlight_pill": CaptionStyle(
        slug="highlight_pill",
        name="Highlight Clean (Texto Activo)",
        description="Resalta la palabra pronunciada mediante iluminación limpia de color y resplandor, sin cajas envolventes.",
        word_inactive_opacity=0.45,
        active_css=(
            "opacity: 1;",
            "color: var(--caption-active);",
            "text-shadow: var(--caption-glow);",
        ),
    ),
    "minimal_clean": CaptionStyle(
        slug="minimal_clean",
        name="Minimal Clean (Editorial Sobrio)",
        description="Transición limpia de opacidad y color sin adornos, orientada a lecturas bíblicas y ensayos.",
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
    "surface",
    "surface_elevated",
    "border",
    "border_strong",
    "divider",
    "shadow",
    "text_primary",
    "text_secondary",
    "text_muted",
    "font_sans",
    "font_mono",
    "accent_primary",
    "accent_secondary",
    "accent_tertiary",
    "accent_warning",
    "accent_danger",
    "node_fill",
    "cable_idle",
    "caption_bg",
    "caption_text",
    "caption_active",
    "radius_lg",
    "radius_md",
    "radius_sm",
    "border_width",
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


def get_chrome_variant(slug: str) -> ChromeVariant:
    return _get_entry(CHROME_VARIANTS, slug, "La variante de marco")


def get_motion_profile(slug: str) -> MotionProfile:
    return _get_entry(MOTION_PROFILES, slug, "El perfil de movimiento")


def get_caption_style(slug: str) -> CaptionStyle:
    return _get_entry(CAPTION_STYLES, slug, "El estilo de subtítulos")
