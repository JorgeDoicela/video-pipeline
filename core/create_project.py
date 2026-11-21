#!/usr/bin/env python3
"""
Scaffolding automatizado de proyectos de video a partir de plantillas optimizadas.
Copia la plantilla seleccionada, aplica la arquitectura jerárquica de diseño en 3 niveles
(Diseño Macro, Variantes Internas y Overrides), personaliza metadatos y prepara HyperFrames.
"""

import argparse
import html
import json
import re
import shutil
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core._runtime import ensure_local_venv, ensure_repo_root_on_path  # noqa: E402

ensure_repo_root_on_path()

from core.styles import (  # noqa: E402
    CAPTION_STYLES,
    DEFAULT_DESIGN,
    DESIGN_SYSTEMS,
    THEMES,
    add_design_arguments,
    apply_style_to_project,
    parse_set_overrides,
)

AVAILABLE_TEMPLATES = {
    "explainer_scenes_9_16": "Formato vertical 9:16 (1080x1920) multi-escena estilo Vox/Explainer con SVG animados, UI mockups y SFX",
    "explainer_scenes_16_9": "Formato horizontal 16:9 (1920x1080) multi-escena faceless para ensayos, tutoriales y explicativos",
    "short_quote_9_16": "Formato vertical 9:16 (1080x1920) para citas, versículos, reflexiones y narrativa breve",
    "short_tech_9_16": "Formato vertical 9:16 (1080x1920) para tips técnicos y código en TikTok/Reels/Shorts",
    "talking_head_9_16": "Video vertical 9:16 (1080x1920) con presentador y subtítulos en zona segura",
    "editorial_16_9": "Formato horizontal 16:9 (1920x1080) para narrativa histórica, bíblica, ensayos y puntos clave",
    "talking_head_16_9": "Video horizontal 16:9 (1920x1080) con presentador, lower-third animado y subtítulos cinéticos",
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
    template: str = "short_quote_9_16",
    title: str | None = None,
    duration: float | None = None,
    force: bool = False,
    design: str = DEFAULT_DESIGN,
    style: str | None = None,
    layout: str | None = None,
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
            motion_slug=motion,
            overrides=overrides,
        )

        if duration is not None:
            update_composition_duration(html_file, duration)

        if title:
            safe_title = html.escape(title, quote=False)
            html_content = html_file.read_text(encoding="utf-8")
            if "<h1" in html_content:
                html_content = re.sub(
                    r"(<h1[^>]*>).*?(</h1>)",
                    lambda m: f"{m.group(1)}{safe_title}{m.group(2)}",
                    html_content,
                    count=1,
                    flags=re.DOTALL,
                )
            elif 'id="card-title"' in html_content:
                html_content = re.sub(
                    r'(<[^>]+id="card-title"[^>]*>).*?(</h[1-6]>)',
                    lambda m: f"{m.group(1)}{safe_title}{m.group(2)}",
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
        f"  2. Cambiar diseño o estilo  : python3 core/pipeline.py style {project_slug} -d editorial"
    )
    print(f"  3. Validación de estándares : pnpm exec hyperframes check projects/{project_slug}")
    print(
        f"  4. Renderizado de producción: pnpm exec hyperframes render projects/{project_slug} -o projects/{project_slug}/video_{project_slug}.mp4"
    )

    return target_path


def register_scaffold_arguments(parser: argparse.ArgumentParser) -> None:
    """Registra los argumentos de creación/scaffolding de proyectos en el parser indicado."""
    parser.add_argument("name", help="Nombre o slug del nuevo proyecto")
    parser.add_argument(
        "-t",
        "--template",
        default="short_quote_9_16",
        choices=list(AVAILABLE_TEMPLATES.keys()),
        help="Plantilla base a utilizar",
    )
    add_design_arguments(parser, default_design=DEFAULT_DESIGN)
    parser.add_argument("--title", help="Título principal para inyectar en el index.html")
    parser.add_argument(
        "--duration", type=float, help="Duración en segundos del video (data-duration)"
    )
    parser.add_argument(
        "-f", "--force", action="store_true", help="Sobrescribir si el directorio ya existe"
    )


def main() -> None:
    ensure_local_venv()
    parser = argparse.ArgumentParser(
        description="Scaffold de nuevos proyectos de video programático en HyperFrames"
    )
    register_scaffold_arguments(parser)
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
        motion=args.motion,
        caption_style=args.caption_style,
        overrides=parsed_overrides,
    )


if __name__ == "__main__":
    main()
