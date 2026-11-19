#!/usr/bin/env python3
"""
Gestor y descargador determinista de activos abiertos (CC0 / MIT) para video-pipeline.

Conecta el pipeline bajo demanda con tres fuentes abiertas y gratuitas sin romper
el renderizado 100% offline:
  1. Iconify API (Lucide, Tabler, Simple Icons — MIT/CC0, sin API Key) -> assets/icons/<slug>.svg
  2. Natural Earth GeoJSON (Dominio Público CC0, sin API Key) -> assets/maps/<slug>.svg
  3. Audio CC0 (URL directa o búsqueda en Freesound API v2 con filtro CC0) -> assets/audio/ o assets/music/ (WAV 48kHz 16-bit)
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

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core._runtime import ensure_local_venv  # noqa: E402

ICONIFY_API_BASE = "https://api.iconify.design"
NATURAL_EARTH_110M_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "master/geojson/ne_110m_admin_0_countries.geojson"
)
FREESOUND_SEARCH_URL = "https://freesound.org/apiv2/search/text/"

USER_AGENT = "video-pipeline-asset-fetcher/1.0 (local-deterministic-studio)"


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
    }


def main() -> None:
    ensure_local_venv()
    parser = argparse.ArgumentParser(
        description="Gestor y descargador de assets abiertos (Iconify SVG, Natural Earth Maps, Audio CC0)."
    )
    sub = parser.add_subparsers(dest="kind", help="Tipo de asset a gestionar")

    # 1. Subcomando: icon
    p_icon = sub.add_parser(
        "icon", help="Descargar icono o logo SVG desde Iconify (Lucide/Tabler/Simple Icons)"
    )
    p_icon.add_argument(
        "spec",
        help="Identificador del icono (ej. 'shield-alert', 'lucide:cpu', 'tabler:radar-2', 'simple-icons:linux')",
    )
    p_icon.add_argument("-n", "--name", help="Nombre de archivo destino sin extensión (opcional)")
    p_icon.add_argument("-f", "--force", action="store_true", help="Sobrescribir si ya existe")

    # 2. Subcomando: map
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

    # 3. Subcomando: audio
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

    # 4. Subcomando: list
    p_list = sub.add_parser("list", help="Listar todos los assets locales disponibles en assets/")
    p_list.add_argument("--json", action="store_true", help="Emitir inventario en formato JSON")

    args = parser.parse_args()
    if not args.kind or args.kind == "list":
        inv = list_local_assets()
        if getattr(args, "json", False):
            print(json.dumps(inv, indent=2, ensure_ascii=False))
        else:
            for k, items in inv.items():
                print(f"[{k.upper()}] ({len(items)}): {', '.join(items)}")
        return

    if args.kind == "icon":
        fetch_icon(args.spec, name=args.name, force=args.force)
    elif args.kind == "map":
        fetch_map(
            country_queries=args.country,
            name=args.name,
            context_queries=args.context,
            geojson_source=args.geojson,
            force=args.force,
        )
    elif args.kind == "audio":
        fetch_audio_cc0(
            name=args.name,
            url=args.url,
            freesound_query=args.freesound,
            kind=args.type,
            max_duration=args.max_duration,
            force=args.force,
        )


if __name__ == "__main__":
    main()
