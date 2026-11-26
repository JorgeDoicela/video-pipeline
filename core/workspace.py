#!/usr/bin/env python3
"""
Capa de gestión de Workspace, Perfiles de Canal/Cliente e Historial de Producciones.

Desacopla el motor (video-pipeline) de la organización de producciones multi-canal y clientes:
  - Perfiles declarativos (profiles/*.json): encapsulan plantilla, diseño, tema, layout,
    motion, overrides, música, limpieza vocal y glosario técnico por canal o cliente.
  - Organización jerárquica de proyectos: <workspace>/<canal>/<fecha>_<slug>/ con soporte
    para workspace local (projects/) o repositorio externo (VIDEO_PIPELINE_WORKSPACE / --output-dir).
  - Historial append-only (catalog.jsonl): trazabilidad liviana y sin conflictos de merge
    de cada proyecto creado, producido o renderizado.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core._runtime import REPO_ROOT, ensure_repo_root_on_path  # noqa: E402

ensure_repo_root_on_path()

from core._styles_catalog import (  # noqa: E402
    CAPTION_STYLES,
    DEFAULT_DESIGN,
    DESIGN_SYSTEMS,
    LAYOUT_VARIANTS,
    MOTION_PROFILES,
    THEMES,
)
from core._styles_renderer import parse_set_overrides  # noqa: E402

WORKSPACE_ENV_VAR = "VIDEO_PIPELINE_WORKSPACE"
PROFILES_DIR = REPO_ROOT / "profiles"
CATALOG_FILENAME = "catalog.jsonl"
VALID_TEMPLATES: tuple[str, ...] = (
    "explainer_scenes_9_16",
    "explainer_scenes_16_9",
    "short_quote_9_16",
    "short_tech_9_16",
    "talking_head_9_16",
    "editorial_16_9",
    "talking_head_16_9",
)


@dataclass(frozen=True)
class ChannelProfile:
    """Especificación inmutable y reutilizable de identidad audiovisual para un canal o cliente."""

    slug: str
    name: str
    description: str = ""
    channel: str = ""
    template: str = "explainer_scenes_9_16"
    design: str = DEFAULT_DESIGN
    style: str | None = None
    layout: str | None = None
    motion: str | None = None
    caption_style: str | None = None
    overrides: dict[str, str] = field(default_factory=dict)
    brand: str = ""
    category: str = ""
    music: str | None = None
    music_volume: float = 0.14
    ambient_bed: bool = False
    voice_polish: bool = False
    words_per_group: int | None = None
    whisper_model: str = "base"
    language: str = "es"
    whisper_prompt: str | None = None
    whisper_hotwords: str | None = None
    replacements: dict[str, str] = field(default_factory=dict)
    output_root: str | None = None


def sanitize_slug(raw: str, label: str = "identificador") -> str:
    """Convierte un nombre arbitrario en un slug seguro para directorios y archivos."""
    slug = re.sub(r"[^a-zA-Z0-9_\-]+", "-", raw.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        raise ValueError(f"El {label} '{raw}' no contiene caracteres alfanuméricos válidos.")
    return slug


def sanitize_channel_path(raw_channel: str | None) -> Path | None:
    """
    Valida y normaliza una ruta relativa de canal/cliente (ej. 'tech', 'clientes/acme').
    Impide rutas absolutas y path traversal ('..').
    """
    if not raw_channel or not raw_channel.strip():
        return None
    normalized = raw_channel.strip().replace("\\", "/")
    if normalized.startswith("/") or re.match(r"^[a-zA-Z]:", normalized):
        raise ValueError(
            f"El canal '{raw_channel}' debe ser una ruta relativa (ej. 'tech' o 'clientes/acme')."
        )
    segments: list[str] = []
    for part in normalized.split("/"):
        cleaned = part.strip()
        if not cleaned or cleaned == ".":
            continue
        if cleaned == "..":
            raise ValueError(
                f"El canal '{raw_channel}' no puede contener '..' (path traversal bloqueado)."
            )
        segments.append(sanitize_slug(cleaned, label="segmento de canal"))
    if not segments:
        return None
    return Path(*segments)


def format_project_slug(name: str, dated: bool = False, ref_date: date | None = None) -> str:
    """Normaliza el slug del proyecto y opcionalmente antepone prefijo YYYY-MM-DD_."""
    slug = sanitize_slug(name, label="nombre del proyecto")
    if not dated:
        return slug
    if re.match(r"^\d{4}-\d{2}-\d{2}[-_]", slug):
        return slug
    today = ref_date or date.today()
    return f"{today.isoformat()}_{slug}"


def resolve_workspace_root(
    output_dir: str | Path | None = None,
    profile_output_root: str | None = None,
    base_dir: Path | None = None,
) -> Path:
    """
    Resuelve el directorio raíz donde se almacenan los proyectos:
      1. --output-dir explícito en CLI
      2. output_root definido en el perfil de canal
      3. Variable de entorno VIDEO_PIPELINE_WORKSPACE
      4. Directorio projects/ local del repositorio (defecto retrocompatible)
    """
    root_base = base_dir or REPO_ROOT
    candidate = output_dir or profile_output_root or os.environ.get(WORKSPACE_ENV_VAR)
    if candidate:
        path = Path(candidate).expanduser()
        if not path.is_absolute():
            path = (root_base / path).resolve()
        return path
    return root_base / "projects"


def infer_workspace_root_from_project(project_dir: Path, channel: str | None = None) -> Path:
    """
    Infere el directorio raíz del workspace al que pertenece un proyecto existente
    a partir de su ruta y su canal declarado (ej. '<ws>/clientes/acme/<slug>' -> '<ws>').
    """
    resolved = project_dir.resolve()
    channel_rel = sanitize_channel_path(channel)
    depth = len(channel_rel.parts) if channel_rel else 0
    parent = resolved.parent
    for _ in range(depth):
        parent = parent.parent
    return parent


def _validate_profile_payload(data: dict[str, Any], fallback_slug: str) -> ChannelProfile:
    """Valida el esquema y los tokens declarados en un archivo JSON de perfil de canal."""
    slug = sanitize_slug(str(data.get("slug") or fallback_slug), label="slug de perfil")
    name = str(data.get("name") or slug).strip()
    template = str(data.get("template") or "explainer_scenes_9_16").strip()
    if template not in VALID_TEMPLATES:
        raise ValueError(
            f"Perfil '{slug}': plantilla '{template}' inválida. "
            f"Opciones: {', '.join(VALID_TEMPLATES)}."
        )
    design = str(data.get("design") or DEFAULT_DESIGN).strip()
    if design not in DESIGN_SYSTEMS:
        raise ValueError(
            f"Perfil '{slug}': diseño '{design}' inválido. Opciones: {', '.join(DESIGN_SYSTEMS)}."
        )

    style = data.get("style")
    if style is not None and style not in THEMES:
        raise ValueError(
            f"Perfil '{slug}': tema '{style}' inválido. Opciones: {', '.join(THEMES)}."
        )

    layout = data.get("layout")
    if layout is not None and layout not in LAYOUT_VARIANTS:
        raise ValueError(
            f"Perfil '{slug}': layout '{layout}' inválido. Opciones: {', '.join(LAYOUT_VARIANTS)}."
        )

    motion = data.get("motion")
    if motion is not None and motion not in MOTION_PROFILES:
        raise ValueError(
            f"Perfil '{slug}': motion '{motion}' inválido. Opciones: {', '.join(MOTION_PROFILES)}."
        )

    caption_style = data.get("caption_style")
    if caption_style is not None and caption_style not in CAPTION_STYLES:
        raise ValueError(
            f"Perfil '{slug}': caption_style '{caption_style}' inválido. "
            f"Opciones: {', '.join(CAPTION_STYLES)}."
        )

    raw_overrides = data.get("overrides") or {}
    if not isinstance(raw_overrides, dict):
        raise ValueError(f"Perfil '{slug}': 'overrides' debe ser un objeto JSON clave-valor.")
    validated_overrides = parse_set_overrides([f"{k}={v}" for k, v in raw_overrides.items()])

    raw_replacements = data.get("replacements") or {}
    if not isinstance(raw_replacements, dict):
        raise ValueError(f"Perfil '{slug}': 'replacements' debe ser un objeto JSON clave-valor.")
    replacements = {
        str(k).strip(): str(v).strip()
        for k, v in raw_replacements.items()
        if str(k).strip() and str(v).strip()
    }

    channel_raw = str(data.get("channel") or "").strip()
    channel_path = sanitize_channel_path(channel_raw)
    channel_str = channel_path.as_posix() if channel_path else ""

    wpg = data.get("words_per_group")
    if wpg is not None:
        wpg = int(wpg)
        if wpg <= 0:
            raise ValueError(f"Perfil '{slug}': 'words_per_group' debe ser mayor a 0.")

    return ChannelProfile(
        slug=slug,
        name=name,
        description=str(data.get("description") or "").strip(),
        channel=channel_str,
        template=str(data.get("template") or "explainer_scenes_9_16").strip(),
        design=design,
        style=str(style) if style is not None else None,
        layout=str(layout) if layout is not None else None,
        motion=str(motion) if motion is not None else None,
        caption_style=str(caption_style) if caption_style is not None else None,
        overrides=validated_overrides,
        brand=str(data.get("brand") or "").strip(),
        category=str(data.get("category") or "").strip(),
        music=str(data["music"]).strip() if data.get("music") else None,
        music_volume=float(data.get("music_volume", 0.14)),
        ambient_bed=bool(data.get("ambient_bed", False)),
        voice_polish=bool(data.get("voice_polish", False)),
        words_per_group=wpg,
        whisper_model=str(data.get("whisper_model") or "base").strip(),
        language=str(data.get("language") or "es").strip(),
        whisper_prompt=str(data["whisper_prompt"]).strip() if data.get("whisper_prompt") else None,
        whisper_hotwords=(
            str(data["whisper_hotwords"]).strip() if data.get("whisper_hotwords") else None
        ),
        replacements=replacements,
        output_root=str(data["output_root"]).strip() if data.get("output_root") else None,
    )


def resolve_profile_path(profile_ref: str | Path, profiles_dir: Path | None = None) -> Path:
    """Resuelve un slug de perfil ('tech_short') o ruta directa a archivo .json."""
    ref_path = Path(profile_ref)
    if ref_path.is_file():
        return ref_path

    base = profiles_dir or PROFILES_DIR
    slug = str(profile_ref).removesuffix(".json")
    candidate = base / f"{slug}.json"
    if candidate.is_file():
        return candidate

    available = [p.stem for p in sorted(base.glob("*.json"))] if base.exists() else []
    hint = f" Disponibles: {', '.join(available)}." if available else ""
    raise FileNotFoundError(f"No se encontró el perfil de canal '{profile_ref}'.{hint}")


def load_profile(profile_ref: str | Path, profiles_dir: Path | None = None) -> ChannelProfile:
    """Carga y valida un perfil de canal desde profiles/<slug>.json o ruta directa."""
    path = resolve_profile_path(profile_ref, profiles_dir=profiles_dir)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON inválido en perfil '{path}': {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"El perfil '{path}' debe contener un objeto JSON en la raíz.")
    return _validate_profile_payload(data, fallback_slug=path.stem)


def list_profiles(profiles_dir: Path | None = None) -> list[ChannelProfile]:
    """Devuelve todos los perfiles válidos registrados en profiles/."""
    base = profiles_dir or PROFILES_DIR
    if not base.exists():
        return []
    return [load_profile(p, profiles_dir=base) for p in sorted(base.glob("*.json"))]


def save_profile(
    profile: ChannelProfile,
    profiles_dir: Path | None = None,
    force: bool = False,
) -> Path:
    """Persiste un perfil de canal validado en profiles/<slug>.json."""
    base = profiles_dir or PROFILES_DIR
    base.mkdir(parents=True, exist_ok=True)
    target = base / f"{profile.slug}.json"
    if target.exists() and not force:
        raise FileExistsError(
            f"El perfil '{profile.slug}' ya existe en {target}. Usa --force para sobrescribir."
        )
    payload = asdict(profile)
    # Validar de nuevo antes de escribir
    _validate_profile_payload(payload, fallback_slug=profile.slug)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def record_history_event(
    workspace_root: Path,
    *,
    action: str,
    project_slug: str,
    project_dir: Path,
    channel: str | None = None,
    profile: str | None = None,
    title: str | None = None,
    template: str | None = None,
    design: str | None = None,
    style: str | None = None,
    layout: str | None = None,
    motion: str | None = None,
    duration: float | None = None,
    output_video: Path | str | None = None,
    status: str = "ok",
) -> Path:
    """Registra un evento estructurado en <workspace_root>/catalog.jsonl (append-only)."""
    workspace_root.mkdir(parents=True, exist_ok=True)
    catalog_path = workspace_root / CATALOG_FILENAME

    try:
        rel_dir = project_dir.resolve().relative_to(workspace_root.resolve()).as_posix()
    except ValueError:
        rel_dir = str(project_dir.resolve())

    entry: dict[str, Any] = {
        "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "action": action,
        "status": status,
        "project": project_slug,
        "channel": channel or "",
        "profile": profile or "",
        "title": title or "",
        "template": template or "",
        "design": design or "",
        "style": style or "",
        "layout": layout or "",
        "motion": motion or "",
        "duration": round(duration, 2) if duration is not None else None,
        "project_dir": rel_dir,
        "output_video": str(output_video) if output_video else "",
    }
    with open(catalog_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return catalog_path


def load_history(
    workspace_root: Path,
    channel: str | None = None,
    profile: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Lee y filtra el historial de producciones desde catalog.jsonl (orden más reciente primero)."""
    catalog_path = workspace_root / CATALOG_FILENAME
    if not catalog_path.exists():
        return []

    records: list[dict[str, Any]] = []
    for line in catalog_path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            item = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if channel and item.get("channel") != channel:
            continue
        if profile and item.get("profile") != profile:
            continue
        records.append(item)

    records.reverse()
    if limit is not None and limit > 0:
        return records[:limit]
    return records


def print_profiles_table(profiles: list[ChannelProfile], as_json: bool = False) -> None:
    if as_json:
        print(json.dumps([asdict(p) for p in profiles], indent=2, ensure_ascii=False))
        return
    if not profiles:
        print("No hay perfiles registrados en profiles/. Crea uno con 'pipeline.py profiles init'.")
        return
    print("\n=== PERFILES DE CANAL / CLIENTE (profiles/) ===")
    for p in profiles:
        ch = p.channel or "(raíz)"
        print(f"  * {p.slug:<20} : {p.name}")
        print(
            f"    Canal: {ch} | Plantilla: {p.template} | Diseño: {p.design}"
            + (f" / {p.style}" if p.style else "")
            + (f" | Música: {p.music}" if p.music else "")
        )
        if p.description:
            print(f"    Descripción: {p.description}")
    print()


def print_history_table(records: list[dict[str, Any]], as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(records, indent=2, ensure_ascii=False))
        return
    if not records:
        print("No hay registros en el historial todavía (catalog.jsonl).")
        return
    print("\n=== HISTORIAL DE PRODUCCIONES (más recientes primero) ===")
    for item in records:
        ts = item.get("timestamp", "")[:16].replace("T", " ")
        ch = item.get("channel") or "-"
        prof = item.get("profile") or "-"
        dur = f"{item['duration']}s" if item.get("duration") is not None else "-"
        print(
            f"  [{ts}] {item.get('action', ''):<8} | canal={ch:<14} | perfil={prof:<15} | "
            f"{item.get('project', '')} ({item.get('template', '')}, {item.get('design', '')}, {dur})"
        )
        if item.get("output_video"):
            print(f"    MP4: {item['output_video']}")
    print()


def register_profiles_subparsers(
    parser: argparse.ArgumentParser, dest: str = "profile_action"
) -> None:
    sub = parser.add_subparsers(dest=dest, help="Gestión de perfiles de canal y cliente")

    p_list = sub.add_parser("list", help="Listar perfiles registrados en profiles/")
    p_list.add_argument("--json", action="store_true", help="Exportar en formato JSON")

    p_show = sub.add_parser("show", help="Mostrar la configuración completa de un perfil")
    p_show.add_argument("profile", help="Slug del perfil o ruta a archivo .json")

    p_init = sub.add_parser("init", help="Crear un nuevo perfil de canal o cliente en profiles/")
    p_init.add_argument("slug", help="Identificador del perfil (ej. canal_ciber, cliente_acme)")
    p_init.add_argument("--name", help="Nombre legible del canal o cliente")
    p_init.add_argument("--description", default="", help="Descripción breve del perfil")
    p_init.add_argument(
        "--channel", default="", help="Subcarpeta de canal/cliente (ej. tech o clientes/acme)"
    )
    p_init.add_argument(
        "-t",
        "--template",
        default="explainer_scenes_9_16",
        choices=list(VALID_TEMPLATES),
        help="Plantilla base",
    )
    p_init.add_argument("-d", "--design", default=DEFAULT_DESIGN, choices=list(DESIGN_SYSTEMS))
    p_init.add_argument("-s", "--style", choices=list(THEMES))
    p_init.add_argument("--layout", choices=list(LAYOUT_VARIANTS))
    p_init.add_argument("--motion", choices=list(MOTION_PROFILES))
    p_init.add_argument("--caption-style", choices=list(CAPTION_STYLES))
    p_init.add_argument("--set", dest="overrides", action="append", metavar="CLAVE=VALOR")
    p_init.add_argument("--brand", default="", help="Firma de marca opcional")
    p_init.add_argument("--category", default="", help="Categoría temática opcional")
    p_init.add_argument("--music", help="Preset musical o ruta de pista por defecto")
    p_init.add_argument("--music-volume", type=float, default=0.14)
    p_init.add_argument("--ambient-bed", action="store_true")
    p_init.add_argument("--voice-polish", action="store_true")
    p_init.add_argument("--words-per-group", type=int, default=None)
    p_init.add_argument("--output-root", help="Directorio/repo externo donde guardar este canal")
    p_init.add_argument("-f", "--force", action="store_true", help="Sobrescribir si ya existe")


def dispatch_profiles_action(args: argparse.Namespace, action_attr: str = "profile_action") -> None:
    action = getattr(args, action_attr, None)
    try:
        if not action or action == "list":
            print_profiles_table(list_profiles(), as_json=getattr(args, "json", False))
            return
        if action == "show":
            profile = load_profile(args.profile)
            print(json.dumps(asdict(profile), indent=2, ensure_ascii=False))
            return
        if action == "init":
            parsed_overrides = parse_set_overrides(args.overrides)
            slug = sanitize_slug(args.slug, label="slug de perfil")
            ch_path = sanitize_channel_path(args.channel)
            profile = ChannelProfile(
                slug=slug,
                name=(args.name or slug).strip(),
                description=args.description.strip(),
                channel=ch_path.as_posix() if ch_path else "",
                template=args.template,
                design=args.design,
                style=args.style,
                layout=args.layout,
                motion=args.motion,
                caption_style=args.caption_style,
                overrides=parsed_overrides,
                brand=args.brand.strip(),
                category=args.category.strip(),
                music=args.music,
                music_volume=args.music_volume,
                ambient_bed=args.ambient_bed,
                voice_polish=args.voice_polish,
                words_per_group=args.words_per_group,
                output_root=args.output_root,
            )
            saved = save_profile(profile, force=args.force)
            print(f"[Profiles] Perfil '{profile.slug}' guardado en: {saved}")
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
