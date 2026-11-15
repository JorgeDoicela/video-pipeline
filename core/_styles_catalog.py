"""
Catálogo declarativo de tokens y variantes para el sistema de diseño en 3 niveles:
  - Nivel 1: Diseños Macro (DESIGN_SYSTEMS)
  - Nivel 2: Temas cromáticos (THEMES), Layouts (LAYOUT_VARIANTS), Marcos (CHROME_VARIANTS),
             Perfiles GSAP (MOTION_PROFILES) y Subtítulos (CAPTION_STYLES)
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
    use_scale_pop: bool = False


DEFAULT_DESIGN = "cyber_glass"
DEFAULT_THEME = "cyber_dark"
DEFAULT_LAYOUT = "standard"
DEFAULT_CHROME = "auto"
DEFAULT_MOTION = "dynamic"
DEFAULT_CAPTION_STYLE = "karaoke_glow"

# =====================================================================
# NIVEL 1: CATÁLOGO DE DISEÑOS MACRO (7 DISEÑOS GRANDES)
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
        shadow_mode="theme",
        structural_css=(
            ".panel, #main-card, #main-window, .clean-card, .node-glass {",
            "  background: var(--surface);",
            "  border: 1px solid var(--border);",
            "  border-top: 1.5px solid var(--border-strong);",
            "  border-left: 1.5px solid var(--border-strong);",
            "  box-shadow: var(--shadow), inset 0 1px 1px 0 var(--divider);",
            "  backdrop-filter: var(--panel-backdrop);",
            "  -webkit-backdrop-filter: var(--panel-backdrop);",
            "}",
        ),
    ),
    "clean_studio": DesignSystem(
        slug="clean_studio",
        name="Clean Studio (Apple Keynote & Stripe Light)",
        description="Diseño corporativo luminoso de alta gama con sombras multicapa, tarjetas limpias y acentos vivos.",
        default_theme="minimal_light",
        default_chrome="hidden",
        default_motion="smooth",
        default_caption_style="highlight_pill",
        radius_lg="28px",
        radius_md="16px",
        radius_sm="999px",
        border_width="1px",
        panel_backdrop="blur(24px)",
        badge_radius="999px",
        shadow_mode="theme",
        structural_css=(
            ".panel, #main-card, #main-window, .clean-card {",
            "  background: var(--surface);",
            "  border: 1px solid var(--border);",
            "  box-shadow: var(--shadow), inset 0 1px 0 var(--divider);",
            "  backdrop-filter: var(--panel-backdrop);",
            "  -webkit-backdrop-filter: var(--panel-backdrop);",
            "}",
        ),
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
        shadow_mode="none",
        structural_css=(
            ".panel, #main-card, #main-window {",
            "  border-left: none;",
            "  border-right: none;",
            "  border-top: 4px solid var(--text-primary);",
            "  border-bottom: 1px solid var(--divider);",
            "}",
            "header {",
            "  border-bottom: 2px solid var(--text-primary);",
            "  padding-bottom: 20px;",
            "}",
        ),
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
        shadow_mode="hard",
        structural_css=(
            ".panel, #main-card, #main-window, .lower-third {",
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
        shadow_mode="theme",
        structural_css=(
            ".panel, #main-card, #main-window {",
            "  border-left: 6px solid var(--accent-primary);",
            "}",
        ),
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
        shadow_mode="theme",
        structural_css=(
            ".panel, #main-card, #main-window {",
            "  border: 1px solid var(--border-strong);",
            "  box-shadow: inset 0 1px 0 var(--divider), var(--shadow);",
            "}",
        ),
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
        shadow_mode="none",
        structural_css=(
            ".panel, #main-card, #main-window {",
            "  border: 2px solid var(--text-primary);",
            "}",
            "header {",
            "  border-top: 3px solid var(--text-primary);",
            "  border-bottom: 1px solid var(--text-primary);",
            "  padding: 14px 0;",
            "}",
        ),
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
        css_rules=(
            ".dot {",
            "  border-radius: 0px;",
            "  width: 12px;",
            "  height: 12px;",
            "}",
            ".window-header, .win-bar, .code-header {",
            "  border-bottom: 2px solid var(--accent-primary);",
            "}",
        ),
    ),
    "minimal_line": ChromeVariant(
        slug="minimal_line",
        name="Minimal Editorial Line",
        description="Oculta los botones de ventana y deja únicamente la barra tipográfica limpia.",
        css_rules=(
            ".window-dots, .win-bar .dot, .dots {",
            "  display: none;",
            "}",
        ),
    ),
    "hidden": ChromeVariant(
        slug="hidden",
        name="Clean Card (Sin Barra de Ventana)",
        description="Oculta por completo la barra superior de ventana dejando tarjetas puras.",
        css_rules=(
            ".window-header, .win-bar, .code-header {",
            "  display: none;",
            "}",
        ),
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
        active_css=(
            "opacity: 1;",
            "color: var(--caption-active);",
            "text-shadow: var(--caption-glow);",
        ),
    ),
    "highlight_pill": CaptionStyle(
        slug="highlight_pill",
        name="Highlight Pill (Pastilla Activa)",
        description="Resalta la palabra pronunciada mediante una pastilla sólida de alto contraste.",
        word_inactive_opacity=0.45,
        active_css=(
            "opacity: 1;",
            "color: var(--caption-active);",
            "background: var(--accent-primary-soft);",
            "border: 1px solid var(--border-strong);",
            "border-radius: var(--radius-sm, 8px);",
            "padding: 2px 10px;",
            "text-shadow: none;",
        ),
    ),
    "pop_scale": CaptionStyle(
        slug="pop_scale",
        name="Pop Scale (Pulso Dinámico)",
        description="Combina iluminación de color con un pulso de escala determinista en GSAP al activar cada palabra.",
        word_inactive_opacity=0.30,
        use_scale_pop=True,
        active_css=(
            "opacity: 1;",
            "color: var(--caption-active);",
            "text-shadow: var(--caption-glow);",
        ),
    ),
    "minimal_clean": CaptionStyle(
        slug="minimal_clean",
        name="Minimal Clean (Editorial Sobrio)",
        description="Transición limpia de opacidad y color sin resplandor neón, orientada a contenido técnico sobrio.",
        word_inactive_opacity=0.40,
        active_css=(
            "opacity: 1;",
            "color: var(--caption-active);",
            "text-shadow: var(--caption-shadow);",
        ),
    ),
    "underline_bar": CaptionStyle(
        slug="underline_bar",
        name="Underline Bar (Subrayado Técnico)",
        description="Subraya la palabra activa mediante una barra inferior sólida de 4px sin alterar el espaciado.",
        word_inactive_opacity=0.35,
        active_css=(
            "opacity: 1;",
            "color: var(--caption-active);",
            "border-bottom: 4px solid var(--caption-active);",
            "padding-bottom: 2px;",
            "text-shadow: var(--caption-shadow);",
        ),
    ),
    "box_invert": CaptionStyle(
        slug="box_invert",
        name="Box Invert (Bloque Invertido)",
        description="Invierte el color de fondo y texto sobre la palabra activa para máximo contraste visual.",
        word_inactive_opacity=0.40,
        active_css=(
            "opacity: 1;",
            "background: var(--caption-active);",
            "color: var(--bg);",
            "border-radius: var(--radius-sm, 4px);",
            "padding: 2px 10px;",
            "text-shadow: none;",
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
