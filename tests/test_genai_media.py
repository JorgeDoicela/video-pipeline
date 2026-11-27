"""
Pruebas unitarias para el conector opcional Google Gemini API (core/genai_media.py).
Todas las pruebas corren sin conexión de red ni GEMINI_API_KEY real (aptas para CI).
"""

import base64
import json
from types import SimpleNamespace

import pytest

from core.genai_media import (
    GENAI_MODEL_CATALOG,
    check_genai_environment,
    generate_genai_image,
    generate_genai_music,
    generate_genai_tts,
    generate_genai_video,
    sanitize_error,
    validate_model_name,
    validate_omni_constraints,
)


def _fake_sdk_modules(client_factory):
    class _FakeAPIError(Exception):
        pass

    class _FakeHttpOptions:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class _FakeUploadConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    fake_genai = SimpleNamespace(Client=client_factory)
    fake_types = SimpleNamespace(HttpOptions=_FakeHttpOptions, UploadFileConfig=_FakeUploadConfig)
    fake_errors = SimpleNamespace(APIError=_FakeAPIError)
    return fake_genai, fake_types, fake_errors


def test_sanitize_error_and_api_key_safety(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaFakeSecretKeyForTesting1234567890")
    raw = (
        "Failed request https://generativelanguage.googleapis.com/v1beta/test?key=AIzaFakeSecretKeyForTesting1234567890 "
        "with header Bearer ya29.SomeOAuthSecretToken"
    )
    clean = sanitize_error(raw)
    assert "AIzaFakeSecretKey" not in clean
    assert "ya29.SomeOAuthSecretToken" not in clean
    assert "[REDACTED_KEY]" in clean
    assert "[REDACTED_TOKEN]" in clean

    env_info = check_genai_environment()
    assert env_info["api_key_configured"] is True
    assert "AIza" not in json.dumps(env_info)


def test_validate_model_rejects_deprecated():
    assert validate_model_name("", "video") == GENAI_MODEL_CATALOG["video"]["default"]
    assert validate_model_name("gemini-nano-banana-2.1", "image") == "gemini-nano-banana-2.1"

    for bad, kind in (
        ("gemini-2.5-flash", "image"),
        ("gemini-omni-1.1-flash", "video"),
        ("gemini-3.1-flash-tts-preview", "tts"),
    ):
        with pytest.raises(ValueError, match="obsoleto"):
            validate_model_name(bad, kind)


def test_validate_omni_constraints_catches_invalid_combinations():
    assert validate_omni_constraints(duration=8, aspect_ratio="9:16", resolution="1080p") == (
        "8s",
        "9:16",
        "1080p",
    )

    with pytest.raises(ValueError, match="between|entre"):
        validate_omni_constraints(duration=2)
    with pytest.raises(ValueError, match="first-frame"):
        validate_omni_constraints(last_frame="end.png")
    with pytest.raises(ValueError, match="máximo 10s"):
        validate_omni_constraints(duration=12, first_frame="a.png", last_frame="b.png")
    with pytest.raises(ValueError, match="--video-reference"):
        validate_omni_constraints(video_input="clip.mp4", video_references=["ref.mp4"])
    with pytest.raises(ValueError, match="Resolución"):
        validate_omni_constraints(resolution="8k")
    with pytest.raises(ValueError, match="6 imágenes"):
        validate_omni_constraints(
            first_frame="f1.png",
            last_frame="f2.png",
            ref_images=["r1.png", "r2.png", "r3.png", "r4.png", "r5.png"],
        )


def test_generate_genai_image_with_reference_and_output_path(tmp_path, monkeypatch):
    ref_img = tmp_path / "coco.jpg"
    ref_img.write_bytes(b"FAKE_JPEG_DATA")
    out_img = tmp_path / "out" / "fresa.png"

    captured: list[dict] = []

    class FakeClient:
        def __init__(self, **kwargs):
            self.interactions = SimpleNamespace(create=self._create)

        def _create(self, **kwargs):
            captured.append(kwargs)
            return SimpleNamespace(
                id="v1_img_turn1",
                output_image=SimpleNamespace(
                    data=base64.b64encode(b"PNG_OUT_BYTES").decode("ascii"),
                    mime_type="image/png",
                ),
            )

    monkeypatch.setenv("GEMINI_API_KEY", "AIzaUnitTestingKey000000000000000000")
    monkeypatch.setattr("core.genai_media.load_genai_sdk", lambda: _fake_sdk_modules(FakeClient))

    res = generate_genai_image(
        "Fresa Valentina en Coco's Scoops",
        reference_images=[ref_img],
        aspect_ratio="9:16",
        image_size="2K",
        output_path=out_img,
    )
    assert res.output_path == out_img
    assert out_img.read_bytes() == b"PNG_OUT_BYTES"
    assert res.interaction_id == "v1_img_turn1"
    assert captured[0]["model"] == "gemini-nano-banana-2.1"
    assert captured[0]["response_format"]["aspect_ratio"] == "9:16"
    assert captured[0]["input"][1]["mime_type"] == "image/jpeg"


def test_generate_genai_video_uploads_first_frame_polls_and_downloads(tmp_path, monkeypatch):
    frame1 = tmp_path / "act1.png"
    frame1.write_bytes(b"PNG_FRAME1")
    out_mp4 = tmp_path / "scene.mp4"

    calls: dict = {"get_count": 0, "create": None, "downloaded": None}

    class FakeClient:
        def __init__(self, **kwargs):
            self.files = SimpleNamespace(
                upload=self._upload,
                get=self._get,
                download=self._download,
            )
            self.interactions = SimpleNamespace(create=self._create)

        def _upload(self, file, config):
            return SimpleNamespace(
                name="files/abc123", uri="https://generativelanguage.googleapis.com/files/abc123"
            )

        def _get(self, name):
            calls["get_count"] += 1
            state = "PROCESSING" if calls["get_count"] == 1 else "ACTIVE"
            return SimpleNamespace(
                name=name,
                uri=f"https://generativelanguage.googleapis.com/{name}",
                mime_type="image/png",
                state=SimpleNamespace(name=state),
            )

        def _create(self, **kwargs):
            calls["create"] = kwargs
            return SimpleNamespace(
                id="v1_vid_99",
                output_video=SimpleNamespace(
                    uri="https://generativelanguage.googleapis.com/files/outvid777"
                ),
            )

        def _download(self, file):
            calls["downloaded"] = file
            return b"FAKE_MP4_STREAM"

    monkeypatch.setenv("GEMINI_API_KEY", "AIzaUnitTestingKey000000000000000000")
    monkeypatch.setattr("core.genai_media.load_genai_sdk", lambda: _fake_sdk_modules(FakeClient))
    monkeypatch.setattr("core.genai_media.time.sleep", lambda _: None)

    res = generate_genai_video(
        "Coco smiles and blinks",
        first_frame=frame1,
        aspect_ratio="9:16",
        resolution="1080p",
        duration=5,
        output_path=out_mp4,
    )
    assert res.output_path == out_mp4
    assert out_mp4.read_bytes() == b"FAKE_MP4_STREAM"
    assert calls["get_count"] == 2
    assert calls["create"]["response_format"]["aspect_ratio"] == "9:16"
    assert calls["create"]["response_format"]["duration"] == "5s"
    assert calls["create"]["input"][0]["type"] == "image"
    assert "files/outvid777" in calls["downloaded"]


def test_generate_genai_tts_multispeaker_and_music(tmp_path, monkeypatch):
    calls: list[dict] = []

    class FakeClient:
        def __init__(self, **kwargs):
            calls.append({"client_init": kwargs})
            self.interactions = SimpleNamespace(create=self._create)

        def _create(self, **kwargs):
            calls.append({"create": kwargs})
            return SimpleNamespace(
                id="v1_audio_1",
                output_audio=SimpleNamespace(
                    data=base64.b64encode(b"RIFF_AUDIO_BYTES").decode("ascii"),
                    mime_type="audio/wav",
                ),
                output_text="Instrumental cue",
            )

    monkeypatch.setenv("GEMINI_API_KEY", "AIzaUnitTestingKey000000000000000000")
    monkeypatch.setattr("core.genai_media.load_genai_sdk", lambda: _fake_sdk_modules(FakeClient))

    tts_out = tmp_path / "dialogo.wav"
    res_tts = generate_genai_tts(
        "Coco: Bienvenida.\nFresa: Dame el secreto.",
        speakers="Coco=Puck,Fresa=Kore",
        style="dramatic novela tone",
        normalize_wav=False,
        output_path=tts_out,
    )
    assert res_tts.output_path == tts_out
    assert tts_out.read_bytes() == b"RIFF_AUDIO_BYTES"
    assert calls[0]["client_init"] == {"http_options": {"api_version": "v1beta"}}
    assert len(calls[1]["create"]["input"][0]["content"]) == 2
    assert (
        calls[1]["create"]["generation_config"]["speech_config"]["speakers"][0]["speaker"] == "Coco"
    )

    mus_out = tmp_path / "telenovela.mp3"
    res_mus = generate_genai_music(
        "Warm dramatic guitar soundtrack",
        normalize_wav=False,
        output_path=mus_out,
    )
    assert res_mus.output_path == mus_out
    assert mus_out.read_bytes() == b"RIFF_AUDIO_BYTES"
    assert res_mus.extra_text == "Instrumental cue"


def test_generate_genai_tts_turns_json_single_speaker_and_normalize(tmp_path, monkeypatch):
    calls: list[dict] = []
    turns_path = tmp_path / "turns.json"
    turns_path.write_text(
        json.dumps(
            [{"speaker": "Narrador", "voice": "Puck", "style": "calm", "text": "Acto uno."}]
        ),
        encoding="utf-8",
    )

    class FakeClient:
        def __init__(self, **kwargs):
            self.interactions = SimpleNamespace(create=self._create)

        def _create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                id="v1_tts_turns",
                output_audio=SimpleNamespace(
                    data=base64.b64encode(b"RAW_WAV").decode("ascii"),
                    mime_type="audio/wav",
                ),
            )

    ffmpeg_cmds: list[list[str]] = []

    def fake_run(cmd, check=False, stdout=None, stderr=None):
        ffmpeg_cmds.append(cmd)
        from pathlib import Path

        Path(cmd[-1]).write_bytes(b"WAV_48K_STEREO")
        return SimpleNamespace(returncode=0, stderr=b"")

    monkeypatch.setenv("GEMINI_API_KEY", "AIzaUnitTestingKey000000000000000000")
    monkeypatch.setattr("core.genai_media.load_genai_sdk", lambda: _fake_sdk_modules(FakeClient))
    monkeypatch.setattr("core.genai_media.subprocess.run", fake_run)

    out_wav = tmp_path / "narrador.wav"
    res = generate_genai_tts(turns_file=turns_path, normalize_wav=True, output_path=out_wav)
    assert res.output_path == out_wav
    assert out_wav.read_bytes() == b"WAV_48K_STEREO"
    assert calls[0]["generation_config"]["speech_config"] == [{"voice": "Puck"}]
    assert len(ffmpeg_cmds) == 1

    bad_turns = tmp_path / "bad.json"
    bad_turns.write_text(json.dumps([{"speaker": "Solo"}]), encoding="utf-8")
    with pytest.raises(ValueError, match="requiere 'speaker' y 'text'"):
        generate_genai_tts(turns_file=bad_turns)


def test_load_dotenv_if_present_respects_existing_env_vars(tmp_path, monkeypatch):
    from core._runtime import load_dotenv_if_present

    dotenv = tmp_path / ".env"
    dotenv.write_text(
        '# Comentario\nGEMINI_API_KEY="from_dotenv_value"\nexport CUSTOM_VP_VAR=hola\nEMPTY_VAR=\n',
        encoding="utf-8",
    )
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("CUSTOM_VP_VAR", "from_os_env")

    assert load_dotenv_if_present(dotenv) is True
    import os

    assert os.environ["GEMINI_API_KEY"] == "from_dotenv_value"
    # Variable ya existente en el SO no se sobrescribe
    assert os.environ["CUSTOM_VP_VAR"] == "from_os_env"
    assert "EMPTY_VAR" not in os.environ
