#!/usr/bin/env python3
"""
Motor profesional y determinista de procesamiento de imágenes y recortes transparentes (cutouts)
para el video-pipeline.

Capacidades 100% locales (cero APIs en la nube):
  1. Conversión de formatos (PNG, WEBP, JPG, ICO, AVIF) preservando canal alfa y calidad.
  2. Recorte y encuadre inteligente (crop por caja x,y,w,h, aspect-ratio 9:16 / 16:9 / 1:1,
     resize con filtro Lanczos y modes 'contain' / 'cover', más auto-trim de bordes vacíos).
  3. Eliminación de fondo (Background Removal) con un único modelo neuronal de estudio:
     - 'ai' (defecto): Red neuronal DIS IS-Net General Use (isnet-general-use.onnx, 1024x1024)
       ejecutada localmente sobre ONNX Runtime con descarga y caché única en .cache/models/.
     - 'color': Extracción cromática determinista en espacio RGB/Euclidiano con feathering suave
       para fondos sólidos o chroma.
  4. Acabado de estudio para composiciones: contorno tipo sticker/cutout editorial y sombra paralela
     suave, listos para incrustar en escenas de HyperFrames (`assets/images/`).
"""

from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core._runtime import REPO_ROOT, ensure_local_venv, ensure_repo_root_on_path  # noqa: E402

ensure_repo_root_on_path()
_REPO_ROOT = REPO_ROOT

ISNET_MODEL_FILENAME = "isnet-general-use.onnx"
ISNET_MODEL_URL = (
    "https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-general-use.onnx"
)
ISNET_INPUT_SIZE: tuple[int, int] = (1024, 1024)
USER_AGENT = "video-pipeline-image-tools/1.0 (local-onnx-pillow)"

ASPECT_PRESETS: dict[str, tuple[int, int]] = {
    "9:16": (9, 16),
    "16:9": (16, 9),
    "1:1": (1, 1),
    "4:5": (4, 5),
    "4:3": (4, 3),
}


def load_image(path: Path | str) -> Image.Image:
    """Carga una imagen desde disco corrigiendo orientación EXIF."""
    src = Path(path)
    if not src.exists():
        raise FileNotFoundError(f"No se encontró el archivo de imagen: {src}")
    img = Image.open(src)
    return ImageOps.exif_transpose(img)


def save_image(
    img: Image.Image,
    output_path: Path | str,
    quality: int = 92,
) -> Path:
    """Guarda la imagen en el formato inferido por su extensión (.png, .webp, .jpg)."""
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    ext = dest.suffix.lower()

    if ext in {".jpg", ".jpeg"}:
        if img.mode in {"RGBA", "LA", "P"}:
            bg = Image.new("RGB", img.size, (9, 9, 11))
            rgba = img.convert("RGBA")
            bg.paste(rgba, mask=rgba.split()[3])
            img = bg
        else:
            img = img.convert("RGB")
        img.save(dest, format="JPEG", quality=quality, optimize=True)
    elif ext == ".webp":
        img.save(dest, format="WEBP", quality=quality, method=6)
    elif ext == ".png":
        img.save(dest, format="PNG", optimize=True)
    else:
        img.save(dest)
    return dest


def trim_transparent_or_solid_borders(
    img: Image.Image,
    padding: int = 0,
    tolerance: int = 12,
) -> Image.Image:
    """
    Recorta automáticamente márgenes transparentes (si tiene canal alfa con transparencias)
    o márgenes del mismo color sólido de la esquina superior izquierda.
    """
    rgba = img.convert("RGBA")
    arr = np.asarray(rgba, dtype=np.int16)
    alpha = arr[:, :, 3]

    if np.any(alpha < 250):
        mask = alpha > tolerance
    else:
        corner = arr[0, 0, :3]
        diff = np.abs(arr[:, :, :3] - corner).max(axis=2)
        mask = diff > tolerance

    coords = np.argwhere(mask)
    if coords.size == 0:
        return rgba

    y0, x0 = coords.min(axis=0)
    y1, x1 = coords.max(axis=0) + 1

    w, h = rgba.size
    x0 = max(0, int(x0) - padding)
    y0 = max(0, int(y0) - padding)
    x1 = min(w, int(x1) + padding)
    y1 = min(h, int(y1) + padding)
    return rgba.crop((x0, y0, x1, y1))


def crop_and_resize_image(
    img: Image.Image,
    box: tuple[int, int, int, int] | None = None,
    aspect: str | None = None,
    width: int | None = None,
    height: int | None = None,
    mode: str = "cover",
    auto_trim: bool = False,
    trim_padding: int = 0,
) -> Image.Image:
    """
    Aplica recorte por coordenadas (x, y, w, h), recorte por relación de aspecto centrada,
    auto-trim de bordes vacíos y redimensionamiento Lanczos ('cover', 'contain' o exacto).
    """
    work = img.convert("RGBA")

    if box is not None:
        bx, by, bw, bh = box
        if bw <= 0 or bh <= 0:
            raise ValueError(f"Dimensiones de recorte inválidas: {box}")
        work = work.crop((bx, by, bx + bw, by + bh))

    if auto_trim:
        work = trim_transparent_or_solid_borders(work, padding=trim_padding)

    if aspect:
        if aspect not in ASPECT_PRESETS:
            valid = ", ".join(ASPECT_PRESETS)
            raise ValueError(f"Relación de aspecto '{aspect}' no soportada. Válidas: {valid}")
        ar_w, ar_h = ASPECT_PRESETS[aspect]
        cur_w, cur_h = work.size
        target_ratio = ar_w / ar_h
        cur_ratio = cur_w / cur_h
        if cur_ratio > target_ratio:
            new_w = int(round(cur_h * target_ratio))
            x_off = (cur_w - new_w) // 2
            work = work.crop((x_off, 0, x_off + new_w, cur_h))
        elif cur_ratio < target_ratio:
            new_h = int(round(cur_w / target_ratio))
            y_off = (cur_h - new_h) // 2
            work = work.crop((0, y_off, cur_w, y_off + new_h))

    if width is not None or height is not None:
        cur_w, cur_h = work.size
        target_w = width or int(round(cur_w * (height / cur_h)))  # type: ignore[operator]
        target_h = height or int(round(cur_h * (width / cur_w)))  # type: ignore[operator]

        if mode == "cover":
            work = ImageOps.fit(work, (target_w, target_h), method=Image.Resampling.LANCZOS)
        elif mode == "contain":
            contained = ImageOps.contain(
                work, (target_w, target_h), method=Image.Resampling.LANCZOS
            )
            canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
            ox = (target_w - contained.width) // 2
            oy = (target_h - contained.height) // 2
            canvas.paste(contained, (ox, oy))
            work = canvas
        else:
            work = work.resize((target_w, target_h), resample=Image.Resampling.LANCZOS)

    return work


def _parse_hex_rgb(hex_color: str) -> tuple[int, int, int]:
    raw = hex_color.strip().lstrip("#")
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    if len(raw) != 6:
        raise ValueError(f"Color hexadecimal inválido: '{hex_color}'")
    return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)


def remove_background_color_key(
    img: Image.Image,
    key_color: str | tuple[int, int, int] | None = None,
    tolerance: float = 34.0,
    feather: float = 16.0,
) -> Image.Image:
    """
    Elimina un fondo sólido o cromático de forma determinista con transición suave (feathering).
    Si key_color es None, muestrea automáticamente la mediana de las 4 esquinas de la imagen.
    """
    rgba = img.convert("RGBA")
    arr = np.asarray(rgba, dtype=np.float32).copy()
    rgb = arr[:, :, :3]

    if key_color is None:
        corners = np.array(
            [
                rgb[0, 0],
                rgb[0, -1],
                rgb[-1, 0],
                rgb[-1, -1],
            ],
            dtype=np.float32,
        )
        target_rgb = np.median(corners, axis=0)
    elif isinstance(key_color, str):
        target_rgb = np.array(_parse_hex_rgb(key_color), dtype=np.float32)
    else:
        target_rgb = np.array(key_color, dtype=np.float32)

    dist = np.linalg.norm(rgb - target_rgb, axis=2)
    low = max(0.0, float(tolerance))
    high = max(low + 1.0, low + float(feather))

    alpha_factor = np.clip((dist - low) / (high - low), 0.0, 1.0)
    arr[:, :, 3] = arr[:, :, 3] * alpha_factor
    return Image.fromarray(arr.astype(np.uint8), mode="RGBA")


def ensure_onnx_rembg_model(model_dir: Path | None = None) -> Path:
    """Garantiza que el modelo ONNX de estudio IS-Net (1024x1024) esté cacheado localmente."""
    target_dir = model_dir or (_REPO_ROOT / ".cache" / "models")
    target_dir.mkdir(parents=True, exist_ok=True)
    model_path = target_dir / ISNET_MODEL_FILENAME
    if model_path.exists() and model_path.stat().st_size > 100_000:
        return model_path

    print(f"[ImageTools] Descargando modelo ONNX de estudio ({ISNET_MODEL_FILENAME})...")
    req = urllib.request.Request(ISNET_MODEL_URL, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=120.0) as resp:  # noqa: S310
            data = resp.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"No se pudo descargar el modelo ONNX desde {ISNET_MODEL_URL}: {exc}"
        ) from exc

    model_path.write_bytes(data)
    return model_path


def remove_background_onnx(
    img: Image.Image,
    model_path: Path | None = None,
) -> Image.Image:
    """
    Elimina el fondo de retratos, objetos o fotografías ejecutando el modelo de estudio
    DIS IS-Net (1024x1024) directamente sobre ONNX Runtime en local (cero llamadas a la nube).
    """
    import onnxruntime as ort

    resolved_model = (
        model_path if (model_path and model_path.exists()) else ensure_onnx_rembg_model()
    )
    rgba = img.convert("RGBA")
    orig_w, orig_h = rgba.size

    in_w, in_h = ISNET_INPUT_SIZE
    resized = rgba.convert("RGB").resize((in_w, in_h), resample=Image.Resampling.BILINEAR)
    arr = np.asarray(resized, dtype=np.float32)
    max_val = float(arr.max())
    if max_val > 0.0:
        arr = arr / max_val
    norm = arr - 0.5
    tensor = np.transpose(norm, (2, 0, 1))[np.newaxis, :, :, :].astype(np.float32)

    sess = ort.InferenceSession(str(resolved_model), providers=["CPUExecutionProvider"])
    input_name = sess.get_inputs()[0].name
    outputs = sess.run(None, {input_name: tensor})
    pred = np.squeeze(outputs[0])

    p_min, p_max = float(pred.min()), float(pred.max())
    if p_max > p_min:
        pred = (pred - p_min) / (p_max - p_min)
    mask_u8 = (np.clip(pred, 0.0, 1.0) * 255.0).astype(np.uint8)
    mask_img = Image.fromarray(mask_u8, mode="L").resize(
        (orig_w, orig_h), resample=Image.Resampling.LANCZOS
    )

    out_arr = np.asarray(rgba, dtype=np.uint8).copy()
    mask_arr = np.asarray(mask_img, dtype=np.float32) / 255.0
    out_arr[:, :, 3] = (out_arr[:, :, 3].astype(np.float32) * mask_arr).astype(np.uint8)
    return Image.fromarray(out_arr, mode="RGBA")


def apply_cutout_outline_and_shadow(
    img: Image.Image,
    outline_width: int = 0,
    outline_color: str = "#ffffff",
    shadow_blur: int = 0,
    shadow_offset: tuple[int, int] = (0, 10),
    shadow_opacity: float = 0.55,
) -> Image.Image:
    """
    Aplica acabado de estudio tipo cutout/sticker sobre una imagen con transparencia (RGBA):
      - Contorno uniforme perimetral (outline_width > 0) mediante dilatación morfológica MaxFilter.
      - Sombra paralela difuminada (shadow_blur > 0) para separar el sujeto del fondo en HyperFrames.
    """
    rgba = img.convert("RGBA")
    pad = (
        max(0, outline_width * 2)
        + max(0, shadow_blur * 2)
        + max(abs(shadow_offset[0]), abs(shadow_offset[1]))
        + 8
    )
    if outline_width <= 0 and shadow_blur <= 0:
        return rgba

    new_w = rgba.width + pad * 2
    new_h = rgba.height + pad * 2
    canvas = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
    alpha = rgba.split()[3]

    # 1. Sombra paralela
    if shadow_blur > 0:
        sh_layer = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
        sh_alpha = alpha.point(lambda a: int(a * max(0.0, min(1.0, shadow_opacity))))
        sh_color_img = Image.new("RGBA", rgba.size, (0, 0, 0, 255))
        sh_layer.paste(
            sh_color_img, (pad + shadow_offset[0], pad + shadow_offset[1]), mask=sh_alpha
        )
        sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(radius=shadow_blur))
        canvas = Image.alpha_composite(canvas, sh_layer)

    # 2. Contorno de recorte (sticker outline)
    if outline_width > 0:
        padded_alpha = Image.new("L", (new_w, new_h), 0)
        padded_alpha.paste(alpha, (pad, pad))
        kernel_size = outline_width * 2 + 1
        dilated = padded_alpha.filter(ImageFilter.MaxFilter(size=kernel_size))
        dilated = dilated.filter(ImageFilter.GaussianBlur(radius=0.8))
        rgb_col = _parse_hex_rgb(outline_color)
        outline_layer = Image.new("RGBA", (new_w, new_h), (*rgb_col, 255))
        outline_layer.putalpha(dilated)
        canvas = Image.alpha_composite(canvas, outline_layer)

    # 3. Sujeto principal encima
    subj_layer = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
    subj_layer.paste(rgba, (pad, pad), mask=alpha)
    return Image.alpha_composite(canvas, subj_layer)


def _parse_crop_box(spec: str | None) -> tuple[int, int, int, int] | None:
    if not spec:
        return None
    parts = [int(p.strip()) for p in spec.split(",")]
    if len(parts) != 4:
        raise ValueError("El formato de --box debe ser 'x,y,ancho,alto' (ej. '100,50,600,600').")
    return parts[0], parts[1], parts[2], parts[3]


def process_image_pipeline(
    input_path: Path | str,
    output_path: Path | str,
    remove_bg: str | None = None,
    key_color: str | None = None,
    tolerance: float = 34.0,
    feather: float = 16.0,
    crop_box: tuple[int, int, int, int] | None = None,
    aspect: str | None = None,
    width: int | None = None,
    height: int | None = None,
    resize_mode: str = "cover",
    auto_trim: bool = False,
    trim_padding: int = 0,
    outline_width: int = 0,
    outline_color: str = "#ffffff",
    shadow_blur: int = 0,
    quality: int = 92,
) -> Path:
    """
    Ejecuta una tubería completa sobre una imagen:
      Carga -> Eliminación de fondo (opcional) -> Recorte/Auto-Trim/Resize -> Contorno/Sombra -> Guardado.
    """
    img = load_image(input_path)

    if remove_bg == "color":
        img = remove_background_color_key(
            img, key_color=key_color, tolerance=tolerance, feather=feather
        )
    elif remove_bg == "ai":
        img = remove_background_onnx(img)
    elif remove_bg is not None:
        raise ValueError(f"Modo remove_bg '{remove_bg}' inválido. Usa 'ai' o 'color'.")

    img = crop_and_resize_image(
        img,
        box=crop_box,
        aspect=aspect,
        width=width,
        height=height,
        mode=resize_mode,
        auto_trim=auto_trim,
        trim_padding=trim_padding,
    )

    if outline_width > 0 or shadow_blur > 0:
        img = apply_cutout_outline_and_shadow(
            img,
            outline_width=outline_width,
            outline_color=outline_color,
            shadow_blur=shadow_blur,
        )

    out = save_image(img, output_path, quality=quality)
    print(f"[ImageTools] Procesada: {out} ({img.width}x{img.height}px, {img.mode})")
    return out


def register_image_subparsers(
    parser: argparse.ArgumentParser,
    dest: str = "image_action",
) -> None:
    """Registra los subcomandos de procesamiento de imágenes en el parser indicado."""
    sub = parser.add_subparsers(dest=dest, help="Acción sobre imagen")

    # 1. Subcomando: convert
    p_conv = sub.add_parser(
        "convert", help="Convertir formato (PNG, WEBP, JPG) y redimensionar con filtro Lanczos"
    )
    p_conv.add_argument("-i", "--input", required=True, help="Imagen de entrada")
    p_conv.add_argument("-o", "--output", required=True, help="Ruta de salida (.png, .webp, .jpg)")
    p_conv.add_argument("--width", type=int, help="Ancho destino en píxeles")
    p_conv.add_argument("--height", type=int, help="Alto destino en píxeles")
    p_conv.add_argument(
        "--mode",
        choices=["cover", "contain", "stretch"],
        default="cover",
        help="Modo de ajuste al redimensionar (defecto: cover)",
    )
    p_conv.add_argument("--quality", type=int, default=92, help="Calidad WEBP/JPEG (1-100)")

    # 2. Subcomando: crop
    p_crop = sub.add_parser(
        "crop",
        help="Recortar por coordenadas, aspect-ratio (9:16, 16:9, 1:1) o auto-trim de bordes",
    )
    p_crop.add_argument("-i", "--input", required=True, help="Imagen de entrada")
    p_crop.add_argument("-o", "--output", required=True, help="Imagen de salida")
    p_crop.add_argument("--box", help="Caja exacta 'x,y,ancho,alto' en píxeles")
    p_crop.add_argument(
        "--aspect",
        choices=list(ASPECT_PRESETS.keys()),
        help="Recorte centrado a relación de aspecto (9:16, 16:9, 1:1, 4:5, 4:3)",
    )
    p_crop.add_argument(
        "--trim", action="store_true", help="Recortar automáticamente bordes vacíos o sólidos"
    )
    p_crop.add_argument(
        "--padding", type=int, default=0, help="Margen extra en píxeles tras --trim"
    )
    p_crop.add_argument("--width", type=int, help="Ancho final opcional")
    p_crop.add_argument("--height", type=int, help="Alto final opcional")
    p_crop.add_argument(
        "--mode",
        choices=["cover", "contain", "stretch"],
        default="cover",
        help="Modo de redimensionamiento si se indican --width/--height",
    )

    # 3. Subcomando: rembg
    p_bg = sub.add_parser(
        "rembg",
        help="Eliminar el fondo (por IA local ONNX IS-Net 1024x1024 o extracción cromática) y generar cutout con borde/sombra",
    )
    p_bg.add_argument("-i", "--input", required=True, help="Imagen de entrada")
    p_bg.add_argument(
        "-o", "--output", required=True, help="Imagen de salida (.png o .webp transparente)"
    )
    p_bg.add_argument(
        "-m",
        "--method",
        choices=["ai", "color"],
        default="ai",
        help="Método: 'ai' (red neuronal ONNX IS-Net 1024x1024 de estudio, defecto) o 'color' (fondo sólido/chroma)",
    )
    p_bg.add_argument(
        "--color", help="Color hexadecimal del fondo a eliminar en modo color (ej. '#ffffff')"
    )
    p_bg.add_argument(
        "--tolerance", type=float, default=34.0, help="Tolerancia de color (0-255, defecto: 34)"
    )
    p_bg.add_argument(
        "--feather", type=float, default=16.0, help="Suavizado de bordes (defecto: 16)"
    )
    p_bg.add_argument(
        "--trim", action="store_true", help="Ajustar caja al sujeto recortando bordes vacíos"
    )
    p_bg.add_argument(
        "--padding", type=int, default=12, help="Margen alrededor del sujeto al usar --trim"
    )
    p_bg.add_argument(
        "--outline", type=int, default=0, help="Grosor en px del borde estilo sticker/cutout"
    )
    p_bg.add_argument(
        "--outline-color", default="#ffffff", help="Color del borde cutout (defecto: #ffffff)"
    )
    p_bg.add_argument(
        "--shadow",
        type=int,
        default=0,
        help="Radio de desenfoque de sombra paralela (0 = sin sombra)",
    )


def dispatch_image_action(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
    action_attr: str = "image_action",
) -> None:
    """Ejecuta la acción de procesamiento de imágenes seleccionada en un argparse.Namespace."""
    img_act = getattr(args, action_attr, None)
    if not img_act:
        parser.print_help()
        sys.exit(0)
    elif img_act == "convert":
        process_image_pipeline(
            input_path=args.input,
            output_path=args.output,
            width=args.width,
            height=args.height,
            resize_mode=args.mode,
            quality=args.quality,
        )
    elif img_act == "crop":
        process_image_pipeline(
            input_path=args.input,
            output_path=args.output,
            crop_box=_parse_crop_box(args.box),
            aspect=args.aspect,
            auto_trim=args.trim,
            trim_padding=args.padding,
            width=args.width,
            height=args.height,
            resize_mode=args.mode,
        )
    elif img_act == "rembg":
        process_image_pipeline(
            input_path=args.input,
            output_path=args.output,
            remove_bg=args.method,
            key_color=args.color,
            tolerance=args.tolerance,
            feather=args.feather,
            auto_trim=args.trim,
            trim_padding=args.padding,
            outline_width=args.outline,
            outline_color=args.outline_color,
            shadow_blur=args.shadow,
        )


def main() -> None:
    ensure_local_venv()
    parser = argparse.ArgumentParser(
        description="Herramientas profesionales de recorte, conversión y eliminación de fondo de imágenes."
    )
    register_image_subparsers(parser, dest="image_action")
    args = parser.parse_args()
    dispatch_image_action(args, parser=parser, action_attr="image_action")


if __name__ == "__main__":
    main()
