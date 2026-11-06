#!/usr/bin/env python3
"""
Scaffolding automatizado de proyectos de video a partir de plantillas optimizadas.
Copia la plantilla seleccionada, personaliza metadatos y prepara el entorno para HyperFrames.
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

AVAILABLE_TEMPLATES = {
    "portrait_9_16": "Formato vertical 9:16 (1080x1920) para TikTok, Instagram Reels y YouTube Shorts",
    "landscape_16_9": "Formato horizontal 16:9 (1920x1080) para YouTube y presentaciones widescreen",
    "square_1_1": "Formato cuadrado 1:1 (1080x1080) para feeds de LinkedIn, Twitter e Instagram",
    "talking_head": "Video con presentador, lower-third animado y subtítulos cinéticos sincronizados",
    "tech_explainer": "Diagramas de arquitectura SVG interactivos con nodos animados y flujo de paquetes",
}


def sanitize_project_name(name: str) -> str:
    """Convierte el nombre en un slug válido para directorios y package.json."""
    slug = re.sub(r"[^a-zA-Z0-9_\-]+", "-", name.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        raise ValueError("El nombre del proyecto no contiene caracteres alfanuméricos válidos.")
    return slug


def create_project(
    name: str,
    template: str = "portrait_9_16",
    title: str | None = None,
    duration: float | None = None,
    force: bool = False,
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

    # Actualizar package.json con el nombre del proyecto
    pkg_file = target_path / "package.json"
    if pkg_file.exists():
        try:
            with open(pkg_file, encoding="utf-8") as f:
                pkg_data = json.load(f)
            pkg_data["name"] = f"project-{project_slug}"
            with open(pkg_file, "w", encoding="utf-8") as f:
                json.dump(pkg_data, f, indent=2)
                f.write("\n")
        except (OSError, json.JSONDecodeError) as e:
            print(f"Advertencia al actualizar package.json: {e}", file=sys.stderr)

    # Personalizar index.html (título y duración)
    html_file = target_path / "index.html"
    if html_file.exists():
        html_content = html_file.read_text(encoding="utf-8")

        if duration is not None:
            html_content = re.sub(
                r'data-duration="[0-9.]+"',
                f'data-duration="{duration}"',
                html_content,
                count=1,
            )

        if title and "<h1" in html_content:
            # Reemplazar título h1 o título principal si existe
            html_content = re.sub(
                r"(<h1[^>]*>).*?(</h1>)",
                rf"\g<1>{title}\g<2>",
                html_content,
                count=1,
                flags=re.DOTALL,
            )

        html_file.write_text(html_content, encoding="utf-8")

    print(f"[Scaffold] Proyecto '{project_slug}' creado con éxito en: {target_path}")
    print(f"[Scaffold] Plantilla base: {template}")
    print("\nComandos operativos:")
    print(f"  1. Vista previa interactiva : pnpm exec hyperframes preview projects/{project_slug}")
    print(f"  2. Validación de estándares : pnpm exec hyperframes check projects/{project_slug}")
    print(
        f"  3. Renderizado de producción: pnpm exec hyperframes render projects/{project_slug} -o projects/{project_slug}/video_{project_slug}.mp4"
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
    parser.add_argument("--title", help="Título principal para inyectar en el index.html")
    parser.add_argument(
        "--duration", type=float, help="Duración en segundos del video (data-duration)"
    )
    parser.add_argument(
        "-f", "--force", action="store_true", help="Sobrescribir si el directorio ya existe"
    )

    args = parser.parse_args()
    create_project(
        name=args.name,
        template=args.template,
        title=args.title,
        duration=args.duration,
        force=args.force,
    )


if __name__ == "__main__":
    main()
