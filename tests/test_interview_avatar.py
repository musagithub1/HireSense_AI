"""Regression coverage for the local 3D AI interviewer."""

from __future__ import annotations

import json
from pathlib import Path

import voice_input_component

ROOT = Path(__file__).parents[1]
FRONTEND = ROOT / "voice_input" / "frontend"


def test_avatar_is_a_local_accessible_threejs_component_with_fallback() -> None:
    source = (FRONTEND / "src" / "InterviewAvatar.tsx").read_text(
        encoding="utf-8"
    )
    engine = (FRONTEND / "src" / "MayaAvatar3D.ts").read_text(
        encoding="utf-8"
    )

    assert "export type InterviewState" in source
    for state in (
        "ready",
        "listening",
        "processing",
        "speaking",
        "paused",
        "error",
        "offline",
    ):
        assert f'"{state}"' in source + engine
    assert 'data-avatar-engine="threejs"' in source
    assert "StaticAvatarFallback" in source
    assert "<canvas" in source
    assert "<img" in source
    assert "HireSense 3D AI interviewer" in source
    assert "Interrupt interviewer" in source
    assert "new THREE.WebGLRenderer" in engine
    assert "makePortraitGeometry" in engine
    assert "maya-speak-a.webp" in engine
    assert "maya-speak-o.webp" in engine
    assert "maya-blink.webp" in engine
    assert "setSupportMode" in engine
    assert "setViseme" in engine
    assert "webglcontextlost" in engine
    assert "http://" not in source + engine
    assert "https://" not in source + engine

    for asset_name in (
        "maya-neutral.webp",
        "maya-speak-a.webp",
        "maya-speak-o.webp",
        "maya-blink.webp",
    ):
        asset = FRONTEND / "src" / "assets" / asset_name
        assert asset.is_file()
        assert 10_000 < asset.stat().st_size < 150_000


def test_voice_lifecycle_drives_avatar_and_recovery_controls() -> None:
    source = (FRONTEND / "src" / "main.js").read_text(encoding="utf-8")
    markup = (FRONTEND / "index.html").read_text(encoding="utf-8")

    assert "let interviewState" in source
    assert "function handleSpeechStart" in source
    assert "function handleSpeechEnd" in source
    assert "function handleSpeechPause" in source
    assert "function handleSpeechError" in source
    assert "function handleSpeechBoundary" in source
    assert "hiresense:maya-viseme" in source
    assert "function interruptInterviewer" in source
    assert "function showAudioFallback" in source
    assert 'id="interview-avatar"' in markup
    assert 'id="audio-fallback"' in markup
    assert 'id="question" tabindex="-1"' in markup
    assert "<summary>More options</summary>" in markup
    assert "<summary>Review live transcript</summary>" in markup
    assert "progressWrap.classList.add" in source
    assert "\"I'm done\"" in source


def test_live_mode_enables_interrupt_without_exposing_it_to_speaker_mode(
    monkeypatch,
) -> None:
    captured: list[dict] = []

    def fake_component(**kwargs):
        captured.append(kwargs)
        return None

    monkeypatch.setattr(voice_input_component, "_voice_component", fake_component)

    voice_input_component.render_voice_input(
        key="live",
        mode="live",
        question_text="Tell me about a difficult engineering decision.",
        interviewer_name="Maya",
        allow_interrupt=True,
        support_mode=True,
    )
    voice_input_component.render_voice_input(
        key="speaker",
        mode="speaker",
        question_text="Tell me about a difficult engineering decision.",
        interviewer_name="Maya",
        allow_interrupt=True,
    )

    assert captured[0]["interviewer_name"] == "Maya"
    assert captured[0]["allow_interrupt"] is True
    assert captured[0]["support_mode"] is True
    assert captured[1]["allow_interrupt"] is False
    assert captured[1]["support_mode"] is False


def test_frontend_manifest_pins_react_runtime() -> None:
    package = json.loads((FRONTEND / "package.json").read_text(encoding="utf-8"))

    assert package["dependencies"]["react"] == "19.1.1"
    assert package["dependencies"]["react-dom"] == "19.1.1"
    assert package["dependencies"]["three"] == "0.185.1"


def test_built_voice_bundle_contains_avatar_controls() -> None:
    bundles = list((FRONTEND / "dist" / "assets").glob("*.js"))
    assert len(bundles) == 1
    bundle = bundles[0].read_text(encoding="utf-8")

    assert "HireSense 3D AI interviewer" in bundle
    assert "Interrupt interviewer" in bundle
    assert "Audio unavailable" in bundle
    assert "hiresense:maya-viseme" in bundle
    assert "WebGLRenderer" in bundle
