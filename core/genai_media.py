#!/usr/bin/env python3
"""
Conector Opcional y Bajo Demanda de Google Gemini API para video-pipeline.

Este módulo NO se ejecuta en flujos locales ni altera la política de coste cero del núcleo.
Se invoca exclusivamente bajo demanda cuando el usuario desea generar media con la API
de Google Gemini usando su propia variable de entorno GEMINI_API_KEY:

  - Imagen (Nano Banana): gemini-nano-banana-2.1, gemini-3-pro-image, gemini-3.1-flash-lite-image
  - Video (Gemini Omni):  gemini-omni-1.2-flash (texto->video, frame inicial, transición, extensión y edición)
  - Voz actuada (TTS):    gemini-3.8-flash-tts / gemini-3.8-flash-lite-tts (1 voz o diálogo multi-personaje)
  - Música (Lyria):       lyria-3.5 (texto o imagen de referencia -> pista musical)

Todos los artefactos se guardan directo en las carpetas estándar del proyecto o del
repositorio (assets/images/, assets/videos/, assets/music/) y opcionalmente se normalizan
con FFmpeg a WAV PCM 48kHz 16-bit para entrar sin fricción en 'storyboard', 'audio_mix' y 'export-nle'.
"""

from __future__ import annotations

import argparse
import base64
import importlib.metadata
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core._runtime import (  # noqa: E402
    REPO_ROOT,
    ensure_local_venv,
    ensure_repo_root_on_path,
    resolve_project_dir,
)

ensure_repo_root_on_path()

from core.fetch_assets import build_audio_normalize_command  # noqa: E402

DEFAULT_IMAGE_MODEL = "gemini-nano-banana-2.1"
DEFAULT_VIDEO_MODEL = "gemini-omni-1.2-flash"
DEFAULT_TTS_MODEL = "gemini-3.8-flash-tts"
DEFAULT_MUSIC_MODEL = "lyria-3.5"

GENAI_MODEL_CATALOG: dict[str, dict[str, str]] = {
    "image": {
        "default": DEFAULT_IMAGE_MODEL,
        "alternatives": "gemini-3-pro-image, gemini-3.1-flash-lite-image",
        "notes": "Soporta hasta 14 imágenes de referencia y relaciones de aspecto 1:1..16:9/9:16 en 1K/2K/4K.",
    },
    "video": {
        "default": DEFAULT_VIDEO_MODEL,
        "alternatives": "gemini-omni-1.2-flash",
        "notes": "Genera 3s-15s (360p/720p/1080p/4k), transiciones entre 2 frames (3s-10s), extensiones (hasta 30s) y edición.",
    },
    "tts": {
        "default": DEFAULT_TTS_MODEL,
        "alternatives": "gemini-3.8-flash-lite-tts",
        "notes": "Voz expresiva v1beta (speech_metadata) para 1 locutor o diálogo multi-personaje.",
    },
    "music": {
        "default": DEFAULT_MUSIC_MODEL,
        "alternatives": "lyria-3.5",
        "notes": "Música instrumental o vocal desde texto o inspirada en una imagen de referencia.",
    },
}

DEPRECATED_MODELS: set[str] = {
    "gemini-omni-1.1-flash",
    "gemini-3.1-flash-image",
    "gemini-3.1-flash-tts-preview",
    "lyria-realtime-exp",
}

IMAGE_ASPECT_RATIOS: set[str] = {
    "1:1",
    "1:4",
    "1:8",
    "2:3",
    "3:2",
    "3:4",
    "4:1",
    "4:3",
    "4:5",
    "5:4",
    "8:1",
    "9:16",
    "16:9",
    "21:9",
}
IMAGE_SIZES: set[str] = {"512", "1K", "2K", "4K"}

VIDEO_ASPECT_RATIOS: set[str] = {"16:9", "9:16"}
VIDEO_RESOLUTIONS: set[str] = {"360p", "720p", "1080p", "4k"}

MIN_OMNI_DURATION = 3
MAX_OMNI_DURATION = 15
MAX_OMNI_KEYFRAME_OR_EXTEND = 10
MAX_NANO_BANANA_REFS = 14
MAX_OMNI_REF_IMAGES = 6
MAX_OMNI_REF_VIDEOS_SHORT = 3
MAX_OMNI_REF_VIDEOS_LONG = 1


@dataclass(frozen=True)
class GenAIMediaResult:
    """Resultado estructurado de una generación multimedia con Gemini API."""

    kind: str  # "image" | "video" | "tts" | "music"
    model: str
    output_path: Path
    interaction_id: str | None
    mime_type: str | None = None
    extra_text: str | None = None


def _sanitize_slug(raw: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_\-]+", "_", raw.strip().lower())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug[:60] or "genai_asset"


def resolve_gemini_api_key() -> str:
    """Obtiene GEMINI_API_KEY desde el entorno sin leer ni almacenar secretos en disco."""
    return os.environ.get("GEMINI_API_KEY", "").strip()


def require_gemini_api_key() -> str:
    """Exige que GEMINI_API_KEY esté definida en .env o en el entorno antes de llamar a la API."""
    key = resolve_gemini_api_key()
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY no está configurada.\n"
            "Opción recomendada: copia '.env.example' a '.env' en la raíz y define GEMINI_API_KEY=...\n"
            "O expórtala en tu sesión:\n"
            '  PowerShell: $env:GEMINI_API_KEY = "tu_api_key"\n'
            '  Bash      : export GEMINI_API_KEY="tu_api_key"'
        )
    return key


def strip_query_params(url: str | None) -> str:
    """Elimina parámetros de consulta de una URL antes de imprimir o registrar."""
    if not url:
        return ""
    parsed = urllib.parse.urlparse(url)
    return urllib.parse.urlunparse(parsed._replace(query=""))


def sanitize_error(err: Any) -> str:
    """Redacta claves de API, tokens OAuth, headers Bearer y URLs sensibles en mensajes de error."""
    if not err:
        return ""
    err_str = str(err)
    active_key = resolve_gemini_api_key()
    if active_key and len(active_key) >= 8:
        err_str = err_str.replace(active_key, "[REDACTED_KEY]")

    err_str = re.sub(r"AIza[0-9A-Za-z_\-]{20,}", "[REDACTED_KEY]", err_str)
    err_str = re.sub(r"AQ\.[0-9A-Za-z_\-]{16,}", "[REDACTED_KEY]", err_str)
    err_str = re.sub(r"ya29\.[0-9A-Za-z_\-]+", "[REDACTED_TOKEN]", err_str)
    err_str = re.sub(
        r"Bearer\s+[A-Za-z0-9_\-\.]+", "Bearer [REDACTED_TOKEN]", err_str, flags=re.IGNORECASE
    )
    err_str = re.sub(
        r"([?&](?:key|api_key|apiKey|access_token|auth|signature)=)[^&\s\"'<>()]+",
        r"\1[REDACTED_KEY]",
        err_str,
    )
    err_str = re.sub(r"\s+", " ", err_str).strip()
    return err_str[:497] + "..." if len(err_str) > 500 else err_str


def validate_model_name(model: str, expected_kind: str) -> str:
    """Valida que no se usen identificadores heredados o obsoletos."""
    clean = model.strip()
    if not clean:
        return GENAI_MODEL_CATALOG[expected_kind]["default"]
    lower = clean.lower()
    if lower in DEPRECATED_MODELS or any(
        prefix in lower for prefix in ("gemini-2.5", "gemini-2.0", "gemini-1.5")
    ):
        rec = GENAI_MODEL_CATALOG[expected_kind]["default"]
        raise ValueError(
            f"El modelo '{clean}' es obsoleto. Utiliza el modelo actual recomendado: '{rec}'."
        )
    return clean


def load_genai_sdk() -> tuple[Any, Any, Any]:
    """Importa el SDK oficial 'google-genai' bajo demanda (import diferido)."""
    try:
        from google import genai
        from google.genai import errors, types
    except ImportError as exc:
        raise RuntimeError(
            "El SDK opcional 'google-genai' no está instalado en este entorno.\n"
            "Instálalo solo si vas a usar generación en la nube:\n"
            '  uv pip install -e ".[dev,genai]"'
        ) from exc
    return genai, types, errors


def check_genai_environment() -> dict[str, Any]:
    """Diagnostica disponibilidad del SDK google-genai, FFmpeg y estado de GEMINI_API_KEY (sin exponerla)."""
    sdk_available = False
    sdk_version: str | None = None
    try:
        import google.genai  # noqa: F401

        sdk_available = True
        try:
            sdk_version = importlib.metadata.version("google-genai")
        except importlib.metadata.PackageNotFoundError:
            sdk_version = "installed"
    except ImportError:
        pass

    return {
        "sdk_available": sdk_available,
        "sdk_version": sdk_version,
        "api_key_configured": bool(resolve_gemini_api_key()),
        "ffmpeg_bin": shutil.which("ffmpeg"),
        "ffprobe_bin": shutil.which("ffprobe"),
        "models": {k: v["default"] for k, v in GENAI_MODEL_CATALOG.items()},
    }


def _detect_mime_type(path: Path) -> str:
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".webm": "video/webm",
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
    }
    ext = path.suffix.lower()
    if ext in mime_map:
        return mime_map[ext]
    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or "application/octet-stream"


def _build_inline_image_part(image_path: str | Path) -> dict[str, str]:
    p = Path(image_path)
    if not p.is_file():
        raise FileNotFoundError(f"No se encontró la imagen de referencia: '{image_path}'.")
    raw = p.read_bytes()
    return {
        "type": "image",
        "data": base64.b64encode(raw).decode("utf-8"),
        "mime_type": _detect_mime_type(p),
    }


def _resolve_asset_output_path(
    *,
    kind_subdir: str,
    slug: str,
    default_ext: str,
    project: str | Path | None = None,
    output_path: str | Path | None = None,
) -> Path:
    if output_path is not None:
        out = Path(output_path)
    elif project is not None:
        out = resolve_project_dir(project) / "assets" / kind_subdir / f"{slug}{default_ext}"
    else:
        out = REPO_ROOT / "assets" / kind_subdir / f"{slug}{default_ext}"
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


def _is_file_uri(value: str) -> bool:
    return "files/" in value and (
        value.startswith("files/") or "generativelanguage.googleapis.com" in value
    )


def _normalize_file_uri(uri: str) -> str:
    match = re.search(r"files/([a-zA-Z0-9_\-]+)", uri)
    if match:
        return f"https://generativelanguage.googleapis.com/files/{match.group(1)}"
    return strip_query_params(uri)


def _upload_and_wait_active(
    client: Any,
    types: Any,
    media_path: str | Path,
    *,
    default_mime: str,
    strip_audio: bool = False,
    poll_interval: float = 3.0,
    max_timeout: float = 600.0,
) -> tuple[str, str]:
    """Sube un archivo multimedia vía Files API (limpiando audio si se pide) y espera ACTIVE."""
    raw_str = str(media_path).strip()
    if _is_file_uri(raw_str):
        if strip_audio:
            raise ValueError(
                "--strip-audio no puede aplicarse a un URI remoto existente; pasa un archivo local."
            )
        return _normalize_file_uri(raw_str), default_mime

    local_path = Path(raw_str)
    if not local_path.is_file():
        raise FileNotFoundError(f"No se encontró el archivo multimedia local: '{media_path}'.")

    mime_type = _detect_mime_type(local_path)
    with tempfile.TemporaryDirectory(prefix="vp_genai_up_") as tmp_dir:
        upload_src = local_path
        if strip_audio and mime_type.startswith("video/"):
            ffmpeg_bin = shutil.which("ffmpeg")
            if not ffmpeg_bin:
                raise FileNotFoundError("Se requiere 'ffmpeg' en PATH para usar --strip-audio.")
            stripped = Path(tmp_dir) / f"stripped{local_path.suffix or '.mp4'}"
            proc = subprocess.run(
                [ffmpeg_bin, "-y", "-i", str(local_path), "-c:v", "copy", "-an", str(stripped)],
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode != 0:
                raise RuntimeError(
                    f"FFmpeg falló al quitar audio de '{local_path.name}': {sanitize_error(proc.stderr)}"
                )
            upload_src = stripped

        config = types.UploadFileConfig(display_name=local_path.name, mime_type=mime_type)
        uploaded = client.files.upload(file=str(upload_src), config=config)

    file_name = getattr(uploaded, "name", None)
    uri = getattr(uploaded, "uri", None)
    if not file_name:
        raise RuntimeError("La subida mediante Files API no devolvió nombre de archivo.")

    deadline = time.monotonic() + max_timeout
    interval = poll_interval
    while True:
        file_obj = client.files.get(name=file_name)
        state = getattr(file_obj, "state", None)
        state_name = getattr(state, "name", str(state or "")).upper()
        if state_name == "ACTIVE":
            resolved_uri = getattr(file_obj, "uri", uri) or f"files/{file_name}"
            resolved_mime = getattr(file_obj, "mime_type", None) or mime_type
            return _normalize_file_uri(resolved_uri), str(resolved_mime)
        if state_name == "FAILED":
            err = getattr(file_obj, "error", None)
            raise RuntimeError(f"Procesamiento remoto fallido para '{local_path.name}': {err}")
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"Tiempo máximo agotado ({max_timeout}s) esperando archivo activo '{file_name}'."
            )
        time.sleep(interval)
        interval = min(interval * 1.25, 15.0)


def validate_omni_constraints(
    *,
    duration: int | None = None,
    aspect_ratio: str = "16:9",
    resolution: str | None = "720p",
    first_frame: str | Path | None = None,
    last_frame: str | Path | None = None,
    ref_images: list[str | Path] | None = None,
    video_input: str | Path | None = None,
    extend_video: str | Path | None = None,
    video_references: list[str | Path] | None = None,
    task: str | None = None,
    previous_interaction_id: str | None = None,
) -> tuple[str | None, str, str | None]:
    """Valida todas las restricciones oficiales de gemini-omni-1.2-flash antes de subir medios."""
    if aspect_ratio not in VIDEO_ASPECT_RATIOS:
        raise ValueError(
            f"Relación de aspecto '{aspect_ratio}' inválida para video. Usa: {', '.join(sorted(VIDEO_ASPECT_RATIOS))}."
        )
    clean_res: str | None = None
    if resolution is not None:
        clean_res = resolution.strip().lower()
        if clean_res not in VIDEO_RESOLUTIONS:
            raise ValueError(
                f"Resolución '{resolution}' inválida. Opciones: {', '.join(sorted(VIDEO_RESOLUTIONS))}."
            )

    if last_frame and not first_frame:
        raise ValueError("--last-frame requiere obligatoriamente indicar --first-frame.")

    dur_str: str | None = None
    if duration is not None:
        if not isinstance(duration, int) or isinstance(duration, bool):
            raise ValueError(f"La duración debe ser un entero (3..15). Recibido: {duration}.")
        if duration < MIN_OMNI_DURATION or duration > MAX_OMNI_DURATION:
            raise ValueError(
                f"La duración para Omni Flash debe estar entre {MIN_OMNI_DURATION} y {MAX_OMNI_DURATION} segundos (recibido {duration})."
            )
        if duration > MAX_OMNI_KEYFRAME_OR_EXTEND:
            if first_frame and last_frame:
                raise ValueError(
                    f"Las transiciones first-frame + last-frame admiten máximo {MAX_OMNI_KEYFRAME_OR_EXTEND}s (recibido {duration}s)."
                )
            if extend_video or task == "extend":
                raise ValueError(
                    f"Las extensiones de video admiten máximo {MAX_OMNI_KEYFRAME_OR_EXTEND}s por turno (recibido {duration}s)."
                )
        dur_str = f"{duration}s"

    imgs = list(ref_images or [])
    total_images = len(imgs)
    if first_frame:
        total_images += 1
    if last_frame and str(last_frame) != str(first_frame):
        total_images += 1
    if total_images > MAX_OMNI_REF_IMAGES:
        raise ValueError(
            f"Omni Flash admite hasta {MAX_OMNI_REF_IMAGES} imágenes en total (frames + referencias; recibidas {total_images})."
        )

    vrefs = list(video_references or [])
    if vrefs:
        if extend_video or video_input or previous_interaction_id or task in {"edit", "extend"}:
            raise ValueError(
                "--video-reference solo se admite al generar un video nuevo (no en edición, extensión ni turnos previos)."
            )
        max_vrefs = (
            MAX_OMNI_REF_VIDEOS_LONG
            if (duration is not None and duration > MAX_OMNI_KEYFRAME_OR_EXTEND)
            else MAX_OMNI_REF_VIDEOS_SHORT
        )
        if len(vrefs) > max_vrefs:
            raise ValueError(
                f"Se admiten máximo {max_vrefs} video(s) de referencia para {dur_str or '10s'} (recibidos {len(vrefs)})."
            )

    return dur_str, aspect_ratio, clean_res


def generate_genai_image(
    prompt: str,
    *,
    reference_images: list[str | Path] | None = None,
    model: str = DEFAULT_IMAGE_MODEL,
    aspect_ratio: str | None = None,
    image_size: str | None = None,
    mime_type: str = "image/png",
    previous_interaction_id: str | None = None,
    project: str | Path | None = None,
    output_path: str | Path | None = None,
    slug: str | None = None,
) -> GenAIMediaResult:
    """Genera o edita una imagen con Nano Banana 2.1 mediante la Interactions API."""
    clean_model = validate_model_name(model, "image")
    refs = list(reference_images or [])
    if len(refs) > MAX_NANO_BANANA_REFS:
        raise ValueError(
            f"Nano Banana admite hasta {MAX_NANO_BANANA_REFS} imágenes de referencia (recibidas {len(refs)})."
        )
    if aspect_ratio and aspect_ratio not in IMAGE_ASPECT_RATIOS:
        raise ValueError(f"Aspect ratio '{aspect_ratio}' inválido para imagen.")
    if image_size and image_size not in IMAGE_SIZES:
        raise ValueError(f"Tamaño '{image_size}' inválido. Usa: {', '.join(sorted(IMAGE_SIZES))}.")
    if mime_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise ValueError(f"MIME de salida '{mime_type}' inválido para imagen.")

    require_gemini_api_key()
    genai, _, errors = load_genai_sdk()

    input_payload: str | list[dict[str, str]]
    if refs:
        input_payload = [{"type": "text", "text": prompt}] + [
            _build_inline_image_part(p) for p in refs
        ]
    else:
        input_payload = prompt

    resp_format: dict[str, Any] = {"type": "image", "mime_type": mime_type}
    if aspect_ratio:
        resp_format["aspect_ratio"] = aspect_ratio
    if image_size:
        resp_format["image_size"] = image_size

    create_kwargs: dict[str, Any] = {
        "model": clean_model,
        "input": input_payload,
        "response_format": resp_format,
    }
    if previous_interaction_id:
        create_kwargs["previous_interaction_id"] = previous_interaction_id

    client = genai.Client()
    try:
        interaction = client.interactions.create(**create_kwargs)
    except errors.APIError as exc:
        raise RuntimeError(f"Error de Gemini API generando imagen: {sanitize_error(exc)}") from exc

    out_img = getattr(interaction, "output_image", None)
    if not out_img or not getattr(out_img, "data", None):
        raise RuntimeError("La respuesta de Gemini API no devolvió bytes de imagen.")

    out_mime = getattr(out_img, "mime_type", None) or mime_type
    ext = ".jpg" if "jpeg" in out_mime else (".webp" if "webp" in out_mime else ".png")
    dest = _resolve_asset_output_path(
        kind_subdir="images",
        slug=_sanitize_slug(slug or prompt),
        default_ext=ext,
        project=project,
        output_path=output_path,
    )
    dest.write_bytes(base64.b64decode(out_img.data))

    interaction_id = getattr(interaction, "id", None)
    print(f"[GenAI:Image] Guardada ({clean_model}) -> {dest}")
    if interaction_id:
        print(f"[GenAI:Image] Interaction ID: {interaction_id}")
    return GenAIMediaResult(
        kind="image",
        model=clean_model,
        output_path=dest,
        interaction_id=interaction_id,
        mime_type=out_mime,
    )


def _append_uploaded_media(
    input_parts: list[dict[str, str]],
    client: Any,
    types: Any,
    items: list[str | Path],
    *,
    part_type: str,
    default_mime: str,
    strip_audio: bool,
    timeout: float,
) -> None:
    """Sube elementos multimedia y los agrega al arreglo input_parts del SDK."""
    for item in items:
        uri, mime = _upload_and_wait_active(
            client,
            types,
            item,
            default_mime=default_mime,
            strip_audio=strip_audio,
            max_timeout=timeout,
        )
        input_parts.append({"type": part_type, "uri": uri, "mime_type": mime})


def _write_audio_output(
    raw_bytes: bytes,
    dest: Path,
    *,
    raw_ext: str,
    normalize_wav: bool,
) -> None:
    """Escribe bytes de audio y opcionalmente normaliza a WAV PCM 48kHz 16-bit estéreo."""
    if not normalize_wav:
        dest.write_bytes(raw_bytes)
        return
    with tempfile.TemporaryDirectory(prefix="vp_genai_aud_") as tmp_dir:
        raw_tmp = Path(tmp_dir) / f"genai_raw{raw_ext}"
        raw_tmp.write_bytes(raw_bytes)
        cmd = build_audio_normalize_command(raw_tmp, dest)
        proc = subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            err_tail = " | ".join(
                proc.stderr.decode("utf-8", errors="replace").strip().splitlines()[-4:]
            )
            raise RuntimeError(
                f"FFmpeg falló al normalizar audio hacia '{dest.name}': {sanitize_error(err_tail)}"
            )


def generate_genai_video(
    prompt: str,
    *,
    model: str = DEFAULT_VIDEO_MODEL,
    aspect_ratio: str = "16:9",
    duration: int | None = None,
    resolution: str | None = "720p",
    first_frame: str | Path | None = None,
    last_frame: str | Path | None = None,
    reference_images: list[str | Path] | None = None,
    video_input: str | Path | None = None,
    extend_video: str | Path | None = None,
    video_references: list[str | Path] | None = None,
    task: str | None = None,
    strip_audio: bool = False,
    previous_interaction_id: str | None = None,
    timeout: int = 600,
    project: str | Path | None = None,
    output_path: str | Path | None = None,
    slug: str | None = None,
) -> GenAIMediaResult:
    """Genera, anima, extiende o edita un video MP4 con Gemini Omni 1.2 Flash."""
    clean_model = validate_model_name(model, "video")
    if timeout <= 0:
        raise ValueError(f"Timeout inválido: {timeout}. Debe ser mayor a 0 segundos.")

    dur_str, clean_ar, clean_res = validate_omni_constraints(
        duration=duration,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        first_frame=first_frame,
        last_frame=last_frame,
        ref_images=reference_images,
        video_input=video_input,
        extend_video=extend_video,
        video_references=video_references,
        task=task,
        previous_interaction_id=previous_interaction_id,
    )

    require_gemini_api_key()
    genai, types, errors = load_genai_sdk()
    client = genai.Client(http_options=types.HttpOptions(timeout=int(timeout) * 1000))

    input_parts: list[dict[str, str]] = []
    f1_uri: str | None = None
    f1_mime: str | None = None
    if first_frame:
        f1_uri, f1_mime = _upload_and_wait_active(
            client, types, first_frame, default_mime="image/png", max_timeout=float(timeout)
        )
        input_parts.append({"type": "image", "uri": f1_uri, "mime_type": f1_mime})

    if last_frame:
        if str(last_frame) == str(first_frame) and f1_uri and f1_mime:
            input_parts.append({"type": "image", "uri": f1_uri, "mime_type": f1_mime})
        else:
            f2_uri, f2_mime = _upload_and_wait_active(
                client, types, last_frame, default_mime="image/png", max_timeout=float(timeout)
            )
            input_parts.append({"type": "image", "uri": f2_uri, "mime_type": f2_mime})

    if reference_images:
        _append_uploaded_media(
            input_parts,
            client,
            types,
            list(reference_images),
            part_type="image",
            default_mime="image/png",
            strip_audio=False,
            timeout=float(timeout),
        )
    if extend_video:
        _append_uploaded_media(
            input_parts,
            client,
            types,
            [extend_video],
            part_type="video",
            default_mime="video/mp4",
            strip_audio=strip_audio,
            timeout=float(timeout),
        )
    if video_input:
        _append_uploaded_media(
            input_parts,
            client,
            types,
            [video_input],
            part_type="video",
            default_mime="video/mp4",
            strip_audio=strip_audio,
            timeout=float(timeout),
        )
    if video_references:
        _append_uploaded_media(
            input_parts,
            client,
            types,
            list(video_references),
            part_type="video",
            default_mime="video/mp4",
            strip_audio=strip_audio,
            timeout=float(timeout),
        )

    prompt_text = prompt.strip()
    if extend_video and not any(
        tok in prompt_text.lower() for tok in ("extend", "extiende", "continue", "continúa")
    ):
        prompt_text = f"Extend this video. {prompt_text}".strip()
    elif (
        first_frame
        and last_frame
        and "first" not in prompt_text.lower()
        and "starting" not in prompt_text.lower()
    ):
        prompt_text = f"{prompt_text}. Use the first image as the starting frame and the second image as the final frame."
    elif (
        first_frame and "first" not in prompt_text.lower() and "starting" not in prompt_text.lower()
    ):
        prompt_text = f"{prompt_text}. Use the first image as the starting frame."

    input_parts.append({"type": "text", "text": prompt_text})

    video_fmt: dict[str, Any] = {"type": "video", "delivery": "uri"}
    if task != "extend":
        video_fmt["aspect_ratio"] = clean_ar
    if dur_str:
        video_fmt["duration"] = dur_str
    if clean_res:
        video_fmt["resolution"] = clean_res

    create_kwargs: dict[str, Any] = {
        "model": clean_model,
        "input": input_parts,
        "response_format": video_fmt,
    }
    if task and not previous_interaction_id:
        create_kwargs["generation_config"] = {"video_config": {"task": task}}
    if previous_interaction_id:
        create_kwargs["previous_interaction_id"] = previous_interaction_id

    print(
        f"[GenAI:Video] Generando con {clean_model} ({clean_ar}, {clean_res or '720p'}, {dur_str or '10s'})..."
    )
    try:
        interaction = client.interactions.create(**create_kwargs)
    except errors.APIError as exc:
        raise RuntimeError(f"Error de Gemini API generando video: {sanitize_error(exc)}") from exc

    out_vid = getattr(interaction, "output_video", None)
    if not out_vid or not getattr(out_vid, "uri", None):
        raise RuntimeError("La respuesta de Omni Flash no devolvió URI de video generado.")

    dest = _resolve_asset_output_path(
        kind_subdir="videos",
        slug=_sanitize_slug(slug or prompt),
        default_ext=".mp4",
        project=project,
        output_path=output_path,
    )
    try:
        download_target = getattr(out_vid, "uri", out_vid)
        video_bytes = client.files.download(file=download_target)
        dest.write_bytes(video_bytes)
    except Exception as exc:
        raise RuntimeError(
            f"Error descargando video generado desde Gemini API: {sanitize_error(exc)}"
        ) from exc

    interaction_id = getattr(interaction, "id", None)
    print(f"[GenAI:Video] Video descargado -> {dest}")
    if interaction_id:
        print(f"[GenAI:Video] Interaction ID: {interaction_id}")
    return GenAIMediaResult(
        kind="video",
        model=clean_model,
        output_path=dest,
        interaction_id=interaction_id,
        mime_type="video/mp4",
    )


def _parse_speakers_map(raw_speakers: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for pair in raw_speakers.split(","):
        item = pair.strip()
        if not item:
            continue
        if "=" not in item:
            raise ValueError(
                f"Formato inválido en --speakers: '{item}'. Usa 'Personaje=Voz' (ej. 'Coco=Puck,Fresa=Kore')."
            )
        speaker, voice = item.split("=", 1)
        s_clean, v_clean = speaker.strip(), voice.strip()
        if not s_clean or not v_clean:
            raise ValueError(f"Par inválido en --speakers: '{item}'.")
        mapping[s_clean] = v_clean
    if not mapping:
        raise ValueError("Debes indicar al menos un locutor en --speakers.")
    return mapping


def _parse_dialogue_lines(text: str, valid_speakers: list[str]) -> list[dict[str, str]]:
    """Convierte líneas 'Personaje: texto' en turnos estructurados para multi-speaker TTS."""
    turns: list[dict[str, str]] = []
    speaker_lut = {s.lower(): s for s in valid_speakers}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if ":" in line:
            head, body = line.split(":", 1)
            matched = speaker_lut.get(head.strip().lower())
            if matched:
                turns.append({"speaker": matched, "text": body.strip()})
                continue
        if turns:
            turns[-1]["text"] = f"{turns[-1]['text']} {line}".strip()
        else:
            turns.append({"speaker": valid_speakers[0], "text": line})
    return turns


def generate_genai_tts(
    text: str | None = None,
    *,
    turns_file: str | Path | None = None,
    voice: str = "Kore",
    style: str | None = None,
    speakers: str | None = None,
    model: str = DEFAULT_TTS_MODEL,
    normalize_wav: bool = True,
    project: str | Path | None = None,
    output_path: str | Path | None = None,
    slug: str | None = None,
) -> GenAIMediaResult:
    """
    Genera locución simple o diálogo multi-personaje con Gemini 3.8 TTS (v1beta).
    Opcionalmente normaliza a WAV PCM 48kHz 16-bit estéreo para el pipeline.
    """
    clean_model = validate_model_name(model, "tts")
    content_items: list[dict[str, Any]] = []
    speech_config: Any

    if turns_file is not None:
        turns_path = Path(turns_file)
        if not turns_path.is_file():
            raise FileNotFoundError(f"No se encontró el archivo de turnos JSON: '{turns_file}'.")
        raw_turns = json.loads(turns_path.read_text(encoding="utf-8"))
        if not isinstance(raw_turns, list) or not raw_turns:
            raise ValueError(f"El archivo '{turns_file}' debe contener una lista JSON no vacía.")
        speaker_voices: dict[str, str] = {}
        for idx, item in enumerate(raw_turns):
            if not isinstance(item, dict) or not item.get("speaker") or not item.get("text"):
                raise ValueError(
                    f"Turno #{idx + 1} inválido en '{turns_file}': requiere 'speaker' y 'text'."
                )
            sp = str(item["speaker"]).strip()
            vc = str(item.get("voice", voice)).strip() or voice
            speaker_voices.setdefault(sp, vc)
            entry: dict[str, Any] = {"type": "text", "text": str(item["text"]).strip()}
            ann: dict[str, str] = {"type": "speech_metadata", "speaker": sp}
            if item.get("style"):
                ann["style"] = str(item["style"]).strip()
            entry["annotations"] = [ann]
            content_items.append(entry)
        if len(speaker_voices) == 1:
            only_voice = next(iter(speaker_voices.values()))
            for entry in content_items:
                entry["annotations"][0].pop("speaker", None)
                if len(entry["annotations"][0]) == 1:
                    entry.pop("annotations")
            speech_config = [{"voice": only_voice}]
        else:
            speech_config = {
                "speakers": [{"speaker": s, "voice": v} for s, v in speaker_voices.items()]
            }
    elif speakers:
        if not text or not text.strip():
            raise ValueError("Debes proporcionar texto de diálogo junto con --speakers.")
        sp_map = _parse_speakers_map(speakers)
        parsed_turns = _parse_dialogue_lines(text, list(sp_map.keys()))
        if len(sp_map) == 1:
            only_voice = next(iter(sp_map.values()))
            for t in parsed_turns:
                entry_s: dict[str, Any] = {"type": "text", "text": t["text"]}
                if style:
                    entry_s["annotations"] = [{"type": "speech_metadata", "style": style}]
                content_items.append(entry_s)
            speech_config = [{"voice": only_voice}]
        else:
            for t in parsed_turns:
                ann_item: dict[str, str] = {"type": "speech_metadata", "speaker": t["speaker"]}
                if style:
                    ann_item["style"] = style
                content_items.append({"type": "text", "text": t["text"], "annotations": [ann_item]})
            speech_config = {"speakers": [{"speaker": s, "voice": v} for s, v in sp_map.items()]}
    else:
        if not text or not text.strip():
            raise ValueError("Debes proporcionar el texto a locutar o usar --turns-json.")
        entry = {"type": "text", "text": text.strip()}
        if style:
            entry["annotations"] = [{"type": "speech_metadata", "style": style.strip()}]
        content_items.append(entry)
        speech_config = [{"voice": voice}]

    require_gemini_api_key()
    genai, _, errors = load_genai_sdk()
    client = genai.Client(http_options={"api_version": "v1beta"})

    try:
        interaction = client.interactions.create(
            model=clean_model,
            input=[{"type": "user_input", "content": content_items}],
            response_format={"type": "audio"},
            generation_config={"speech_config": speech_config},
        )
    except errors.APIError as exc:
        raise RuntimeError(f"Error de Gemini API generando TTS: {sanitize_error(exc)}") from exc

    out_audio = getattr(interaction, "output_audio", None)
    if not out_audio or not getattr(out_audio, "data", None):
        raise RuntimeError("Gemini TTS no devolvió datos de audio.")

    raw_bytes = base64.b64decode(out_audio.data)
    default_slug = (
        slug or (Path(turns_file).stem if turns_file is not None else None) or (text or "locucion")
    )
    dest = _resolve_asset_output_path(
        kind_subdir="audio",
        slug=_sanitize_slug(default_slug),
        default_ext=".wav",
        project=project,
        output_path=output_path,
    )

    _write_audio_output(raw_bytes, dest, raw_ext=".wav", normalize_wav=normalize_wav)

    interaction_id = getattr(interaction, "id", None)
    print(f"[GenAI:TTS] Locución guardada ({clean_model}) -> {dest}")
    return GenAIMediaResult(
        kind="tts",
        model=clean_model,
        output_path=dest,
        interaction_id=interaction_id,
        mime_type="audio/wav",
    )


def generate_genai_music(
    prompt: str,
    *,
    reference_images: list[str | Path] | None = None,
    model: str = DEFAULT_MUSIC_MODEL,
    normalize_wav: bool = True,
    project: str | Path | None = None,
    output_path: str | Path | None = None,
    slug: str | None = None,
) -> GenAIMediaResult:
    """Genera música original con Lyria 3.5 y la exporta en assets/music/."""
    clean_model = validate_model_name(model, "music")
    require_gemini_api_key()
    genai, _, errors = load_genai_sdk()

    refs = list(reference_images or [])
    input_payload: str | list[dict[str, str]]
    if refs:
        input_payload = [{"type": "text", "text": prompt}] + [
            _build_inline_image_part(p) for p in refs
        ]
    else:
        input_payload = prompt

    client = genai.Client()
    try:
        interaction = client.interactions.create(
            model=clean_model,
            input=input_payload,
        )
    except errors.APIError as exc:
        raise RuntimeError(f"Error de Gemini API generando música: {sanitize_error(exc)}") from exc

    out_audio = getattr(interaction, "output_audio", None)
    if not out_audio or not getattr(out_audio, "data", None):
        raise RuntimeError("Lyria 3.5 no devolvió pista de audio.")

    raw_bytes = base64.b64decode(out_audio.data)
    out_mime = getattr(out_audio, "mime_type", None) or "audio/mp3"
    ext = ".wav" if normalize_wav else (".wav" if "wav" in out_mime else ".mp3")
    dest = _resolve_asset_output_path(
        kind_subdir="music",
        slug=_sanitize_slug(slug or prompt),
        default_ext=ext,
        project=project,
        output_path=output_path,
    )

    raw_ext = ".wav" if "wav" in out_mime else ".mp3"
    _write_audio_output(raw_bytes, dest, raw_ext=raw_ext, normalize_wav=normalize_wav)

    lyrics = getattr(interaction, "output_text", None)
    interaction_id = getattr(interaction, "id", None)
    print(f"[GenAI:Music] Pista guardada ({clean_model}) -> {dest}")
    return GenAIMediaResult(
        kind="music",
        model=clean_model,
        output_path=dest,
        interaction_id=interaction_id,
        mime_type="audio/wav" if normalize_wav else out_mime,
        extra_text=lyrics,
    )


def register_genai_subparsers(parser: argparse.ArgumentParser, dest: str = "genai_action") -> None:
    sub = parser.add_subparsers(
        dest=dest, help="Generación multimedia opcional con Google Gemini API"
    )

    p_doc = sub.add_parser(
        "doctor", help="Verificar SDK google-genai, FFmpeg y presencia segura de GEMINI_API_KEY"
    )
    p_doc.add_argument("--json", action="store_true", help="Imprimir diagnóstico en JSON")

    p_mod = sub.add_parser("models", help="Listar modelos actuales soportados por modalidad")
    p_mod.add_argument("--json", action="store_true", help="Imprimir catálogo en JSON")

    p_img = sub.add_parser("image", help="Generar o editar imagen con Nano Banana 2.1")
    p_img.add_argument("prompt", help="Descripción de la escena o edición deseada")
    p_img.add_argument(
        "-i", "--input", dest="inputs", action="append", help="Imagen(es) de referencia (hasta 14)"
    )
    p_img.add_argument("-m", "--model", default=DEFAULT_IMAGE_MODEL)
    p_img.add_argument("--aspect-ratio", default=None, help="Ej. 16:9, 9:16, 1:1, 4:5")
    p_img.add_argument(
        "--size", default=None, choices=sorted(IMAGE_SIZES), help="Resolución (512, 1K, 2K, 4K)"
    )
    p_img.add_argument(
        "--mime", default="image/png", choices=["image/png", "image/jpeg", "image/webp"]
    )
    p_img.add_argument("--previous-interaction-id", help="Continuar edición desde un turno previo")
    p_img.add_argument("-p", "--project", help="Proyecto destino (<proyecto>/assets/images/)")
    p_img.add_argument("--slug", help="Nombre base del archivo")
    p_img.add_argument("-o", "--output", help="Ruta explícita de salida")

    p_vid = sub.add_parser(
        "video", help="Generar, animar o extender video MP4 con Gemini Omni 1.2 Flash"
    )
    p_vid.add_argument("prompt", help="Prompt narrativo o de edición de video")
    p_vid.add_argument("-m", "--model", default=DEFAULT_VIDEO_MODEL)
    p_vid.add_argument("--aspect-ratio", default="16:9", choices=sorted(VIDEO_ASPECT_RATIOS))
    p_vid.add_argument("--resolution", default="720p", choices=sorted(VIDEO_RESOLUTIONS))
    p_vid.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Segundos (3..15; 3..10 en transiciones/extensión)",
    )
    p_vid.add_argument("--first-frame", help="Imagen inicial (archivo local o files/<id>)")
    p_vid.add_argument("--last-frame", help="Imagen final (requiere --first-frame)")
    p_vid.add_argument(
        "-i", "--image", dest="ref_images", action="append", help="Imágenes de referencia (hasta 6)"
    )
    p_vid.add_argument("--video", dest="video_input", help="Video fuente a editar")
    p_vid.add_argument("--extend", dest="extend_video", help="Video fuente a extender (3..10s)")
    p_vid.add_argument(
        "--video-reference",
        dest="video_refs",
        action="append",
        help="Video(s) de referencia para generación nueva",
    )
    p_vid.add_argument("--task", choices=["generate", "edit", "extend"], default=None)
    p_vid.add_argument(
        "--strip-audio", action="store_true", help="Quitar audio previo antes de subir"
    )
    p_vid.add_argument("--previous-interaction-id", help="Continuar turno previo sin re-subir")
    p_vid.add_argument("--timeout", type=int, default=600, help="Timeout HTTP/polling en segundos")
    p_vid.add_argument("-p", "--project", help="Proyecto destino (<proyecto>/assets/videos/)")
    p_vid.add_argument("--slug", help="Nombre base del archivo MP4")
    p_vid.add_argument("-o", "--output", help="Ruta explícita de salida")

    p_tts = sub.add_parser(
        "tts", help="Generar locución o diálogo multi-personaje con Gemini 3.8 TTS"
    )
    p_tts.add_argument("text", nargs="?", default=None, help="Texto o líneas 'Personaje: texto'")
    p_tts.add_argument(
        "--turns-json", help="Archivo JSON con lista de turnos [{speaker, voice, style, text}]"
    )
    p_tts.add_argument("--voice", default="Kore", help="Voz principal (ej. Kore, Puck)")
    p_tts.add_argument(
        "--style", default=None, help="Estilo emocional (ej. 'dramatic and intense')"
    )
    p_tts.add_argument("--speakers", default=None, help="Mapa multi-voz: 'Coco=Puck,Fresa=Kore'")
    p_tts.add_argument("-m", "--model", default=DEFAULT_TTS_MODEL)
    p_tts.add_argument(
        "--no-normalize", action="store_true", help="Guardar WAV crudo sin convertir a 48kHz"
    )
    p_tts.add_argument("-p", "--project", help="Proyecto destino (<proyecto>/assets/audio/)")
    p_tts.add_argument("--slug", help="Nombre base del archivo WAV")
    p_tts.add_argument("-o", "--output", help="Ruta explícita de salida")

    p_mus = sub.add_parser("music", help="Generar pista musical con Lyria 3.5")
    p_mus.add_argument("prompt", help="Descripción musical, género, tempo e instrumentación")
    p_mus.add_argument(
        "-i", "--input", dest="inputs", action="append", help="Imagen opcional de inspiración"
    )
    p_mus.add_argument("-m", "--model", default=DEFAULT_MUSIC_MODEL)
    p_mus.add_argument(
        "--no-normalize",
        action="store_true",
        help="Mantener MP3/formato crudo sin pasar a WAV 48kHz",
    )
    p_mus.add_argument("-p", "--project", help="Proyecto destino (<proyecto>/assets/music/)")
    p_mus.add_argument("--slug", help="Nombre base de la pista")
    p_mus.add_argument("-o", "--output", help="Ruta explícita de salida")


def dispatch_genai_action(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser | None = None,
    action_attr: str = "genai_action",
) -> None:
    action = getattr(args, action_attr, None)
    if not action:
        if parser is not None:
            parser.print_help()
        return

    try:
        if action == "doctor":
            info = check_genai_environment()
            print(json.dumps(info, indent=2, ensure_ascii=False))
            return

        if action == "models":
            if getattr(args, "json", False):
                print(json.dumps(GENAI_MODEL_CATALOG, indent=2, ensure_ascii=False))
                return
            print("\n=== MODELOS GEMINI SOPORTADOS (BAJO DEMANDA) ===")
            for kind, meta in GENAI_MODEL_CATALOG.items():
                print(f"  - {kind:<6} : {meta['default']} | {meta['notes']}")
            print()
            return

        if action == "image":
            generate_genai_image(
                args.prompt,
                reference_images=args.inputs,
                model=args.model,
                aspect_ratio=args.aspect_ratio,
                image_size=args.size,
                mime_type=args.mime,
                previous_interaction_id=args.previous_interaction_id,
                project=args.project,
                output_path=args.output,
                slug=args.slug,
            )
            return

        if action == "video":
            generate_genai_video(
                args.prompt,
                model=args.model,
                aspect_ratio=args.aspect_ratio,
                duration=args.duration,
                resolution=args.resolution,
                first_frame=args.first_frame,
                last_frame=args.last_frame,
                reference_images=args.ref_images,
                video_input=args.video_input,
                extend_video=args.extend_video,
                video_references=args.video_refs,
                task=args.task,
                strip_audio=args.strip_audio,
                previous_interaction_id=args.previous_interaction_id,
                timeout=args.timeout,
                project=args.project,
                output_path=args.output,
                slug=args.slug,
            )
            return

        if action == "tts":
            generate_genai_tts(
                args.text,
                turns_file=args.turns_json,
                voice=args.voice,
                style=args.style,
                speakers=args.speakers,
                model=args.model,
                normalize_wav=not args.no_normalize,
                project=args.project,
                output_path=args.output,
                slug=args.slug,
            )
            return

        if action == "music":
            generate_genai_music(
                args.prompt,
                reference_images=args.inputs,
                model=args.model,
                normalize_wav=not args.no_normalize,
                project=args.project,
                output_path=args.output,
                slug=args.slug,
            )
            return
    except (
        FileNotFoundError,
        ValueError,
        RuntimeError,
        TimeoutError,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"Error: {sanitize_error(exc)}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    ensure_local_venv()
    parser = argparse.ArgumentParser(
        description="Conector opcional bajo demanda para Google Gemini API (Nano Banana, Omni Flash, TTS, Lyria)"
    )
    register_genai_subparsers(parser)
    args = parser.parse_args()
    dispatch_genai_action(args, parser=parser)


if __name__ == "__main__":
    main()
