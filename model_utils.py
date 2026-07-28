"""Small, provider-agnostic helpers for model response handling."""

from __future__ import annotations

import json
import re
from typing import Any


def message_text(content: Any) -> str:
    """Normalize text returned as a string or OpenAI-style content blocks."""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""

    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict):
            text = block.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "".join(parts)


def without_reasoning_markup(text: str) -> str:
    """Remove reasoning wrappers that some compatible providers may emit."""
    cleaned = re.sub(
        r"<think\b[^>]*>[\s\S]*?</think\s*>",
        "",
        str(text),
        flags=re.IGNORECASE,
    )
    return cleaned.strip()


def normalize_question(text: str) -> str:
    """Return one candidate-facing question without provider preamble."""
    cleaned = without_reasoning_markup(text)
    cleaned = re.sub(r"^```(?:text|markdown)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip().strip('"“”')

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    while len(lines) > 1 and re.fullmatch(
        r"(?:here(?:'s| is) (?:the )?question|question|interview question)\s*:?",
        lines[0],
        flags=re.IGNORECASE,
    ):
        lines.pop(0)
    cleaned = " ".join(lines)
    cleaned = re.sub(
        r"^(?:question|interview question)\s*(?:\d+\s*)?:\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"^[*\-\u2022]\s*", "", cleaned).strip()

    # The candidate interface expects one question. Keep an optional short
    # welcome sentence, but drop any second question or trailing commentary.
    first_question_mark = cleaned.find("?")
    if first_question_mark >= 0:
        cleaned = cleaned[: first_question_mark + 1]
    return " ".join(cleaned.split())


def extract_json_object(text: str) -> dict[str, Any] | None:
    """Decode the first complete JSON object from a model response."""
    cleaned = without_reasoning_markup(text)
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        value = None
        for index, character in enumerate(cleaned):
            if character != "{":
                continue
            try:
                candidate, _ = decoder.raw_decode(cleaned[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict):
                value = candidate
                break
        if value is None:
            return None
    return value if isinstance(value, dict) else None
