#!/usr/bin/env python3
"""
Gestor y descargador determinista de activos abiertos (CC0 / MIT) para video-pipeline.

Conecta el pipeline bajo demanda con fuentes abiertas y gratuitas sin romper
el renderizado 100% offline, e incluye el catálogo base de 18 iconos técnicos vectoriales:
  1. Iconify API (Lucide, Tabler, Simple Icons — MIT/CC0, sin API Key) + 18 iconos semilla locales -> assets/icons/<slug>.svg
  2. Natural Earth GeoJSON (Dominio Público CC0, sin API Key) -> assets/maps/<slug>.svg
  3. Audio CC0 (URL directa o búsqueda en Freesound API v2 con filtro CC0) -> assets/audio/ o assets/music/ (WAV 48kHz 16-bit)
  4. Modelos 3D glTF/GLB (URL directa CC0 o importación local desde Blender/Poly Pizza/Sketchfab) -> assets/models/<slug>.glb|.gltf
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core._runtime import REPO_ROOT, ensure_local_venv, ensure_repo_root_on_path  # noqa: E402

ensure_repo_root_on_path()
_REPO_ROOT = REPO_ROOT

ICONIFY_API_BASE = "https://api.iconify.design"
NATURAL_EARTH_110M_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "master/geojson/ne_110m_admin_0_countries.geojson"
)
FREESOUND_SEARCH_URL = "https://freesound.org/apiv2/search/text/"

USER_AGENT = "video-pipeline-asset-fetcher/1.0 (local-deterministic-studio)"

BASE_ICONS: dict[str, str] = {
    "server": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <rect x="2" y="2" width="20" height="8" rx="2" ry="2"/>
  <rect x="2" y="14" width="20" height="8" rx="2" ry="2"/>
  <line x1="6" y1="6" x2="6.01" y2="6"/>
  <line x1="6" y1="18" x2="6.01" y2="18"/>
</svg>""",
    "database": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <ellipse cx="12" cy="5" rx="9" ry="3"/>
  <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
  <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
</svg>""",
    "cloud": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
</svg>""",
    "docker": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <path d="M4 10h2v2H4zM7 10h2v2H7zM10 10h2v2h-2zM7 7h2v2H7zM10 7h2v2h-2zM13 7h2v2h-2z"/>
  <path d="M22 13c-.5-1-1.5-1.5-2.5-1.5-.5 0-1 .2-1.5.5C17 9 14 8 11 8H2c-.5 0-1 .5-1 1 0 4 3 8 9 8 5.5 0 9.5-3 10.5-6.5.5.3 1 .5 1.5.5z"/>
</svg>""",
    "kubernetes": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <polygon points="12 2 21 7 21 17 12 22 3 17 3 7 12 2"/>
  <circle cx="12" cy="12" r="3"/>
  <line x1="12" y1="2" x2="12" y2="9"/>
  <line x1="12" y1="15" x2="12" y2="22"/>
  <line x1="21" y1="7" x2="15" y2="10.5"/>
  <line x1="3" y1="17" x2="9" y2="13.5"/>
  <line x1="21" y1="17" x2="15" y2="13.5"/>
  <line x1="3" y1="7" x2="9" y2="10.5"/>
</svg>""",
    "kafka": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="18" cy="5" r="3"/>
  <circle cx="6" cy="12" r="3"/>
  <circle cx="18" cy="19" r="3"/>
  <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/>
  <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
</svg>""",
    "redis": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <polygon points="12 2 2 7 12 12 22 7 12 2"/>
  <polyline points="2 12 12 17 22 12"/>
  <polyline points="2 17 12 22 22 17"/>
</svg>""",
    "git": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="18" cy="18" r="3"/>
  <circle cx="6" cy="6" r="3"/>
  <path d="M6 9a9 9 0 0 0 9 9"/>
  <line x1="6" y1="9" x2="6" y2="21"/>
</svg>""",
    "cpu": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <rect x="4" y="4" width="16" height="16" rx="2"/>
  <rect x="9" y="9" width="6" height="6"/>
  <line x1="9" y1="1" x2="9" y2="4"/>
  <line x1="15" y1="1" x2="15" y2="4"/>
  <line x1="9" y1="20" x2="9" y2="23"/>
  <line x1="15" y1="20" x2="15" y2="23"/>
  <line x1="20" y1="9" x2="23" y2="9"/>
  <line x1="20" y1="15" x2="23" y2="15"/>
  <line x1="1" y1="9" x2="4" y2="9"/>
  <line x1="1" y1="15" x2="4" y2="15"/>
</svg>""",
    "terminal": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="4 17 10 11 4 5"/>
  <line x1="12" y1="19" x2="20" y2="19"/>
</svg>""",
    "shield": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
</svg>""",
    "lock": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
  <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
</svg>""",
    "eye": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/>
  <circle cx="12" cy="12" r="3"/>
</svg>""",
    "globe": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="10"/>
  <line x1="2" y1="12" x2="22" y2="12"/>
  <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
</svg>""",
    "smartphone": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <rect x="5" y="2" width="14" height="20" rx="2" ry="2"/>
  <line x1="12" y1="18" x2="12.01" y2="18"/>
</svg>""",
    "alert": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>
  <line x1="12" y1="9" x2="12" y2="13"/>
  <line x1="12" y1="17" x2="12.01" y2="17"/>
</svg>""",
    "key": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="7.5" cy="15.5" r="5.5"/>
  <path d="m21 2-9.6 9.6"/>
  <path d="m15.5 7.5 3 3L22 7l-3-3"/>
</svg>""",
    "radar": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M19.07 4.93A10 10 0 0 0 6.99 3.34"/>
  <path d="M4 6h.01"/>
  <path d="M2.29 9.62A10 10 0 1 0 21.31 8.35"/>
  <path d="M16.24 7.76A6 6 0 1 0 8.23 16.67"/>
  <path d="M12 18h.01"/>
  <path d="M17.99 11.66A6 6 0 0 1 15.77 16.67"/>
  <circle cx="12" cy="12" r="2"/>
  <path d="m13.41 10.59 5.66-5.66"/>
</svg>""",
}


def ensure_base_icons(icons_dir: Path | None = None, force: bool = False) -> dict[str, Path]:
    """Garantiza que los 18 iconos técnicos vectoriales SVG semilla existan en assets/icons/."""
    target_dir = icons_dir or (_REPO_ROOT / "assets" / "icons")
    target_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for slug, svg_content in BASE_ICONS.items():
        file_path = target_dir / f"{slug}.svg"
        if not file_path.exists() or force:
            file_path.write_text(svg_content.strip() + "\n", encoding="utf-8")
            print(f"[Assets:Icon] Generado icono base: {file_path.name}")
        paths[slug] = file_path
    return paths


def _sanitize_slug(raw: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9_-]+", "-", raw.strip().lower()).strip("-")
    if not clean:
        raise ValueError(f"Identificador de asset inválido: '{raw}'")
    return clean


def _http_get_bytes(url: str, timeout: float = 15.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return resp.read()


def normalize_iconify_svg(raw_svg: str) -> str:
    """
    Limpia y estandariza un SVG de Iconify para cumplir con las restricciones visuales:
      - Cero cápsulas o fondos envolventes.
      - Dimensiones desacopladas (eliminando width/height fijos en <svg> y conservando viewBox).
      - Color adaptativo heredado del token de acento o currentColor.
    """
    svg = raw_svg.strip()
    if "<svg" not in svg.lower():
        raise ValueError("El contenido descargado no es un documento SVG válido.")
    svg = re.sub(r'\swidth="[^"]*"', "", svg, count=1)
    svg = re.sub(r'\sheight="[^"]*"', "", svg, count=1)
    return svg + "\n"


def fetch_icon(
    spec: str,
    name: str | None = None,
    icons_dir: Path | None = None,
    force: bool = False,
) -> Path:
    """
    Descarga un icono vectorial SVG desde Iconify (Lucide, Tabler, Simple Icons, etc.)
    y lo almacena en assets/icons/<slug>.svg.
    Formatos aceptados para spec:
      - 'shield-alert' (usa colección 'lucide' por defecto -> lucide:shield-alert)
      - 'lucide:cpu'
      - 'tabler:radar-2'
      - 'simple-icons:wireshark'
    """
    target_dir = icons_dir or (_REPO_ROOT / "assets" / "icons")
    target_dir.mkdir(parents=True, exist_ok=True)

    raw_spec = spec.strip()
    if ":" in raw_spec:
        prefix, icon_id = raw_spec.split(":", 1)
    elif "/" in raw_spec:
        prefix, icon_id = raw_spec.split("/", 1)
    else:
        prefix, icon_id = "lucide", raw_spec

    prefix = _sanitize_slug(prefix)
    icon_id = _sanitize_slug(icon_id)
    out_slug = _sanitize_slug(name) if name else icon_id
    out_path = target_dir / f"{out_slug}.svg"

    if out_path.exists() and not force:
        return out_path

    if prefix == "lucide" and icon_id in BASE_ICONS and not force:
        out_path.write_text(BASE_ICONS[icon_id].strip() + "\n", encoding="utf-8")
        print(f"[Assets:Icon] Generado desde catálogo base: {out_path.name}")
        return out_path

    url = f"{ICONIFY_API_BASE}/{prefix}/{icon_id}.svg"
    try:
        raw_bytes = _http_get_bytes(url)
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"No se pudo descargar el icono '{prefix}:{icon_id}' desde Iconify ({url}): {exc}"
        ) from exc

    raw_svg = raw_bytes.decode("utf-8", errors="replace")
    if "<svg" not in raw_svg:
        raise ValueError(
            f"El icono '{prefix}:{icon_id}' no existe en el catálogo de Iconify ({url})."
        )

    cleaned = normalize_iconify_svg(raw_svg)
    out_path.write_text(cleaned, encoding="utf-8")
    print(f"[Assets:Icon] Guardado: {out_path.name} ({prefix}:{icon_id})")
    return out_path


def _extract_polygons(geometry: dict[str, Any]) -> list[list[list[tuple[float, float]]]]:
    """Convierte geometrías GeoJSON Polygon o MultiPolygon en listas de anillos [(lon, lat), ...]."""
    g_type = geometry.get("type")
    coords = geometry.get("coordinates", [])
    polygons: list[list[list[tuple[float, float]]]] = []
    if g_type == "Polygon":
        poly = [[(float(pt[0]), float(pt[1])) for pt in ring] for ring in coords if len(ring) >= 3]
        if poly:
            polygons.append(poly)
    elif g_type == "MultiPolygon":
        for raw_poly in coords:
            poly = [
                [(float(pt[0]), float(pt[1])) for pt in ring] for ring in raw_poly if len(ring) >= 3
            ]
            if poly:
                polygons.append(poly)
    return polygons


def _match_feature(feature: dict[str, Any], query: str) -> bool:
    props = feature.get("properties") or {}
    q = query.strip().lower()
    candidates = [
        str(props.get("ISO_A3", "")),
        str(props.get("ISO_A2", "")),
        str(props.get("ADM0_A3", "")),
        str(props.get("NAME", "")),
        str(props.get("NAME_LONG", "")),
        str(props.get("ADMIN", "")),
        str(props.get("SOVEREIGNT", "")),
        str(props.get("CONTINENT", "")),
        str(props.get("REGION_UN", "")),
        str(props.get("SUBREGION", "")),
    ]
    for cand in candidates:
        c_low = cand.strip().lower()
        if c_low and (c_low == q or (len(q) >= 4 and q in c_low)):
            return True
    return False


def compile_geojson_to_radar_svg(
    geojson_data: dict[str, Any],
    primary_queries: list[str],
    context_queries: list[str] | None = None,
    view_width: int = 880,
    view_height: int = 680,
    padding: int = 85,
) -> str:
    """
    Proyecta polígonos reales GeoJSON (Natural Earth CC0) al sistema de coordenadas
    viewBox="0 0 880 680" de radar_map aplicando los tokens CSS del sistema.
    """
    features = geojson_data.get("features") or []
    primary_polys: list[list[list[tuple[float, float]]]] = []
    context_polys: list[list[list[tuple[float, float]]]] = []

    ctx_list = [q.strip() for q in (context_queries or []) if q.strip()]
    pri_list = [q.strip() for q in primary_queries if q.strip()]

    for feat in features:
        geom = feat.get("geometry") or {}
        if any(_match_feature(feat, q) for q in pri_list):
            primary_polys.extend(_extract_polygons(geom))
        elif ctx_list and any(_match_feature(feat, q) for q in ctx_list):
            context_polys.extend(_extract_polygons(geom))

    if not primary_polys:
        raise ValueError(
            f"No se encontraron fronteras geográficas en GeoJSON para: {', '.join(pri_list)}"
        )

    all_polys = primary_polys + context_polys
    all_points = [pt for poly in all_polys for ring in poly for pt in ring]
    min_lon = min(pt[0] for pt in all_points)
    max_lon = max(pt[0] for pt in all_points)
    min_lat = min(pt[1] for pt in all_points)
    max_lat = max(pt[1] for pt in all_points)

    lon_span = max(0.01, max_lon - min_lon)
    lat_span = max(0.01, max_lat - min_lat)
    avail_w = view_width - 2 * padding
    avail_h = view_height - 2 * padding
    scale = min(avail_w / lon_span, avail_h / lat_span)

    proj_w = lon_span * scale
    proj_h = lat_span * scale
    offset_x = (view_width - proj_w) / 2.0
    offset_y = (view_height - proj_h) / 2.0

    def _project(lon: float, lat: float) -> tuple[float, float]:
        x = offset_x + (lon - min_lon) * scale
        y = offset_y + (max_lat - lat) * scale
        return round(x, 1), round(y, 1)

    def _polys_to_path_d(polys: list[list[list[tuple[float, float]]]]) -> str:
        commands: list[str] = []
        for poly in polys:
            for ring in poly:
                pts = [_project(lon, lat) for lon, lat in ring]
                # Simplificación por distancia mínima en píxeles para SVG limpio
                filtered: list[tuple[float, float]] = []
                for pt in pts:
                    if (
                        not filtered
                        or (abs(pt[0] - filtered[-1][0]) + abs(pt[1] - filtered[-1][1])) >= 2.0
                    ):
                        filtered.append(pt)
                if len(filtered) < 3:
                    filtered = pts[:3]
                seg = " L ".join(f"{x} {y}" for x, y in filtered)
                commands.append(f"M {seg} Z")
        return " ".join(commands)

    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {view_width} {view_height}">'
    ]
    if context_polys:
        ctx_d = _polys_to_path_d(context_polys)
        if ctx_d:
            svg_lines.append(
                f'  <path d="{ctx_d}" fill="rgba(148,163,184,0.14)" stroke="var(--border-strong)" '
                f'stroke-width="2.5" stroke-linejoin="round" />'
            )

    pri_d = _polys_to_path_d(primary_polys)
    svg_lines.append(
        f'  <path d="{pri_d}" fill="var(--accent-primary-soft)" '
        f'stroke="var(--scene-accent, var(--accent-danger))" stroke-width="4" stroke-linejoin="round" />'
    )
    svg_lines.append("</svg>\n")
    return "\n".join(svg_lines)


def fetch_map(
    country_queries: str | list[str],
    name: str | None = None,
    context_queries: str | list[str] | None = None,
    maps_dir: Path | None = None,
    geojson_source: Path | str | None = None,
    force: bool = False,
) -> Path:
    """
    Compila un mapa vectorial SVG en assets/maps/<slug>.svg a partir de fronteras reales
    de Natural Earth (CC0 Dominio Público).
    """
    target_dir = maps_dir or (_REPO_ROOT / "assets" / "maps")
    target_dir.mkdir(parents=True, exist_ok=True)

    if isinstance(country_queries, str):
        pri_list = [q.strip() for q in country_queries.split(",") if q.strip()]
    else:
        pri_list = [str(q).strip() for q in country_queries if str(q).strip()]

    if not pri_list:
        raise ValueError(
            "Debes especificar al menos un país o código ISO (ej. 'PRK' o 'North Korea')."
        )

    if isinstance(context_queries, str):
        ctx_list = [q.strip() for q in context_queries.split(",") if q.strip()]
    elif context_queries:
        ctx_list = [str(q).strip() for q in context_queries if str(q).strip()]
    else:
        ctx_list = []

    out_slug = _sanitize_slug(name if name else pri_list[0])
    out_path = target_dir / f"{out_slug}.svg"
    if out_path.exists() and not force:
        return out_path

    if geojson_source and Path(str(geojson_source)).exists():
        raw_json = Path(str(geojson_source)).read_text(encoding="utf-8")
    else:
        url = str(geojson_source) if geojson_source else NATURAL_EARTH_110M_URL
        try:
            raw_json = _http_get_bytes(url, timeout=20.0).decode("utf-8")
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"No se pudo descargar el dataset GeoJSON de Natural Earth ({url}): {exc}"
            ) from exc

    geojson_data = json.loads(raw_json)
    svg_content = compile_geojson_to_radar_svg(
        geojson_data=geojson_data,
        primary_queries=pri_list,
        context_queries=ctx_list,
    )
    out_path.write_text(svg_content, encoding="utf-8")
    print(f"[Assets:Map] Generado mapa vectorial real: {out_path.name} ({', '.join(pri_list)})")
    return out_path


def build_audio_normalize_command(
    input_path: Path,
    output_path: Path,
    max_duration: float | None = None,
) -> list[str]:
    """
    Construye el comando FFmpeg determinista para convertir cualquier muestra de audio CC0
    a WAV PCM estéreo 48,000 Hz 16-bit con limitación segura de picos.
    """
    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    cmd = [
        ffmpeg_bin,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(input_path),
    ]
    if max_duration is not None and max_duration > 0:
        cmd.extend(["-t", f"{max_duration:.3f}"])
    cmd.extend(
        [
            "-af",
            "alimiter=limit=0.92",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]
    )
    return cmd


def _resolve_freesound_preview_url(query: str, api_key: str) -> str:
    """Consulta Freesound API v2 filtrando estrictamente por licencia Creative Commons 0 (CC0)."""
    params = urllib.parse.urlencode(
        {
            "query": query,
            "filter": 'license:"Creative Commons 0"',
            "fields": "id,name,previews,license,duration",
            "page_size": "5",
            "token": api_key,
        }
    )
    url = f"{FREESOUND_SEARCH_URL}?{params}"
    raw = _http_get_bytes(url, timeout=15.0).decode("utf-8")
    payload = json.loads(raw)
    results = payload.get("results") or []
    if not results:
        raise ValueError(f"No se encontraron sonidos CC0 en Freesound para la búsqueda: '{query}'")
    previews = results[0].get("previews") or {}
    preview_url = previews.get("preview-hq-ogg") or previews.get("preview-hq-mp3")
    if not preview_url:
        raise ValueError(f"El resultado CC0 '{results[0].get('name')}' no incluye URL de preview.")
    return str(preview_url)


def fetch_audio_cc0(
    name: str,
    url: str | None = None,
    freesound_query: str | None = None,
    kind: str = "sfx",
    target_dir: Path | None = None,
    max_duration: float | None = None,
    api_key: str | None = None,
    force: bool = False,
) -> Path:
    """
    Descarga un efecto de sonido o pista musical CC0 (desde URL directa o Freesound API v2 CC0)
    y lo normaliza con FFmpeg a WAV PCM 48kHz 16-bit estéreo en assets/audio/ o assets/music/.
    """
    if kind not in {"sfx", "music"}:
        raise ValueError("El parámetro 'kind' debe ser 'sfx' o 'music'.")

    default_dir = _REPO_ROOT / "assets" / ("music" if kind == "music" else "audio")
    dest_dir = target_dir or default_dir
    dest_dir.mkdir(parents=True, exist_ok=True)

    out_slug = _sanitize_slug(name)
    out_path = dest_dir / f"{out_slug}.wav"
    if out_path.exists() and not force:
        return out_path

    effective_url = url
    if not effective_url:
        if not freesound_query:
            raise ValueError(
                "Debes proporcionar --url <url_directa_cc0> o --freesound <busqueda_cc0>."
            )
        resolved_key = api_key or os.environ.get("FREESOUND_API_KEY", "").strip()
        if not resolved_key:
            raise RuntimeError(
                "Para buscar en Freesound API v2 define la variable de entorno FREESOUND_API_KEY "
                "o utiliza --url con un enlace directo a un archivo de audio CC0."
            )
        effective_url = _resolve_freesound_preview_url(freesound_query, resolved_key)

    raw_bytes = _http_get_bytes(effective_url, timeout=25.0)
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_in = Path(tmp_dir) / "download_raw.audio"
        tmp_in.write_bytes(raw_bytes)
        cmd = build_audio_normalize_command(tmp_in, out_path, max_duration=max_duration)
        subprocess.run(cmd, check=True)

    print(f"[Assets:Audio] Normalizado WAV 48kHz 16-bit ({kind}): {out_path.name}")
    return out_path


BASE_BLENDER_MODELS: dict[str, str] = {
    "shield_3d": """
import bpy, bmesh, math
bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=1.15, depth=0.22, location=(0, 0, 0.1))
obj = bpy.context.active_object
obj.rotation_euler = (math.radians(90), 0, 0)
obj.scale = (0.95, 1.25, 1.0)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bev = obj.modifiers.new(name="Bevel", type='BEVEL')
bev.width = 0.08
bev.segments = 2
bpy.ops.object.modifier_apply(modifier=bev.name)
""",
    "gear_3d": """
import bpy, math
bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=1.1, depth=0.32, location=(0, 0, 0))
gear = bpy.context.active_object
gear.rotation_euler = (math.radians(90), 0, 0)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.42, depth=0.8, location=(0, 0, 0))
cutter = bpy.context.active_object
cutter.rotation_euler = (math.radians(90), 0, 0)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
mod = gear.modifiers.new(name="Hole", type='BOOLEAN')
mod.operation = 'DIFFERENCE'
mod.object = cutter
bpy.context.view_layer.objects.active = gear
bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.data.objects.remove(cutter, do_unlink=True)
for i in range(8):
    ang = i * (math.pi / 4.0)
    bpy.ops.mesh.primitive_cube_add(size=0.32, location=(math.cos(ang) * 1.12, 0, math.sin(ang) * 1.12))
    t = bpy.context.active_object
    t.rotation_euler = (0, -ang, 0)
""",
    "crown_3d": """
import bpy, math
bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=1.05, depth=0.36, location=(0, 0, -0.25))
base = bpy.context.active_object
bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.92, depth=0.5, location=(0, 0, -0.25))
inner = bpy.context.active_object
mod = base.modifiers.new(name="Hollow", type='BOOLEAN')
mod.operation = 'DIFFERENCE'
mod.object = inner
bpy.context.view_layer.objects.active = base
bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.data.objects.remove(inner, do_unlink=True)
for i in range(6):
    ang = i * (math.pi / 3.0)
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=0.22, radius2=0.02, depth=0.55, location=(math.cos(ang) * 0.98, math.sin(ang) * 0.98, 0.2))
""",
    "open_book_3d": """
import bpy, math
for side in (-1, 1):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(side * 0.62, 0, 0.08 * abs(side)))
    page = bpy.context.active_object
    page.scale = (0.58, 0.82, 0.08)
    page.rotation_euler = (0, side * math.radians(-14), 0)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bev = page.modifiers.new(name="Bevel", type='BEVEL')
    bev.width = 0.025
    bev.segments = 2
    bpy.ops.object.modifier_apply(modifier=bev.name)
bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.1, depth=1.64, location=(0, 0, -0.02))
spine = bpy.context.active_object
spine.rotation_euler = (math.radians(90), 0, 0)
""",
    "lock_3d": """
import bpy, math
bpy.ops.mesh.primitive_cube_add(size=1.2, location=(0, 0, -0.35))
body = bpy.context.active_object
body.scale = (0.95, 0.45, 0.82)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bev = body.modifiers.new(name="Bevel", type='BEVEL')
bev.width = 0.09
bev.segments = 2
bpy.ops.object.modifier_apply(modifier=bev.name)
bpy.ops.mesh.primitive_torus_add(major_radius=0.52, minor_radius=0.11, major_segments=20, minor_segments=10, location=(0, 0, 0.45))
shackle = bpy.context.active_object
shackle.rotation_euler = (math.radians(90), 0, 0)
""",
    "globe_3d": """
import bpy, math
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.95, location=(0, 0, 0))
bpy.ops.mesh.primitive_torus_add(major_radius=1.28, minor_radius=0.035, major_segments=32, minor_segments=8, location=(0, 0, 0))
r1 = bpy.context.active_object
r1.rotation_euler = (math.radians(28), math.radians(15), 0)
bpy.ops.mesh.primitive_torus_add(major_radius=1.36, minor_radius=0.03, major_segments=32, minor_segments=8, location=(0, 0, 0))
r2 = bpy.context.active_object
r2.rotation_euler = (math.radians(-52), math.radians(-20), 0)
""",
}


def resolve_blender() -> str:
    """
    Resuelve el ejecutable de Blender de forma multiplataforma (Linux, Windows, macOS):
      1. Variable de entorno BLENDER_BIN.
      2. Binario 'blender' en PATH (cubre apt /usr/bin/blender, Nix Flakes / Home Manager, Snap).
      3. Rutas estándar de Linux (/opt/blender*/blender, Nix profiles, Flatpak, ~/.local/bin).
      4. Rutas estándar de Windows (C:\\Program Files\\Blender Foundation\\Blender *\\blender.exe).
      5. Ruta estándar de macOS (/Applications/Blender.app/Contents/MacOS/Blender).
    """
    env_bin = os.environ.get("BLENDER_BIN", "").strip()
    if env_bin and Path(env_bin).exists():
        return str(Path(env_bin).resolve())

    path_bin = shutil.which("blender")
    if path_bin:
        return path_bin

    candidates: list[Path] = []
    home = Path.home()

    # Rutas frecuentes en Linux (Debian, Nix Flakes / Home Manager, tarballs en /opt, Flatpak, Snap)
    candidates.extend(
        [
            home / ".nix-profile" / "bin" / "blender",
            Path("/run/current-system/sw/bin/blender"),
            home / ".local" / "bin" / "blender",
            Path("/usr/local/bin/blender"),
            Path("/usr/bin/blender"),
            Path("/snap/bin/blender"),
            Path("/var/lib/flatpak/exports/bin/org.blender.Blender"),
            home / ".local" / "share" / "flatpak" / "exports" / "bin" / "org.blender.Blender",
        ]
    )
    opt_dir = Path("/opt")
    if opt_dir.exists():
        candidates.extend(sorted(opt_dir.glob("blender*/blender"), reverse=True))
    local_share = home / ".local" / "share"
    if local_share.exists():
        candidates.extend(sorted(local_share.glob("blender*/blender"), reverse=True))

    # Rutas estándar en Windows
    prog_files = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Blender Foundation"
    if prog_files.exists():
        candidates.extend(sorted(prog_files.glob("Blender*/blender.exe"), reverse=True))

    # Ruta estándar en macOS
    mac_bin = Path("/Applications/Blender.app/Contents/MacOS/Blender")
    if mac_bin.exists():
        candidates.append(mac_bin)

    for cand in candidates:
        if cand.exists() and cand.is_file():
            return str(cand.resolve())

    raise FileNotFoundError(
        "No se encontró 'blender' en PATH ni en ubicaciones estándar de Linux (/usr/bin, /opt, Nix, Flatpak), "
        "Windows ('C:\\Program Files\\Blender Foundation') o macOS. "
        "Instala Blender (ej. 'sudo apt install blender' o Nix 'pkgs.blender') o define BLENDER_BIN."
    )


def compile_blender_to_glb(
    name: str,
    blender_script: str | Path | None = None,
    blender_code: str | None = None,
    input_mesh: str | Path | None = None,
    decimate_ratio: float | None = None,
    models_dir: Path | None = None,
    force: bool = False,
) -> Path:
    """
    Ejecuta Blender en modo headless (--background --factory-startup) para compilar un script bpy
    o convertir/normalizar un archivo 3D (.blend, .obj, .fbx, .stl, .ply, .glb) a glTF Binary (.glb)
    en assets/models/<slug>.glb con orientación +Y Up, centrado en origen y decimación opcional.
    """
    target_dir = models_dir or (_REPO_ROOT / "assets" / "models")
    target_dir.mkdir(parents=True, exist_ok=True)
    slug = _sanitize_slug(name)
    out_path = target_dir / f"{slug}.glb"
    if out_path.exists() and not force:
        print(f"[Assets:Blender] En caché local: {out_path.name}")
        return out_path

    blender_bin = resolve_blender()
    user_code = ""
    if blender_script is not None:
        script_p = Path(blender_script).resolve()
        if not script_p.exists():
            raise FileNotFoundError(f"No se encontró el script de Blender: {script_p}")
        user_code = script_p.read_text(encoding="utf-8")
    elif blender_code is not None:
        user_code = blender_code
    elif input_mesh is None:
        raise ValueError(
            "Debes especificar 'blender_script', 'blender_code' o 'input_mesh' para compilar con Blender."
        )

    mesh_path_str = str(Path(input_mesh).resolve()) if input_mesh is not None else ""
    if input_mesh is not None and not Path(mesh_path_str).exists():
        raise FileNotFoundError(f"No se encontró el archivo 3D de entrada: {mesh_path_str}")

    dec_val = float(decimate_ratio) if decimate_ratio is not None else 0.0

    driver_code = f"""import bpy
from pathlib import Path

mesh_in = {json.dumps(mesh_path_str)}
out_glb = {json.dumps(str(out_path.resolve()))}
dec_ratio = {dec_val}

if mesh_in and mesh_in.lower().endswith(".blend"):
    bpy.ops.wm.open_mainfile(filepath=mesh_in)
else:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if mesh_in:
        low = mesh_in.lower()
        if low.endswith(".obj"):
            bpy.ops.wm.obj_import(filepath=mesh_in)
        elif low.endswith(".fbx"):
            bpy.ops.import_scene.fbx(filepath=mesh_in)
        elif low.endswith(".stl"):
            bpy.ops.wm.stl_import(filepath=mesh_in)
        elif low.endswith(".ply"):
            bpy.ops.wm.ply_import(filepath=mesh_in)
        elif low.endswith((".glb", ".gltf")):
            bpy.ops.import_scene.gltf(filepath=mesh_in)
        else:
            raise ValueError(f"Formato de malla no soportado en Blender: {{mesh_in}}")

{user_code}

for obj in list(bpy.data.objects):
    if obj.type not in {{'MESH', 'CURVE', 'SURFACE', 'FONT', 'EMPTY'}}:
        bpy.data.objects.remove(obj, do_unlink=True)

for obj in list(bpy.data.objects):
    if obj.type == 'MESH' and 0.01 <= dec_ratio < 1.0:
        bpy.context.view_layer.objects.active = obj
        mod = obj.modifiers.new(name="AutoDecimate", type='DECIMATE')
        mod.ratio = dec_ratio
        bpy.ops.object.modifier_apply(modifier=mod.name)

bpy.ops.export_scene.gltf(
    filepath=out_glb,
    export_format='GLB',
    export_yup=True,
    export_apply=True,
)
"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        driver_file = Path(tmp_dir) / "blender_export_driver.py"
        driver_file.write_text(driver_code, encoding="utf-8")
        cmd = [
            blender_bin,
            "--background",
            "--factory-startup",
            "--python-exit-code",
            "1",
            "--python",
            str(driver_file),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    raw_bytes = out_path.read_bytes()
    validate_3d_model_bytes(raw_bytes, ".glb")
    print(f"[Assets:Blender] Exportado GLB ({len(raw_bytes):,} bytes): {out_path.name}")
    return out_path


def ensure_base_models(models_dir: Path | None = None, force: bool = False) -> dict[str, Path]:
    """Genera el catálogo base de 6 modelos 3D universales (.glb) mediante Blender headless."""
    target_dir = models_dir or (_REPO_ROOT / "assets" / "models")
    target_dir.mkdir(parents=True, exist_ok=True)
    generated: dict[str, Path] = {}
    for slug, code in BASE_BLENDER_MODELS.items():
        generated[slug] = compile_blender_to_glb(
            name=slug,
            blender_code=code,
            models_dir=target_dir,
            force=force,
        )
    return generated


def validate_3d_model_bytes(raw_bytes: bytes, suffix: str) -> None:
    """Valida integridad básica de un modelo 3D glTF 2.0 (.glb binario o .gltf JSON)."""
    ext = suffix.lower()
    if ext == ".glb":
        if len(raw_bytes) < 12 or raw_bytes[:4] != b"glTF":
            raise ValueError(
                "Archivo .glb inválido: no contiene la cabecera mágica binaria 'glTF'."
            )
    elif ext == ".gltf":
        try:
            payload = json.loads(raw_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Archivo .gltf inválido: JSON malformado ({exc}).") from exc
        if not isinstance(payload, dict) or "asset" not in payload:
            raise ValueError("Archivo .gltf inválido: falta la sección obligatoria 'asset'.")
    else:
        raise ValueError(f"Extensión 3D no soportada '{suffix}'. Usa '.glb' o '.gltf'.")


def fetch_model(
    name: str,
    url: str | None = None,
    source_path: str | Path | None = None,
    blender_script: str | Path | None = None,
    decimate_ratio: float | None = None,
    models_dir: Path | None = None,
    force: bool = False,
) -> Path:
    """
    Descarga, importa o compila con Blender un modelo 3D abierto (.glb / .gltf / .blend / .obj / .fbx / .stl)
    hacia assets/models/<slug>.<ext>, validando su cabecera glTF 2.0 antes de guardarlo en caché local.
    """
    if not url and not source_path and not blender_script:
        raise ValueError(
            "Debes proporcionar '--url' (descarga CC0), '--file' (archivo 3D local) o '--blender-script' (script bpy)."
        )

    target_dir = models_dir or (_REPO_ROOT / "assets" / "models")
    target_dir.mkdir(parents=True, exist_ok=True)
    slug = _sanitize_slug(name)

    if blender_script is not None:
        return compile_blender_to_glb(
            name=slug,
            blender_script=blender_script,
            input_mesh=source_path,
            decimate_ratio=decimate_ratio,
            models_dir=target_dir,
            force=force,
        )

    if source_path is not None:
        src = Path(source_path).resolve()
        if not src.exists():
            raise FileNotFoundError(f"No se encontró el modelo 3D local: {src}")
        ext = src.suffix.lower() or ".glb"
        if ext in {".blend", ".obj", ".fbx", ".stl", ".ply"} or decimate_ratio is not None:
            return compile_blender_to_glb(
                name=slug,
                input_mesh=src,
                decimate_ratio=decimate_ratio,
                models_dir=target_dir,
                force=force,
            )
        raw_bytes = src.read_bytes()
    else:
        assert url is not None
        parsed_path = urllib.parse.urlparse(url).path
        ext = Path(parsed_path).suffix.lower() or ".glb"
        if ext not in {".glb", ".gltf"}:
            ext = ".glb"
        out_check = target_dir / f"{slug}{ext}"
        if out_check.exists() and not force:
            print(f"[Assets:Model] En caché local: {out_check.name}")
            return out_check
        raw_bytes = _http_get_bytes(url, timeout=45)

    validate_3d_model_bytes(raw_bytes, ext)
    out_path = target_dir / f"{slug}{ext}"
    if out_path.exists() and not force:
        print(f"[Assets:Model] En caché local: {out_path.name}")
        return out_path

    out_path.write_bytes(raw_bytes)
    print(f"[Assets:Model] Guardado modelo 3D ({len(raw_bytes):,} bytes): {out_path.name}")
    return out_path


def list_local_assets() -> dict[str, list[str]]:
    """Devuelve el inventario de assets locales instalados en assets/."""
    assets_root = _REPO_ROOT / "assets"
    return {
        "icons": sorted(p.stem for p in (assets_root / "icons").glob("*.svg"))
        if (assets_root / "icons").exists()
        else [],
        "maps": sorted(p.stem for p in (assets_root / "maps").glob("*.svg"))
        if (assets_root / "maps").exists()
        else [],
        "audio": sorted(p.stem for p in (assets_root / "audio").glob("*.wav"))
        if (assets_root / "audio").exists()
        else [],
        "music": sorted(
            p.stem
            for p in (assets_root / "music").iterdir()
            if p.suffix.lower() in {".wav", ".mp3"}
        )
        if (assets_root / "music").exists()
        else [],
        "images": sorted(
            p.name
            for p in (assets_root / "images").iterdir()
            if p.suffix.lower() in {".png", ".webp", ".jpg", ".jpeg", ".svg"}
        )
        if (assets_root / "images").exists()
        else [],
        "models": sorted(
            p.name
            for p in (assets_root / "models").iterdir()
            if p.suffix.lower() in {".glb", ".gltf"}
        )
        if (assets_root / "models").exists()
        else [],
    }


def register_assets_subparsers(
    parser: argparse.ArgumentParser,
    dest: str = "asset_action",
) -> None:
    """Registra los subcomandos de gestión de assets en el parser indicado."""
    sub = parser.add_subparsers(dest=dest, help="Acción sobre assets")

    p_list = sub.add_parser("list", help="Listar todos los assets locales disponibles en assets/")
    p_list.add_argument("--json", action="store_true", help="Emitir inventario en formato JSON")

    p_seed = sub.add_parser(
        "seed-icons", help="Generar/restaurar los 18 iconos técnicos vectoriales SVG base"
    )
    p_seed.add_argument("-f", "--force", action="store_true", help="Sobrescribir si ya existen")

    p_icon = sub.add_parser(
        "icon", help="Descargar icono o logo SVG desde Iconify (Lucide/Tabler/Simple Icons)"
    )
    p_icon.add_argument(
        "spec",
        help="Identificador del icono (ej. 'shield-alert', 'lucide:cpu', 'tabler:radar-2', 'simple-icons:linux')",
    )
    p_icon.add_argument("-n", "--name", help="Nombre de archivo destino sin extensión (opcional)")
    p_icon.add_argument("-f", "--force", action="store_true", help="Sobrescribir si ya existe")

    p_map = sub.add_parser(
        "map", help="Compilar mapa vectorial SVG real desde Natural Earth GeoJSON (CC0)"
    )
    p_map.add_argument(
        "country",
        help="País(es) o código(s) ISO separados por coma a destacar (ej. 'PRK', 'North Korea', 'RUS')",
    )
    p_map.add_argument(
        "-n", "--name", help="Slug destino en assets/maps/<name>.svg (ej. 'north_korea')"
    )
    p_map.add_argument(
        "-c",
        "--context",
        help="Países vecinos de contexto secundario separados por coma (ej. 'KOR,JPN')",
    )
    p_map.add_argument("--geojson", help="Ruta local o URL alternativa a archivo GeoJSON")
    p_map.add_argument("-f", "--force", action="store_true", help="Sobrescribir si ya existe")

    p_audio = sub.add_parser(
        "audio", help="Descargar y normalizar SFX o música CC0 a WAV 48kHz 16-bit"
    )
    p_audio.add_argument(
        "name", help="Nombre destino del asset (ej. 'camera_shutter' o 'dark_pulse')"
    )
    p_audio.add_argument("--url", help="URL directa al archivo de audio CC0 (.wav, .ogg, .mp3)")
    p_audio.add_argument(
        "--freesound", help="Consulta de texto en Freesound API v2 (filtra solo CC0)"
    )
    p_audio.add_argument(
        "--type",
        choices=["sfx", "music"],
        default="sfx",
        help="Destino del audio: 'sfx' (assets/audio/) o 'music' (assets/music/)",
    )
    p_audio.add_argument(
        "--max-duration",
        type=float,
        default=None,
        help="Recortar duración máxima en segundos al normalizar con FFmpeg",
    )
    p_audio.add_argument("-f", "--force", action="store_true", help="Sobrescribir si ya existe")

    p_model = sub.add_parser(
        "model",
        help="Descargar, importar o compilar con Blender modelo 3D glTF/GLB hacia assets/models/",
    )
    p_model.add_argument("name", help="Nombre destino del modelo (ej. 'shield_3d' o 'lamb')")
    p_model.add_argument("--url", help="URL directa al modelo 3D abierto (.glb o .gltf)")
    p_model.add_argument(
        "--file",
        dest="source_path",
        help="Ruta a un archivo local .glb/.gltf/.blend/.obj/.fbx/.stl",
    )
    p_model.add_argument(
        "--blender-script",
        help="Ruta a un script Python (bpy) para generar y exportar el modelo .glb con Blender headless",
    )
    p_model.add_argument(
        "--decimate",
        type=float,
        default=None,
        help="Ratio opcional de simplificación poligonal en Blender (0.05 a 1.0) para wireframe limpio",
    )
    p_model.add_argument("-f", "--force", action="store_true", help="Sobrescribir si ya existe")

    p_seed_models = sub.add_parser(
        "seed-models",
        help="Generar los 6 modelos 3D universales base (.glb) en assets/models/ usando Blender headless",
    )
    p_seed_models.add_argument(
        "-f", "--force", action="store_true", help="Sobrescribir si ya existen"
    )


def dispatch_assets_action(args: argparse.Namespace, action_attr: str = "asset_action") -> None:
    """Ejecuta la acción de assets seleccionada en un argparse.Namespace."""
    act = getattr(args, action_attr, None)
    if not act or act == "list":
        inv = list_local_assets()
        if getattr(args, "json", False):
            print(json.dumps(inv, indent=2, ensure_ascii=False))
        else:
            for k, items in inv.items():
                print(f"[{k.upper()}] ({len(items)}): {', '.join(items)}")
        return

    if act == "seed-icons":
        ensure_base_icons(force=getattr(args, "force", False))
    elif act == "seed-models":
        ensure_base_models(force=getattr(args, "force", False))
    elif act == "icon":
        fetch_icon(args.spec, name=args.name, force=args.force)
    elif act == "map":
        fetch_map(
            country_queries=args.country,
            name=args.name,
            context_queries=args.context,
            geojson_source=args.geojson,
            force=args.force,
        )
    elif act == "audio":
        fetch_audio_cc0(
            name=args.name,
            url=args.url,
            freesound_query=args.freesound,
            kind=args.type,
            max_duration=args.max_duration,
            force=args.force,
        )
    elif act == "model":
        fetch_model(
            name=args.name,
            url=args.url,
            source_path=args.source_path,
            blender_script=getattr(args, "blender_script", None),
            decimate_ratio=getattr(args, "decimate", None),
            force=args.force,
        )


def main() -> None:
    ensure_local_venv()
    parser = argparse.ArgumentParser(
        description="Gestor y descargador de assets abiertos (Iconify SVG, Natural Earth Maps, Audio CC0)."
    )
    register_assets_subparsers(parser, dest="asset_action")
    args = parser.parse_args()
    dispatch_assets_action(args, action_attr="asset_action")


if __name__ == "__main__":
    main()
