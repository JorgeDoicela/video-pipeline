"""
Pruebas unitarias para el motor de procesamiento de imágenes y recortes transparentes (core/image_tools.py):
  - Conversión de formatos (PNG, WEBP, JPG)
  - Recorte por caja, aspect-ratio (9:16, 16:9, 1:1) y auto-trim de bordes vacíos
  - Eliminación de fondo por extracción cromática (color key + feathering) y por IA local ONNX (U2-NetP)
  - Acabado de cutout tipo sticker (contorno dilatado + sombra paralela)
  - Componente narrativo image_cutout en core/scenes.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from core.image_tools import (
    apply_cutout_outline_and_shadow,
    crop_and_resize_image,
    process_image_pipeline,
    remove_background_color_key,
    remove_background_onnx,
    trim_transparent_or_solid_borders,
)
from core.scenes import SceneSpec, StoryboardSpec, build_storyboard_html_and_gsap


def _make_sample_subject_on_white(size: tuple[int, int] = (240, 200)) -> Image.Image:
    """Crea una imagen RGB de prueba con fondo blanco (#ffffff) y un círculo rojo central."""
    img = Image.new("RGB", size, (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.ellipse((70, 50, 170, 150), fill=(220, 38, 38))
    return img


def test_remove_background_color_key_and_auto_trim():
    src = _make_sample_subject_on_white((240, 200))
    cutout = remove_background_color_key(src, key_color=None, tolerance=25.0, feather=10.0)
    assert cutout.mode == "RGBA"

    arr = np.asarray(cutout)
    # Las esquinas deben ser 100% transparentes y el centro 100% opaco
    assert arr[0, 0, 3] == 0
    assert arr[-1, -1, 3] == 0
    assert arr[100, 120, 3] == 255

    trimmed = trim_transparent_or_solid_borders(cutout, padding=4)
    # El círculo original ocupaba 100x100; con padding=4 debe quedar cerca de 108x108
    assert 100 <= trimmed.width <= 116
    assert 100 <= trimmed.height <= 116


def test_crop_aspect_ratio_and_format_conversion(tmp_path: Path):
    src = _make_sample_subject_on_white((400, 400))
    in_path = tmp_path / "raw.png"
    src.save(in_path, format="PNG")

    # Recorte 9:16 + redimensionado a 270x480 en WEBP
    out_webp = tmp_path / "vertical.webp"
    process_image_pipeline(
        input_path=in_path,
        output_path=out_webp,
        aspect="9:16",
        width=270,
        height=480,
        resize_mode="cover",
    )
    assert out_webp.exists()
    with Image.open(out_webp) as res_img:
        assert res_img.size == (270, 480)

    # Modo contain sobre imagen rectangular
    contained = crop_and_resize_image(src, width=300, height=150, mode="contain")
    assert contained.size == (300, 150)


def test_apply_cutout_outline_and_shadow_and_full_pipeline(tmp_path: Path):
    src = _make_sample_subject_on_white((200, 200))
    in_path = tmp_path / "logo_white_bg.png"
    src.save(in_path, format="PNG")

    out_cutout = tmp_path / "logo_cutout.png"
    process_image_pipeline(
        input_path=in_path,
        output_path=out_cutout,
        remove_bg="color",
        auto_trim=True,
        trim_padding=6,
        outline_width=5,
        outline_color="#ffffff",
        shadow_blur=6,
    )
    assert out_cutout.exists()
    with Image.open(out_cutout) as final_img:
        assert final_img.mode == "RGBA"
        arr = np.asarray(final_img)
        # Debe conservar transparencia exterior y sujeto opaco en el centro
        assert arr[0, 0, 3] == 0
        assert arr[final_img.height // 2, final_img.width // 2, 3] == 255

    # Verificar que sin outline ni shadow devuelve las mismas dimensiones
    plain = apply_cutout_outline_and_shadow(src.convert("RGBA"), outline_width=0, shadow_blur=0)
    assert plain.size == (200, 200)


def test_remove_background_onnx_inference_pipeline(tmp_path: Path, monkeypatch):
    src = _make_sample_subject_on_white((160, 120))
    fake_model = tmp_path / "model.onnx"
    fake_model.write_bytes(b"FAKE_ONNX")
    observed_shapes: list[tuple[int, ...]] = []

    class FakeInput:
        name = "input.1"

    class FakeSession:
        def __init__(self, path: str, providers: list[str]):
            self.path = path

        def get_inputs(self):
            return [FakeInput()]

        def run(self, output_names, feed):
            tensor = feed["input.1"]
            observed_shapes.append(tensor.shape)
            _, _, h, w = tensor.shape
            mask = np.zeros((1, 1, h, w), dtype=np.float32)
            mask[:, :, h // 4 : (3 * h) // 4, w // 4 : (3 * w) // 4] = 1.0
            return [mask]

    monkeypatch.setattr("onnxruntime.InferenceSession", FakeSession)

    # 1. Modelo por defecto 'isnet' (1024x1024 de estudio)
    res_isnet = remove_background_onnx(src, model_slug="isnet", model_path=fake_model)
    assert res_isnet.size == (160, 120)
    assert res_isnet.mode == "RGBA"
    assert observed_shapes[-1] == (1, 3, 1024, 1024)
    arr = np.asarray(res_isnet)
    assert arr[0, 0, 3] == 0
    assert arr[60, 80, 3] == 255

    # 2. Modelo 'silueta' y 'u2netp' (320x320)
    res_sil = remove_background_onnx(src, model_slug="silueta", model_path=fake_model)
    assert res_sil.size == (160, 120)
    assert observed_shapes[-1] == (1, 3, 320, 320)


def test_image_cutout_scene_component():
    sb = StoryboardSpec(
        title="Cutout Test",
        duration=4.0,
        scenes=[
            SceneSpec(
                id="sc_cut",
                start=0.0,
                end=4.0,
                headline="",
                component="image_cutout",
                props={
                    "src": "pegasus_sticker.png",
                    "title": "EVIDENCIA FORENSE",
                    "subtitle": "Recorte transparente con contorno",
                },
            )
        ],
    )
    html_out, gsap_out = build_storyboard_html_and_gsap(sb)
    assert "../../assets/images/pegasus_sticker.png" in html_out
    assert "sc_cut_cutout_img" in html_out
    assert "EVIDENCIA FORENSE" in html_out
    assert "sc_cut_cutout_stage" in gsap_out
