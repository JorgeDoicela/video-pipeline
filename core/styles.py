#!/usr/bin/env python3
"""
Motor jerárquico de sistemas de diseño en 3 niveles para el pipeline de video:
  1. Nivel Macro (DesignSystem / --design): 6 Diseños grandes estructuralmente distintos
     (cyber_glass, swiss_editorial, brutalist_terminal, cinematic_studio, bento_grid, academic_paper).
  2. Nivel Medio (Variantes internas / --style, --layout, --chrome, --motion, --caption-style):
     8 temas cromáticos WCAG AA, 4 layouts, 5 marcos de ventana, 4 perfiles GSAP y 6 estilos de subtítulos.
  3. Nivel Micro (Overrides granulares / --set clave=valor):
     Ajustes puntuales sobre tokens o propiedades de un único diseño/proyecto sin afectar los demás.
"""

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


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
    Nivel 1 (Diseño Macro): Define la arquitectura geométrica, lenguaje de bordes,
    sombras estructurales, decoración de contenedores y perfil de movimiento por defecto.
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
    use_hard_shadow: bool
    use_editorial_rules: bool
    use_accent_left_bar: bool
    use_bento_surface: bool = False
    use_double_academic_border: bool = False
    use_frosted_glass_physics: bool = False
    use_clean_studio_surface: bool = False


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
    use_pill_background: bool
    use_scale_pop: bool
    use_glow: bool
    use_underline: bool = False
    use_box_invert: bool = False


DEFAULT_DESIGN = "cyber_glass"
DEFAULT_THEME = "cyber_dark"
DEFAULT_LAYOUT = "standard"
DEFAULT_CHROME = "auto"
DEFAULT_MOTION = "dynamic"
DEFAULT_CAPTION_STYLE = "karaoke_glow"

# =====================================================================
# NIVEL 1: CATÁLOGO DE DISEÑOS MACRO (6 DISEÑOS GRANDES)
# =====================================================================
DESIGN_SYSTEMS: dict[str, DesignSystem] = {
    "cyber_glass": DesignSystem(
        slug="cyber_glass",
        name="Cyber Glass (Glassmorphism & Frosted Glass)",
        description="Diseño con paneles translúcidos con bisel especular, desenfoque de cristal saturado y controles tipo macOS.",
        default_theme="cyber_dark",
        default_chrome="macos_dots",
        default_motion="dynamic",
        default_caption_style="karaoke_glow",
        radius_lg="24px",
        radius_md="14px",
        radius_sm="8px",
        border_width="1px",
        panel_backdrop="blur(32px) saturate(190%)",
        badge_radius="999px",
        use_hard_shadow=False,
        use_editorial_rules=False,
        use_accent_left_bar=False,
        use_frosted_glass_physics=True,
    ),
    "clean_studio": DesignSystem(
        slug="clean_studio",
        name="Clean Studio (Apple Keynote & Stripe Light)",
        description="Diseño corporativo luminoso de alta gama con sombras multicapa, tarjetas blancas puras y acentos vivos.",
        default_theme="minimal_light",
        default_chrome="hidden",
        default_motion="smooth",
        default_caption_style="highlight_pill",
        radius_lg="28px",
        radius_md="16px",
        radius_sm="999px",
        border_width="1px",
        panel_backdrop="blur(20px)",
        badge_radius="999px",
        use_hard_shadow=False,
        use_editorial_rules=False,
        use_accent_left_bar=False,
        use_clean_studio_surface=True,
    ),
    "swiss_editorial": DesignSystem(
        slug="swiss_editorial",
        name="Swiss Editorial (Arquitectura & Revista Técnica)",
        description="Diseño editorial suizo de retícula rigurosa, bordes rectos, filetes superiores gruesos y cero adornos.",
        default_theme="minimal_light",
        default_chrome="minimal_line",
        default_motion="smooth",
        default_caption_style="minimal_clean",
        radius_lg="2px",
        radius_md="2px",
        radius_sm="2px",
        border_width="1px",
        panel_backdrop="none",
        badge_radius="2px",
        use_hard_shadow=False,
        use_editorial_rules=True,
        use_accent_left_bar=False,
    ),
    "brutalist_terminal": DesignSystem(
        slug="brutalist_terminal",
        name="Brutalist Terminal (Ingeniería TUI & Sombra Dura)",
        description="Diseño neo-brutalista con esquinas a 90 grados, bordes gruesos y sombra sólida desplazada.",
        default_theme="terminal_hacker",
        default_chrome="terminal_bar",
        default_motion="snappy",
        default_caption_style="highlight_pill",
        radius_lg="0px",
        radius_md="0px",
        radius_sm="0px",
        border_width="2px",
        panel_backdrop="none",
        badge_radius="0px",
        use_hard_shadow=True,
        use_editorial_rules=False,
        use_accent_left_bar=False,
    ),
    "cinematic_studio": DesignSystem(
        slug="cinematic_studio",
        name="Cinematic Studio (Cápsula Ejecutiva)",
        description="Diseño de estudio con curvas amplias, tarjetas flotantes con franja lateral de acento y transición suave.",
        default_theme="linear_violet",
        default_chrome="hidden",
        default_motion="smooth",
        default_caption_style="pop_scale",
        radius_lg="28px",
        radius_md="16px",
        radius_sm="999px",
        border_width="1px",
        panel_backdrop="blur(24px)",
        badge_radius="999px",
        use_hard_shadow=False,
        use_editorial_rules=False,
        use_accent_left_bar=True,
    ),
    "bento_grid": DesignSystem(
        slug="bento_grid",
        name="Bento Grid (Modular Moderno)",
        description="Celdas modulares estilo Bento con esquinas suaves (24px), borde interno sutil y cabeceras limpias.",
        default_theme="dracula_pro",
        default_chrome="minimal_line",
        default_motion="dynamic",
        default_caption_style="underline_bar",
        radius_lg="24px",
        radius_md="16px",
        radius_sm="10px",
        border_width="1px",
        panel_backdrop="blur(16px)",
        badge_radius="999px",
        use_hard_shadow=False,
        use_editorial_rules=False,
        use_accent_left_bar=False,
        use_bento_surface=True,
    ),
    "academic_paper": DesignSystem(
        slug="academic_paper",
        name="Academic Paper (Publicación Científica / IEEE)",
        description="Formato de artículo académico y documentación formal con bordes clásicos, fondo cálido y tono sobrio.",
        default_theme="solarized_sand",
        default_chrome="hidden",
        default_motion="minimal",
        default_caption_style="minimal_clean",
        radius_lg="4px",
        radius_md="4px",
        radius_sm="2px",
        border_width="1px",
        panel_backdrop="none",
        badge_radius="2px",
        use_hard_shadow=False,
        use_editorial_rules=False,
        use_accent_left_bar=False,
        use_double_academic_border=True,
    ),
}

# =====================================================================
# NIVEL 2A: CATÁLOGO DE TEMAS VISUALES (8 PALETAS WCAG AA)
# =====================================================================
THEMES: dict[str, VisualTheme] = {
    "cyber_dark": VisualTheme(
        slug="cyber_dark",
        name="Cyber Dark (Slate & Cyan)",
        description="Estética oscura original del proyecto con paneles cristalinos Slate, acentos Cyan y Emerald.",
        color_scheme="dark",
        bg="#070b14",
        bg_gradient="radial-gradient(circle at 50% 20%, rgba(56, 189, 248, 0.12) 0%, transparent 70%)",
        surface="rgba(16, 23, 42, 0.88)",
        surface_elevated="rgba(255, 255, 255, 0.03)",
        border="rgba(56, 189, 248, 0.25)",
        border_strong="rgba(56, 189, 248, 0.65)",
        divider="rgba(255, 255, 255, 0.08)",
        shadow="0 20px 50px rgba(0, 0, 0, 0.65)",
        text_primary="#f8fafc",
        text_secondary="#cbd5e1",
        text_muted="#94a3b8",
        title_gradient="linear-gradient(135deg, #ffffff 40%, #94a3b8 100%)",
        font_sans="-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif",
        font_mono="'JetBrains Mono', monospace",
        accent_primary="#38bdf8",
        accent_primary_soft="rgba(56, 189, 248, 0.12)",
        accent_primary_glow="rgba(56, 189, 248, 0.35)",
        accent_secondary="#10b981",
        accent_secondary_soft="rgba(16, 185, 129, 0.12)",
        accent_tertiary="#c084fc",
        accent_warning="#fbbf24",
        accent_danger="#f43f5e",
        node_fill="#10172a",
        cable_idle="#1e293b",
        caption_bg="transparent",
        caption_text="#f8fafc",
        caption_active="#38bdf8",
        caption_shadow="0 4px 20px rgba(0, 0, 0, 0.9)",
        caption_glow="0 0 16px #38bdf8",
    ),
    "minimal_light": VisualTheme(
        slug="minimal_light",
        name="Minimal Light (Editorial Técnico)",
        description="Diseño editorial claro de alto contraste con superficie blanca limpia y acentos azul e índigo.",
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
    "terminal_hacker": VisualTheme(
        slug="terminal_hacker",
        name="Terminal Hacker (CRT Phosphor)",
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
    "linear_violet": VisualTheme(
        slug="linear_violet",
        name="Linear Violet (Obsidiana & Cristal)",
        description="Superficie obsidiana monocromática con acentos violeta, esmeralda y cristal esmerilado.",
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
    "blueprint_cad": VisualTheme(
        slug="blueprint_cad",
        name="Blueprint CAD (Ingeniería Naval)",
        description="Plano de arquitectura de sistemas en azul profundo con trazos turquesa y celeste.",
        color_scheme="dark",
        bg="#0a192f",
        bg_gradient="radial-gradient(circle at 50% 20%, rgba(100, 255, 218, 0.10) 0%, transparent 70%)",
        surface="rgba(17, 34, 64, 0.92)",
        surface_elevated="rgba(100, 255, 218, 0.05)",
        border="rgba(100, 255, 218, 0.28)",
        border_strong="rgba(100, 255, 218, 0.70)",
        divider="rgba(230, 241, 255, 0.10)",
        shadow="0 20px 50px rgba(2, 12, 27, 0.75)",
        text_primary="#e6f1ff",
        text_secondary="#ccd6f6",
        text_muted="#94a3b8",
        title_gradient="linear-gradient(135deg, #e6f1ff 40%, #64ffda 100%)",
        font_sans="-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif",
        font_mono="'JetBrains Mono', monospace",
        accent_primary="#64ffda",
        accent_primary_soft="rgba(100, 255, 218, 0.12)",
        accent_primary_glow="rgba(100, 255, 218, 0.35)",
        accent_secondary="#38bdf8",
        accent_secondary_soft="rgba(56, 189, 248, 0.12)",
        accent_tertiary="#c084fc",
        accent_warning="#ffd166",
        accent_danger="#ff6b6b",
        node_fill="#112240",
        cable_idle="#233554",
        caption_bg="transparent",
        caption_text="#e6f1ff",
        caption_active="#64ffda",
        caption_shadow="0 4px 20px rgba(2, 12, 27, 0.95)",
        caption_glow="0 0 16px #64ffda",
    ),
    "dracula_pro": VisualTheme(
        slug="dracula_pro",
        name="Dracula Pro (IDE Dark Syntax)",
        description="Paleta de alto contraste inspirada en editores de código con cian eléctrico, verde menta y rosa.",
        color_scheme="dark",
        bg="#13151f",
        bg_gradient="radial-gradient(circle at 50% 20%, rgba(139, 233, 253, 0.10) 0%, transparent 70%)",
        surface="rgba(30, 32, 48, 0.92)",
        surface_elevated="rgba(255, 255, 255, 0.04)",
        border="rgba(139, 233, 253, 0.25)",
        border_strong="rgba(139, 233, 253, 0.65)",
        divider="rgba(248, 248, 242, 0.10)",
        shadow="0 20px 50px rgba(0, 0, 0, 0.70)",
        text_primary="#f8f8f2",
        text_secondary="#e2e8f0",
        text_muted="#94a3b8",
        title_gradient="linear-gradient(135deg, #f8f8f2 35%, #8be9fd 100%)",
        font_sans="-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif",
        font_mono="'JetBrains Mono', monospace",
        accent_primary="#8be9fd",
        accent_primary_soft="rgba(139, 233, 253, 0.12)",
        accent_primary_glow="rgba(139, 233, 253, 0.35)",
        accent_secondary="#50fa7b",
        accent_secondary_soft="rgba(80, 250, 123, 0.12)",
        accent_tertiary="#ff79c6",
        accent_warning="#f1fa8c",
        accent_danger="#ff5555",
        node_fill="#1e2030",
        cable_idle="#44475a",
        caption_bg="transparent",
        caption_text="#f8f8f2",
        caption_active="#50fa7b",
        caption_shadow="0 4px 20px rgba(0, 0, 0, 0.92)",
        caption_glow="0 0 16px #50fa7b",
    ),
    "solarized_sand": VisualTheme(
        slug="solarized_sand",
        name="Solarized Sand (Paper Cálido & Lectura)",
        description="Fondo crema cálido de baja fatiga visual con tinta azul petróleo y acentos cobalto y esmeralda.",
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
    "crimson_ops": VisualTheme(
        slug="crimson_ops",
        name="Crimson Ops (SecOps & Red Team)",
        description="Estética de ciberseguridad ofensiva y telemetría crítica en carbón oscuro con carmesí y ámbar.",
        color_scheme="dark",
        bg="#0c0a09",
        bg_gradient="radial-gradient(circle at 50% 20%, rgba(244, 63, 94, 0.12) 0%, transparent 70%)",
        surface="rgba(28, 25, 23, 0.90)",
        surface_elevated="rgba(244, 63, 94, 0.05)",
        border="rgba(244, 63, 94, 0.28)",
        border_strong="rgba(244, 63, 94, 0.65)",
        divider="rgba(255, 255, 255, 0.08)",
        shadow="0 20px 50px rgba(0, 0, 0, 0.80)",
        text_primary="#fafaf9",
        text_secondary="#e7e5e4",
        text_muted="#a8a29e",
        title_gradient="linear-gradient(135deg, #fafaf9 35%, #fb7185 100%)",
        font_sans="-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif",
        font_mono="'JetBrains Mono', monospace",
        accent_primary="#fb7185",
        accent_primary_soft="rgba(251, 113, 133, 0.14)",
        accent_primary_glow="rgba(251, 113, 133, 0.35)",
        accent_secondary="#fbbf24",
        accent_secondary_soft="rgba(251, 191, 36, 0.14)",
        accent_tertiary="#38bdf8",
        accent_warning="#f59e0b",
        accent_danger="#f43f5e",
        node_fill="#1c1917",
        cable_idle="#44403c",
        caption_bg="transparent",
        caption_text="#fafaf9",
        caption_active="#fb7185",
        caption_shadow="0 4px 20px rgba(0, 0, 0, 0.95)",
        caption_glow="0 0 16px #fb7185",
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
    "compact_hud": LayoutVariant(
        slug="compact_hud",
        name="Compact HUD (Márgenes Amplios)",
        description="Escenario compacto con márgenes respirables tipo HUD y subtítulos inferiores estilizados.",
        stage_padding="96px 140px",
        stage_gap="32px",
        split_columns="1fr 1fr",
        header_align="center",
        lower_third_side="right",
        caption_bottom="180px",
        caption_size="46px",
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
    "macos_dots": ChromeVariant(
        slug="macos_dots",
        name="macOS Traffic Dots",
        description="Barra de ventana con tres controles circulares (rojo, ámbar, verde).",
    ),
    "terminal_bar": ChromeVariant(
        slug="terminal_bar",
        name="Terminal TUI Block",
        description="Controles cuadrados angulares tipo terminal técnica con borde superior marcado.",
    ),
    "minimal_line": ChromeVariant(
        slug="minimal_line",
        name="Minimal Editorial Line",
        description="Oculta los botones de ventana y deja únicamente la barra tipográfica limpia.",
    ),
    "hidden": ChromeVariant(
        slug="hidden",
        name="Clean Card (Sin Barra de Ventana)",
        description="Oculta por completo la barra superior de ventana dejando tarjetas puras.",
    ),
}

# =====================================================================
# NIVEL 2D: PERFILES DE MOVIMIENTO GSAP (--motion)
# =====================================================================
MOTION_PROFILES: dict[str, MotionProfile] = {
    "dynamic": MotionProfile(
        slug="dynamic",
        name="Dynamic Back-Out (Estándar)",
        description="Entrada con rebote técnico controlado (back.out) y escalonamiento medio.",
        entry_ease="power3.out",
        panel_ease="back.out(1.5)",
        entry_duration=0.8,
        stagger=0.2,
    ),
    "smooth": MotionProfile(
        slug="smooth",
        name="Smooth Editorial (Fluido sin Rebote)",
        description="Desplazamientos desacelerados limpios (expo.out / power2.out) para tono documental o ejecutivo.",
        entry_ease="power2.out",
        panel_ease="power3.out",
        entry_duration=0.95,
        stagger=0.18,
    ),
    "snappy": MotionProfile(
        slug="snappy",
        name="Snappy High-Energy (Rápido)",
        description="Transiciones rápidas y directas (power4.out) ideales para Shorts, Reels y estilo brutalista.",
        entry_ease="power4.out",
        panel_ease="back.out(2.0)",
        entry_duration=0.45,
        stagger=0.1,
    ),
    "minimal": MotionProfile(
        slug="minimal",
        name="Minimal Fade (Sobrio)",
        description="Apariciones rápidas y discretas con mínima traslación.",
        entry_ease="power1.out",
        panel_ease="power1.out",
        entry_duration=0.35,
        stagger=0.08,
    ),
}

# =====================================================================
# NIVEL 2E: ESTILOS DE SUBTÍTULOS CINÉTICOS (6 ESTILOS)
# =====================================================================
CAPTION_STYLES: dict[str, CaptionStyle] = {
    "karaoke_glow": CaptionStyle(
        slug="karaoke_glow",
        name="Karaoke Glow (Estándar)",
        description="Iluminación progresiva palabra por palabra con resplandor sobre el término activo.",
        word_inactive_opacity=0.25,
        use_pill_background=False,
        use_scale_pop=False,
        use_glow=True,
    ),
    "highlight_pill": CaptionStyle(
        slug="highlight_pill",
        name="Highlight Pill (Pastilla Activa)",
        description="Resalta la palabra pronunciada mediante una pastilla sólida de alto contraste.",
        word_inactive_opacity=0.45,
        use_pill_background=True,
        use_scale_pop=False,
        use_glow=False,
    ),
    "pop_scale": CaptionStyle(
        slug="pop_scale",
        name="Pop Scale (Pulso Dinámico)",
        description="Combina iluminación de color con un pulso de escala determinista en GSAP al activar cada palabra.",
        word_inactive_opacity=0.30,
        use_pill_background=False,
        use_scale_pop=True,
        use_glow=True,
    ),
    "minimal_clean": CaptionStyle(
        slug="minimal_clean",
        name="Minimal Clean (Editorial Sobrio)",
        description="Transición limpia de opacidad y color sin resplandor neón, orientada a contenido técnico sobrio.",
        word_inactive_opacity=0.40,
        use_pill_background=False,
        use_scale_pop=False,
        use_glow=False,
    ),
    "underline_bar": CaptionStyle(
        slug="underline_bar",
        name="Underline Bar (Subrayado Técnico)",
        description="Subraya la palabra activa mediante una barra inferior sólida de 4px sin alterar el espaciado.",
        word_inactive_opacity=0.35,
        use_pill_background=False,
        use_scale_pop=False,
        use_glow=False,
        use_underline=True,
    ),
    "box_invert": CaptionStyle(
        slug="box_invert",
        name="Box Invert (Bloque Invertido)",
        description="Invierte el color de fondo y texto sobre la palabra activa para máximo contraste visual.",
        word_inactive_opacity=0.40,
        use_pill_background=False,
        use_scale_pop=False,
        use_glow=False,
        use_box_invert=True,
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


def get_design_system(slug: str) -> DesignSystem:
    if slug not in DESIGN_SYSTEMS:
        available = ", ".join(DESIGN_SYSTEMS.keys())
        raise ValueError(f"El diseño macro '{slug}' no existe. Opciones válidas: {available}")
    return DESIGN_SYSTEMS[slug]


def get_theme(slug: str) -> VisualTheme:
    if slug not in THEMES:
        available = ", ".join(THEMES.keys())
        raise ValueError(f"El estilo visual '{slug}' no existe. Opciones válidas: {available}")
    return THEMES[slug]


def get_layout_variant(slug: str) -> LayoutVariant:
    if slug not in LAYOUT_VARIANTS:
        available = ", ".join(LAYOUT_VARIANTS.keys())
        raise ValueError(f"La variante de layout '{slug}' no existe. Opciones válidas: {available}")
    return LAYOUT_VARIANTS[slug]


def get_chrome_variant(slug: str) -> ChromeVariant:
    if slug not in CHROME_VARIANTS:
        available = ", ".join(CHROME_VARIANTS.keys())
        raise ValueError(f"La variante de marco '{slug}' no existe. Opciones válidas: {available}")
    return CHROME_VARIANTS[slug]


def get_motion_profile(slug: str) -> MotionProfile:
    if slug not in MOTION_PROFILES:
        available = ", ".join(MOTION_PROFILES.keys())
        raise ValueError(
            f"El perfil de movimiento '{slug}' no existe. Opciones válidas: {available}"
        )
    return MOTION_PROFILES[slug]


def get_caption_style(slug: str) -> CaptionStyle:
    if slug not in CAPTION_STYLES:
        available = ", ".join(CAPTION_STYLES.keys())
        raise ValueError(
            f"El estilo de subtítulos '{slug}' no existe. Opciones válidas: {available}"
        )
    return CAPTION_STYLES[slug]


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

    card_shadow = (
        f"8px 8px 0px {pick('accent_primary', theme.accent_primary)}"
        if design.use_hard_shadow
        else (
            "none"
            if (design.use_editorial_rules or design.use_double_academic_border)
            else pick("shadow", theme.shadow)
        )
    )

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
        f"        --badge-radius: {design.badge_radius};",
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
    chrome_slug: str = DEFAULT_CHROME,
    overrides: dict[str, str] | None = None,
) -> str:
    """
    Genera el bloque de reglas estructurales CSS que transforma los componentes
    según el Diseño Macro (Nivel 1), las variantes de Layout/Chrome (Nivel 2)
    y los overrides granulares (Nivel 3).
    """
    ov = overrides or {}
    effective_chrome = design.default_chrome if chrome_slug == "auto" else chrome_slug
    lower_side = ov.get("lower_third_side", layout.lower_third_side)

    lines = [
        "      /* @design-system:start */",
        f"      /* Macro Design: {design.slug} | Layout: {layout.slug} | Chrome: {effective_chrome} */",
        "      .panel, #main-card, #main-window, .node-glass {",
        "        border-radius: var(--radius-lg);",
        "        border: var(--border-width) solid var(--border);",
        "        box-shadow: var(--shadow);",
        "        backdrop-filter: var(--panel-backdrop);",
        "      }",
        "      .badge, .hook-badge, .sys-badge, .term-badge {",
        "        border-radius: var(--badge-radius);",
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

    if design.use_editorial_rules:
        lines.extend(
            [
                "      .panel, #main-card, #main-window {",
                "        border-left: none;",
                "        border-right: none;",
                "        border-top: 4px solid var(--text-primary);",
                "        border-bottom: 1px solid var(--divider);",
                "      }",
                "      header {",
                "        border-bottom: 2px solid var(--text-primary);",
                "        padding-bottom: 20px;",
                "      }",
            ]
        )

    if design.use_hard_shadow:
        lines.extend(
            [
                "      .panel, #main-card, #main-window, .lower-third {",
                "        border: 2px solid var(--accent-primary);",
                "        box-shadow: var(--shadow);",
                "      }",
                "      .badge, .hook-badge {",
                "        background: var(--accent-primary);",
                "        color: var(--bg);",
                "        border: 2px solid var(--accent-primary);",
                "      }",
            ]
        )

    if design.use_accent_left_bar:
        lines.extend(
            [
                "      .panel, #main-card, #main-window {",
                "        border-left: 6px solid var(--accent-primary);",
                "      }",
            ]
        )

    if design.use_bento_surface:
        lines.extend(
            [
                "      .panel, #main-card, #main-window {",
                "        border: 1px solid var(--border-strong);",
                "        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08), var(--shadow);",
                "      }",
            ]
        )

    if design.use_frosted_glass_physics:
        lines.extend(
            [
                "      .panel, #main-card, #main-window, .clean-card, .node-glass {",
                "        background: rgba(255, 255, 255, 0.06);",
                "        border: 1px solid rgba(255, 255, 255, 0.22);",
                "        border-top: 1.5px solid rgba(255, 255, 255, 0.45);",
                "        border-left: 1.5px solid rgba(255, 255, 255, 0.35);",
                "        box-shadow: 0 30px 60px -12px rgba(0, 0, 0, 0.70), inset 0 1px 1px 0 rgba(255, 255, 255, 0.40);",
                "        backdrop-filter: blur(32px) saturate(190%);",
                "        -webkit-backdrop-filter: blur(32px) saturate(190%);",
                "      }",
            ]
        )

    if design.use_clean_studio_surface:
        lines.extend(
            [
                "      .panel, #main-card, #main-window, .clean-card {",
                "        background: rgba(255, 255, 255, 0.88);",
                "        border: 1px solid rgba(255, 255, 255, 0.95);",
                "        box-shadow: 0 20px 45px -12px rgba(15, 23, 42, 0.08), 0 1px 3px 0 rgba(15, 23, 42, 0.04), inset 0 1px 0 #ffffff;",
                "        backdrop-filter: blur(24px);",
                "        -webkit-backdrop-filter: blur(24px);",
                "      }",
            ]
        )

    if design.use_double_academic_border:
        lines.extend(
            [
                "      .panel, #main-card, #main-window {",
                "        border: 2px solid var(--text-primary);",
                "      }",
                "      header {",
                "        border-top: 3px solid var(--text-primary);",
                "        border-bottom: 1px solid var(--text-primary);",
                "        padding: 14px 0;",
                "      }",
            ]
        )

    # Posición de Lower-Third (izquierda o derecha)
    if lower_side == "right":
        lines.extend(
            [
                "      .lower-third {",
                "        left: auto;",
                "        right: 80px;",
                "        border-left: var(--border-width) solid var(--border);",
                "        border-right: 6px solid var(--accent-primary);",
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
                "        border-radius: var(--radius-md);",
                "      }",
            ]
        )

    # Variantes de barra de ventana (Chrome)
    if effective_chrome == "terminal_bar":
        lines.extend(
            [
                "      .dot {",
                "        border-radius: 0px;",
                "        width: 12px;",
                "        height: 12px;",
                "      }",
                "      .window-header, .win-bar, .code-header {",
                "        border-bottom: 2px solid var(--accent-primary);",
                "      }",
            ]
        )
    elif effective_chrome == "minimal_line":
        lines.extend(
            [
                "      .window-dots, .win-bar .dot, .dots {",
                "        display: none;",
                "      }",
            ]
        )
    elif effective_chrome == "hidden":
        lines.extend(
            [
                "      .window-header, .win-bar, .code-header {",
                "        display: none;",
                "      }",
            ]
        )

    lines.append("      /* @design-system:end */")
    return "\n".join(lines)


def generate_caption_css(caption_style: CaptionStyle) -> str:
    """Genera las reglas CSS deterministas para el estilo de subtítulos seleccionado."""
    active_rules = [
        "opacity: 1;",
        "color: var(--caption-active);",
    ]
    if caption_style.use_box_invert:
        active_rules = [
            "opacity: 1;",
            "background: var(--caption-active);",
            "color: var(--bg);",
            "border-radius: var(--radius-sm, 4px);",
            "padding: 2px 10px;",
            "text-shadow: none;",
        ]
    elif caption_style.use_pill_background:
        active_rules.extend(
            [
                "background: var(--accent-primary-soft);",
                "border: 1px solid var(--border-strong);",
                "border-radius: var(--radius-sm, 8px);",
                "padding: 2px 10px;",
                "text-shadow: none;",
            ]
        )
    elif caption_style.use_underline:
        active_rules.extend(
            [
                "border-bottom: 4px solid var(--caption-active);",
                "padding-bottom: 2px;",
                "text-shadow: var(--caption-shadow);",
            ]
        )
    elif caption_style.use_glow:
        active_rules.append("text-shadow: var(--caption-glow);")
    else:
        active_rules.append("text-shadow: var(--caption-shadow);")

    lines = [
        "      /* @caption-style:start */",
        f"      /* Caption Style: {caption_style.slug} */",
        "      .caption-phrase {",
        "        display: inline-block;",
        "        background: var(--caption-bg);",
        "        padding: 6px 18px;",
        "        border-radius: var(--radius-md, 12px);",
        "      }",
        "      .word {",
        "        display: inline-block;",
        f"        opacity: {caption_style.word_inactive_opacity};",
        "        color: var(--caption-text);",
        "        margin: 0 4px;",
        "      }",
        "      .word.active {",
        *[f"        {r}" for r in active_rules],
        "      }",
        "      /* @caption-style:end */",
    ]
    return "\n".join(lines)


def apply_style_to_html(
    html_path: Path,
    theme_slug: str = DEFAULT_THEME,
    caption_style_slug: str | None = None,
    design_slug: str = DEFAULT_DESIGN,
    layout_slug: str = DEFAULT_LAYOUT,
    chrome_slug: str = DEFAULT_CHROME,
    motion_slug: str = DEFAULT_MOTION,
    overrides: dict[str, str] | None = None,
) -> None:
    """
    Aplica de forma idempotente y no destructiva los 3 niveles de diseño sobre index.html:
      - Nivel 1: Diseño Macro (design_slug)
      - Nivel 2: Variantes internas (theme_slug, layout_slug, chrome_slug, motion_slug, caption_style_slug)
      - Nivel 3: Overrides granulares (overrides)
    """
    if not html_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo HTML: {html_path}")

    design = get_design_system(design_slug)
    theme = get_theme(theme_slug)
    layout = get_layout_variant(layout_slug)
    get_chrome_variant(chrome_slug)
    motion = get_motion_profile(motion_slug)

    content = html_path.read_text(encoding="utf-8")
    css_vars_block = build_root_css_block(theme, design, layout, overrides=overrides)
    design_css_block = generate_design_structural_css(
        design, layout, chrome_slug=chrome_slug, overrides=overrides
    )

    # 1. Reemplazar bloque @theme:start ... @theme:end o el primer bloque :root { ... }
    if "/* @theme:start */" in content and "/* @theme:end */" in content:
        content = re.sub(
            r"\s*/\* @theme:start \*/.*?/\* @theme:end \*/",
            "\n" + css_vars_block,
            content,
            count=1,
            flags=re.DOTALL,
        )
    elif ":root" in content:
        content = re.sub(
            r"\s*:root\s*\{[^}]*\}",
            "\n" + css_vars_block,
            content,
            count=1,
            flags=re.DOTALL,
        )

    # 2. Inyectar o actualizar bloque estructural del Diseño Macro y variantes (@design-system)
    if "/* @design-system:start */" in content and "/* @design-system:end */" in content:
        content = re.sub(
            r"\s*/\* @design-system:start \*/.*?/\* @design-system:end \*/",
            "\n" + design_css_block,
            content,
            count=1,
            flags=re.DOTALL,
        )
    elif "</style>" in content:
        content = content.replace("</style>", f"{design_css_block}\n    </style>", 1)

    # 3. Actualizar estilo de subtítulos si se especificó
    if caption_style_slug is not None:
        cap_style = get_caption_style(caption_style_slug)
        cap_css_block = generate_caption_css(cap_style)
        if "/* @caption-style:start */" in content and "/* @caption-style:end */" in content:
            content = re.sub(
                r"\s*/\* @caption-style:start \*/.*?/\* @caption-style:end \*/",
                "\n" + cap_css_block,
                content,
                count=1,
                flags=re.DOTALL,
            )
        elif "</style>" in content:
            content = content.replace("</style>", f"{cap_css_block}\n    </style>", 1)

    # 4. Sincronizar perfil de movimiento GSAP (ease y duration en animaciones de entrada)
    content = re.sub(
        r'(tl\.from\("#header",\s*\{[^}]*duration:\s*)[0-9.]+(,\s*ease:\s*")[a-zA-Z0-9.()]+(")',
        rf"\g<1>{motion.entry_duration}\g<2>{motion.entry_ease}\g<3>",
        content,
    )
    content = re.sub(
        r'(tl\.from\("(?:\.panel|#main-card|#main-window|#node-a, #node-b)",\s*\{[^}]*duration:\s*)[0-9.]+(,\s*ease:\s*")[a-zA-Z0-9.()]+(")',
        rf"\g<1>{motion.entry_duration}\g<2>{motion.panel_ease}\g<3>",
        content,
    )

    # 5. Registrar atributos de trazabilidad en #root
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


def inspect_project_design(project_or_html: str | Path) -> dict:
    """Inspecciona y devuelve la configuración de los 3 niveles activa en un proyecto."""
    target = Path(project_or_html)
    base_dir = Path(__file__).resolve().parent.parent
    if not target.exists():
        candidate = base_dir / "projects" / str(project_or_html)
        if candidate.exists():
            target = candidate

    html_file = target / "index.html" if target.is_dir() else target
    if not html_file.exists():
        raise FileNotFoundError(f"No se encontró index.html en '{target}'.")

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
        "chrome": DEFAULT_CHROME,
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
    chrome_slug: str | None = None,
    motion_slug: str | None = None,
    overrides: dict[str, str] | None = None,
    reset_overrides: bool = False,
) -> Path:
    """
    Aplica o actualiza cualquier combinación de Nivel 1 (Diseño Macro),
    Nivel 2 (Opciones internas) o Nivel 3 (Overrides puntuales) sobre un proyecto,
    preservando la configuración previa de los niveles que no se hayan modificado.
    """
    target = Path(project_or_html)
    base_dir = Path(__file__).resolve().parent.parent

    if not target.exists():
        candidate = base_dir / "projects" / str(project_or_html)
        if candidate.exists():
            target = candidate

    html_file = target / "index.html" if target.is_dir() else target
    if not html_file.exists():
        raise FileNotFoundError(f"No se encontró index.html en '{target}'.")

    pkg_file = html_file.parent / "package.json"
    pkg_data: dict = {}
    saved_state: dict = {}
    if pkg_file.exists():
        try:
            pkg_data = json.loads(pkg_file.read_text(encoding="utf-8"))
            saved_state = pkg_data.get("videoDesign", {})
        except (OSError, json.JSONDecodeError):
            pkg_data = {}

    # Si cambia el Diseño Macro y el usuario no forzó sub-opciones, adoptar las nativas del diseño
    design_changed = design_slug is not None and design_slug != saved_state.get("design")
    resolved_design_slug = design_slug or saved_state.get("design", DEFAULT_DESIGN)
    design_obj = get_design_system(resolved_design_slug)

    resolved_theme = theme_slug or (
        design_obj.default_theme
        if design_changed
        else saved_state.get("style", pkg_data.get("videoStyle", design_obj.default_theme))
    )
    resolved_layout = layout_slug or saved_state.get("layout", DEFAULT_LAYOUT)
    resolved_chrome = chrome_slug or (
        design_obj.default_chrome
        if design_changed
        else saved_state.get("chrome", design_obj.default_chrome)
    )
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
        chrome_slug=resolved_chrome,
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
                "chrome": resolved_chrome,
                "motion": resolved_motion,
                "captionStyle": resolved_caption,
                "overrides": merged_overrides,
            }
            pkg_file.write_text(json.dumps(pkg_data, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass

    print(
        f"[Design] Aplicado Diseño='{resolved_design_slug}' | Tema='{resolved_theme}' | "
        f"Layout='{resolved_layout}' | Chrome='{resolved_chrome}' | Motion='{resolved_motion}' | "
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
            "chromes": {k: asdict(v) for k, v in CHROME_VARIANTS.items()},
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
            f"    Preset nativo        : style={d.default_theme}, chrome={d.default_chrome}, motion={d.default_motion}, captions={d.default_caption_style}"
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

    print("\n=== NIVEL 2C: VARIANTES DE MARCO DE TARJETAS (--chrome) ===")
    for slug, ch in CHROME_VARIANTS.items():
        print(f"  * {slug:<20} : {ch.name} — {ch.description}")

    print("\n=== NIVEL 2D: PERFILES DE ANIMACIÓN GSAP (--motion) ===")
    for slug, mo in MOTION_PROFILES.items():
        print(f"  * {slug:<20} : {mo.name} — {mo.description}")

    print("\n=== NIVEL 2E: ESTILOS DE SUBTÍTULOS CINÉTICOS (--caption-style) ===")
    for slug, c in CAPTION_STYLES.items():
        print(f"  * {slug:<20} : {c.name} — {c.description}")

    print("\n=== NIVEL 3: PROPIEDADES AJUSTABLES POR DISEÑO (--set clave=valor) ===")
    print("  " + ", ".join(sorted(OVERRIDABLE_KEYS)))
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gestor jerárquico de Diseños Macro, Variantes Internas y Overrides para video-pipeline"
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Operaciones de diseño y estilo")

    # list
    p_list = subparsers.add_parser("list", help="Listar catálogo completo de los 3 niveles")
    p_list.add_argument("--json", action="store_true", help="Exportar catálogo en formato JSON")

    # inspect
    p_insp = subparsers.add_parser(
        "inspect", help="Inspeccionar el estado de diseño activo en un proyecto"
    )
    p_insp.add_argument("target", help="Nombre del proyecto en projects/ o ruta a index.html")

    # apply
    p_apply = subparsers.add_parser(
        "apply",
        help="Aplicar un Diseño Macro, cambiar opciones internas o ajustar propiedades puntuales",
    )
    p_apply.add_argument("target", help="Nombre del proyecto en projects/ o ruta a index.html")
    p_apply.add_argument(
        "-d",
        "--design",
        choices=list(DESIGN_SYSTEMS.keys()),
        help="Nivel 1: Diseño Macro completo (cambia geometría, sombras, marcos y preset)",
    )
    p_apply.add_argument(
        "-s",
        "--style",
        choices=list(THEMES.keys()),
        help="Nivel 2: Tema visual / paleta de colores dentro del diseño",
    )
    p_apply.add_argument(
        "--layout",
        choices=list(LAYOUT_VARIANTS.keys()),
        help="Nivel 2: Variante de distribución interna de paneles y lower-third",
    )
    p_apply.add_argument(
        "--chrome",
        choices=list(CHROME_VARIANTS.keys()),
        help="Nivel 2: Variante de cabecera de tarjetas/ventanas",
    )
    p_apply.add_argument(
        "--motion",
        choices=list(MOTION_PROFILES.keys()),
        help="Nivel 2: Perfil de animación GSAP",
    )
    p_apply.add_argument(
        "--caption-style",
        choices=list(CAPTION_STYLES.keys()),
        help="Nivel 2: Estilo de subtítulos cinéticos",
    )
    p_apply.add_argument(
        "--set",
        dest="overrides",
        action="append",
        metavar="CLAVE=VALOR",
        help="Nivel 3: Ajustar propiedad individual de este diseño (repetible, ej. --set accent_primary=#ff5500)",
    )
    p_apply.add_argument(
        "--reset-overrides",
        action="store_true",
        help="Limpiar ajustes individuales (--set) previos del proyecto",
    )

    args = parser.parse_args()
    if not args.subcommand or args.subcommand == "list":
        print_catalog(as_json=getattr(args, "json", False))
        sys.exit(0)

    if args.subcommand == "inspect":
        try:
            state = inspect_project_design(args.target)
            print(json.dumps(state, indent=2, ensure_ascii=False))
        except FileNotFoundError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)

    if args.subcommand == "apply":
        try:
            parsed_overrides = parse_set_overrides(args.overrides)
            apply_style_to_project(
                project_or_html=args.target,
                theme_slug=args.style,
                caption_style_slug=args.caption_style,
                design_slug=args.design,
                layout_slug=args.layout,
                chrome_slug=args.chrome,
                motion_slug=args.motion,
                overrides=parsed_overrides,
                reset_overrides=args.reset_overrides,
            )
        except (FileNotFoundError, ValueError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
