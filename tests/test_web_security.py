"""Regression tests for values embedded in generated browser scripts."""

from __future__ import annotations

import json

from language_support import get_language_specific_tts_html
from live_copilot import get_copilot_component_html
from video_recording import get_recordings_list_html
from web_utils import json_for_script


def test_json_for_script_blocks_closing_tag() -> None:
    payload = '</script><script>alert("x")</script>'
    encoded = json_for_script(payload)
    assert "</script>" not in encoded
    assert json.loads(encoded) == payload


def test_tts_html_does_not_embed_raw_script_close() -> None:
    html = get_language_specific_tts_html("</script><b>unsafe</b>", "en")
    assert "</script><b>" not in html
    assert "\\u003c/script\\u003e" in html


def test_copilot_uses_text_nodes_for_model_supplied_key_points() -> None:
    html = get_copilot_component_html(
        resume_context="resume",
        jd_context="role",
        key_points={"key_achievements": ['<img src=x onerror="alert(1)">']},
    )
    assert "list.innerHTML = items" not in html
    assert "element.textContent = String(item)" in html
    assert '<img src=x onerror="alert(1)">' not in html


def test_recording_history_does_not_render_storage_values_as_html() -> None:
    html = get_recordings_list_html()
    assert "card.innerHTML" not in html
    assert "item.textContent = value" in html
