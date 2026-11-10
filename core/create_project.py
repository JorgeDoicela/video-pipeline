#!/usr/bin/env python3
"""
Scaffolding automatizado de proyectos de video a partir de plantillas optimizadas.
Copia la plantilla seleccionada, aplica la arquitectura jerárquica de diseño en 3 niveles
(Diseño Macro, Variantes Internas y Overrides), personaliza metadatos y prepara HyperFrames.
"""

import argparse
import re
import shutil
import sys
from pathlib import Path

try:
    from core.styles import (
        CAPTION_STYLES,
        CHROME_VARIANTS,
        DEFAULT_DESIGN,
        DESIGN_SYSTEMS,
        LAYOUT_VARIANTS,
        MOTION_PROFILES,
        THEMES,
        apply_style_to_project,
        parse_set_overrides,
    )
except ModuleNotFoundError:
    from styles import (  # type: ignore
        CAPTION_STYLES,
        CHROME_VARIANTS,
        DEFAULT_DESIGN,
        DESIGN_SYSTEMS,
        LAYOUT_VARIANTS,
        MOTION_PROFILES,
        THEMES,
        apply_style_to_project,
        parse_set_overrides,
    )

AVAILABLE_TEMPLATES = {
    "portrait_9_16": "Formato vertical 9:16 (1080x1920) para TikTok, Instagram Reels y YouTube Shorts",
    "landscape_16_9": "Formato horizontal 16:9 (1920x1080) para YouTube y presentaciones widescreen",
    "square_1_1": "Formato cuadrado 1:1 (1080x1080) para feeds de LinkedIn, Twitter e Instagram",
    "feed_4_5": "Formato vertical 4:5 (1080x1350) de alta cobertura para feeds móviles de LinkedIn e Instagram",
    "talking_head": "Video horizontal 16:9 con presentador, lower-third animado y subtítulos cinéticos",
    "talking_head_9_16": "Video vertical 9:16 con presentador para Shorts/Reels/TikTok y subtítulos en zona segura",
    "tech_explainer": "Diagramas de arquitectura SVG interactivos con nodos animados y flujo de paquetes",
    "code_walkthrough": "Explicación de código paso a paso con resaltado progresivo de líneas en GSAP",
    "benchmark_chart": "Comparativa de rendimiento con barras animadas y KPIs de latencia/throughput",
}


def sanitize_project_name(name: str) -> str:
    """Convierte el nombre en un slug válido para directorios y package.json."""
    slug = re.sub(r"[^a-zA-Z0-9_\-]+", "-", name.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        raise ValueError("El nombre del proyecto no contiene caracteres alfanuméricos válidos.")
    return slug


def update_composition_duration(html_path: Path, duration: float) -> None:
    """Actualiza data-duration en el nodo raíz y en etiquetas <video>/<audio> sincronizadas."""
    if not html_path.exists():
        return
    formatted_dur = f"{round(duration, 2):g}"
    content = html_path.read_text(encoding="utf-8")
    content = re.sub(
        r'data-duration="[0-9.]+"',
        f'data-duration="{formatted_dur}"',
        content,
    )
    html_path.write_text(content, encoding="utf-8")


def create_project(
    name: str,
    template: str = "portrait_9_16",
    title: str | None = None,
    duration: float | None = None,
    force: bool = False,
    design: str = DEFAULT_DESIGN,
    style: str | None = None,
    layout: str | None = None,
    chrome: str | None = None,
    motion: str | None = None,
    caption_style: str | None = None,
    overrides: dict[str, str] | None = None,
) -> Path:
    base_dir = Path(__file__).resolve().parent.parent
    templates_dir = base_dir / "templates"
    projects_dir = base_dir / "projects"

    template_path = templates_dir / template
    if not template_path.exists():
        print(f"Error: La plantilla '{template}' no existe en {templates_dir}", file=sys.stderr)
        print("Plantillas disponibles:", file=sys.stderr)
        for t_name, t_desc in AVAILABLE_TEMPLATES.items():
            print(f"  - {t_name}: {t_desc}", file=sys.stderr)
        sys.exit(1)

    if design not in DESIGN_SYSTEMS:
        print(
            f"Error: El diseño macro '{design}' no existe. Opciones: {', '.join(DESIGN_SYSTEMS.keys())}",
            file=sys.stderr,
        )
        sys.exit(1)

    if style is not None and style not in THEMES:
        print(
            f"Error: El estilo '{style}' no existe. Estilos disponibles: {', '.join(THEMES.keys())}",
            file=sys.stderr,
        )
        sys.exit(1)

    if caption_style is not None and caption_style not in CAPTION_STYLES:
        print(
            f"Error: El estilo de subtítulos '{caption_style}' no existe. Opciones: {', '.join(CAPTION_STYLES.keys())}",
            file=sys.stderr,
        )
        sys.exit(1)

    project_slug = sanitize_project_name(name)
    target_path = projects_dir / project_slug

    if target_path.exists():
        if not force:
            print(
                f"Error: El proyecto '{project_slug}' ya existe en {target_path}. Use --force para sobrescribir.",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"[Scaffold] Sobrescribiendo directorio existente: {target_path}")
        shutil.rmtree(target_path)

    # Copiar plantilla excluyendo artefactos de compilación
    def ignore_patterns(dir_path: str, files: list[str]) -> list[str]:
        ignored = []
        for f in files:
            if f in {".hyperframes", ".cache", "frames", "node_modules", ".gitkeep"}:
                ignored.append(f)
        return ignored

    shutil.copytree(template_path, target_path, ignore=ignore_patterns)

    # Actualizar nombre del paquete en package.json antes de aplicar el estado de diseño
    pkg_file = target_path / "package.json"
    if pkg_file.exists():
        import json

        try:
            pkg_data = json.loads(pkg_file.read_text(encoding="utf-8"))
            pkg_data["name"] = f"project-{project_slug}"
            pkg_file.write_text(json.dumps(pkg_data, indent=2) + "\n", encoding="utf-8")
        except (OSError, json.JSONDecodeError) as e:
            print(f"Advertencia al actualizar package.json: {e}", file=sys.stderr)

    # Aplicar arquitectura de diseño de 3 niveles y persistir estado en package.json
    html_file = target_path / "index.html"
    if html_file.exists():
        apply_style_to_project(
            project_or_html=target_path,
            theme_slug=style,
            caption_style_slug=caption_style,
            design_slug=design,
            layout_slug=layout,
            chrome_slug=chrome,
            motion_slug=motion,
            overrides=overrides,
        )

        if duration is not None:
            update_composition_duration(html_file, duration)

        if title:
            html_content = html_file.read_text(encoding="utf-8")
            if "<h1" in html_content:
                html_content = re.sub(
                    r"(<h1[^>]*>).*?(</h1>)",
                    rf"\g<1>{title}\g<2>",
                    html_content,
                    count=1,
                    flags=re.DOTALL,
                )
            elif 'id="card-title"' in html_content:
                html_content = re.sub(
                    r'(<[^>]+id="card-title"[^>]*>).*?(</h[1-6]>)',
                    rf"\g<1>{title}\g<2>",
                    html_content,
                    count=1,
                    flags=re.DOTALL,
                )
            html_file.write_text(html_content, encoding="utf-8")

    print(f"[Scaffold] Proyecto '{project_slug}' creado con éxito en: {target_path}")
    print(f"[Scaffold] Plantilla base: {template} | Diseño Macro: {design}")
    print("\nComandos operativos:")
    print(f"  1. Vista previa interactiva : pnpm exec hyperframes preview projects/{project_slug}")
    print(
        f"  2. Cambiar diseño o estilo  : python3 core/pipeline.py style {project_slug} -d swiss_editorial"
    )
    print(f"  3. Validación de estándares : pnpm exec hyperframes check projects/{project_slug}")
    print(
        f"  4. Renderizado de producción: pnpm exec hyperframes render projects/{project_slug} -o projects/{project_slug}/video_{project_slug}.mp4"
    )

    return target_path


def main():
    parser = argparse.ArgumentParser(
        description="Scaffold de nuevos proyectos de video programático en HyperFrames"
    )
    parser.add_argument("name", help="Nombre o slug del nuevo proyecto")
    parser.add_argument(
        "-t",
        "--template",
        default="portrait_9_16",
        choices=list(AVAILABLE_TEMPLATES.keys()),
        help="Plantilla base a utilizar",
    )
    parser.add_argument(
        "-d",
        "--design",
        default=DEFAULT_DESIGN,
        choices=list(DESIGN_SYSTEMS.keys()),
        help=f"Nivel 1: Diseño Macro del proyecto (defecto: {DEFAULT_DESIGN})",
    )
    parser.add_argument(
        "-s",
        "--style",
        choices=list(THEMES.keys()),
        help="Nivel 2: Tema visual / paleta (si se omite, usa el nativo del Diseño Macro)",
    )
    parser.add_argument(
        "--layout",
        choices=list(LAYOUT_VARIANTS.keys()),
        help="Nivel 2: Variante de distribución interna de paneles y lower-third",
    )
    parser.add_argument(
        "--chrome",
        choices=list(CHROME_VARIANTS.keys()),
        help="Nivel 2: Variante de barra de ventana",
    )
    parser.add_argument(
        "--motion",
        choices=list(MOTION_PROFILES.keys()),
        help="Nivel 2: Perfil de animación GSAP",
    )
    parser.add_argument(
        "--caption-style",
        choices=list(CAPTION_STYLES.keys()),
        help="Nivel 2: Estilo de subtítulos cinéticos",
    )
    parser.add_argument(
        "--set",
        dest="overrides",
        action="append",
        metavar="CLAVE=VALOR",
        help="Nivel 3: Ajustar propiedad individual (ej. --set accent_primary=#ff5500)",
    )
    parser.add_argument("--title", help="Título principal para inyectar en el index.html")
    parser.add_argument(
        "--duration", type=float, help="Duración en segundos del video (data-duration)"
    )
    parser.add_argument(
        "-f", "--force", action="store_true", help="Sobrescribir si el directorio ya existe"
    )

    args = parser.parse_args()
    parsed_overrides = parse_set_overrides(args.overrides)
    create_project(
        name=args.name,
        template=args.template,
        title=args.title,
        duration=args.duration,
        force=args.force,
        design=args.design,
        style=args.style,
        layout=args.layout,
        chrome=args.chrome,
        motion=args.motion,
        caption_style=args.caption_style,
        overrides=parsed_overrides,
    )


if __name__ == "__main__":
    main()
