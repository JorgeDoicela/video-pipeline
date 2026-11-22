#!/usr/bin/env python3
"""
Motor jerárquico de sistemas de diseño en 3 niveles para el pipeline de video:
  1. Nivel Macro (DesignSystem / --design): 3 Diseños canónicos estructuralmente distintos.
  2. Nivel Medio (--style, --layout, --motion, --caption-style):
     3 temas cromáticos WCAG AA, 3 layouts, 3 perfiles GSAP y subtítulos minimal_clean.
  3. Nivel Micro (--set clave=valor):
     Overrides puntuales por proyecto sin alterar el catálogo global.
"""

import argparse
import json
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core._runtime import ensure_local_venv, ensure_repo_root_on_path  # noqa: E402

ensure_repo_root_on_path()

from core._styles_catalog import (  # noqa: E402
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
    MotionProfile,
    VisualTheme,
    get_caption_style,
    get_design_system,
    get_layout_variant,
    get_motion_profile,
    get_theme,
)
from core._styles_renderer import (  # noqa: E402
    apply_style_to_html,
    apply_style_to_project,
    build_root_css_block,
    generate_caption_css,
    generate_design_structural_css,
    inspect_project_design,
    parse_set_overrides,
    print_catalog,
    upsert_marked_css_block,
)

__all__ = [
    "CAPTION_STYLES",
    "DEFAULT_CAPTION_STYLE",
    "DEFAULT_DESIGN",
    "DEFAULT_LAYOUT",
    "DEFAULT_MOTION",
    "DEFAULT_THEME",
    "DESIGN_SYSTEMS",
    "LAYOUT_VARIANTS",
    "MOTION_PROFILES",
    "OVERRIDABLE_KEYS",
    "THEMES",
    "CaptionStyle",
    "DesignSystem",
    "LayoutVariant",
    "MotionProfile",
    "VisualTheme",
    "add_design_arguments",
    "apply_style_to_html",
    "apply_style_to_project",
    "build_root_css_block",
    "generate_caption_css",
    "generate_design_structural_css",
    "get_caption_style",
    "get_design_system",
    "get_layout_variant",
    "get_motion_profile",
    "get_theme",
    "inspect_project_design",
    "parse_set_overrides",
    "print_catalog",
    "upsert_marked_css_block",
]


def add_design_arguments(
    subparser: argparse.ArgumentParser,
    default_design: str | None = None,
) -> None:
    """Registra de forma canónica los argumentos CLI de los 3 niveles de diseño en un parser."""
    subparser.add_argument(
        "-d",
        "--design",
        default=default_design,
        choices=list(DESIGN_SYSTEMS.keys()),
        help=f"Nivel 1: Diseño Macro completo ({', '.join(DESIGN_SYSTEMS.keys())})",
    )
    subparser.add_argument(
        "-s",
        "--style",
        choices=list(THEMES.keys()),
        help=f"Nivel 2: Tema cromático y tipográfico ({', '.join(THEMES.keys())})",
    )
    subparser.add_argument(
        "--layout",
        choices=list(LAYOUT_VARIANTS.keys()),
        help=f"Nivel 2: Variante de distribución interna ({', '.join(LAYOUT_VARIANTS.keys())})",
    )
    subparser.add_argument(
        "--motion",
        choices=list(MOTION_PROFILES.keys()),
        help=f"Nivel 2: Perfil de animación GSAP ({', '.join(MOTION_PROFILES.keys())})",
    )
    subparser.add_argument(
        "--caption-style",
        choices=list(CAPTION_STYLES.keys()),
        help=f"Nivel 2: Estilo de subtítulos cinéticos ({', '.join(CAPTION_STYLES.keys())})",
    )
    subparser.add_argument(
        "--set",
        dest="overrides",
        action="append",
        metavar="CLAVE=VALOR",
        help="Nivel 3: Sobreescribir propiedad puntual de este diseño (ej. --set accent_primary=#ff5500)",
    )


def main() -> None:
    ensure_local_venv()
    parser = argparse.ArgumentParser(
        description="Gestor jerárquico de Diseños Macro, Variantes Internas y Overrides para video-pipeline"
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Operaciones de diseño y estilo")

    p_list = subparsers.add_parser("list", help="Listar catálogo completo de los 3 niveles")
    p_list.add_argument("--json", action="store_true", help="Exportar catálogo en formato JSON")

    p_insp = subparsers.add_parser(
        "inspect", help="Inspeccionar el estado de diseño activo en un proyecto"
    )
    p_insp.add_argument("target", help="Nombre del proyecto en projects/ o ruta a index.html")

    p_apply = subparsers.add_parser(
        "apply",
        help="Aplicar un Diseño Macro, cambiar opciones internas o ajustar propiedades puntuales",
    )
    p_apply.add_argument("target", help="Nombre del proyecto en projects/ o ruta a index.html")
    add_design_arguments(p_apply, default_design=None)
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
                motion_slug=args.motion,
                overrides=parsed_overrides,
                reset_overrides=args.reset_overrides,
            )
        except (FileNotFoundError, ValueError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
