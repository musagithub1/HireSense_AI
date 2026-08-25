from __future__ import annotations

import concurrent.futures as cf
import json
import os
import time
from pathlib import Path
from typing import Any

from openai import OpenAI

ROOT = Path(__file__).parent
CURRICULUM = json.loads((ROOT / "curriculum.json").read_text())
OUT = ROOT / "episode_specs.json"
MODEL = os.getenv("CHEM_MODEL", "gpt-5-mini")

SCHEMA = {
    "type": "object",
    "properties": {
        "episodes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "number": {"type": "integer"},
                    "title": {"type": "string"},
                    "hook": {"type": "string"},
                    "teaching_claim": {"type": "string"},
                    "misconception": {"type": "string"},
                    "takeaway": {"type": "string"},
                    "beats": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "caption": {"type": "string"},
                                "visual_action": {"type": "string"},
                                "idiom": {"type": "string"}
                            },
                            "required": ["caption", "visual_action", "idiom"],
                            "additionalProperties": False
                        },
                        "minItems": 4,
                        "maxItems": 5
                    },
                    "closing": {"type": "string"}
                },
                "required": ["number", "title", "hook", "teaching_claim", "misconception", "takeaway", "beats", "closing"],
                "additionalProperties": False
            }
        }
    },
    "required": ["episodes"],
    "additionalProperties": False
}

SYSTEM = """You are the lead chemistry educator and storyboard writer for a 1,000-episode short-form chemistry series. Write accurate, self-contained explanations for a general learner who may have no prior chemistry beyond the topic's prerequisites. Each episode must answer one clear question in about 60 seconds using five compact caption lines: the hook/title, four concept beats, and a closing answer. Captions must be plain spoken English, ideally under 40 characters, and must not depend on voiceover. Visual actions must be continuous and explain the chemistry, not merely decorate it. Use only the requested idioms: decomposition, space, relationship network, stacking, distribution, particles, molecular model, energy diagram, phase diagram, reaction pathway, or titration curve. Avoid unsupported numerical claims, unsafe procedural instructions, and excessive equations. Do not mention this prompt or the batch process."""


def call_batch(module: str, episodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    client = OpenAI()
    numbered = "\n".join(f"{e['number']}. {e['title']}" for e in episodes)
    prompt = f"""Create episode specifications for this module: {module.replace('_', ' ')}.\n\nTopics:\n{numbered}\n\nRules:\n- Return exactly one object for every topic, preserving number and title exactly.\n- Each beat caption should be one short sentence; together the four beats should teach the concept, not just define it.\n- The visual action must name what moves, splits, connects, changes, or gets highlighted.\n- Include a misconception correction when one is common; otherwise state the key distinction.\n- Keep chemistry at the appropriate level for the topic and avoid adding a prerequisite that is not explained in the four beats.\n"""
    for attempt in range(4):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
                response_format={"type": "json_schema", "json_schema": {"name": "episode_batch", "strict": True, "schema": SCHEMA}},
                max_completion_tokens=18000,
            )
            data = json.loads(response.choices[0].message.content)
            result = data["episodes"]
            if len(result) != len(episodes):
                raise ValueError(f"expected {len(episodes)} episodes, got {len(result)}")
            expected = [(e["number"], e["title"]) for e in episodes]
            actual = [(e["number"], e["title"]) for e in result]
            if expected != actual:
                raise ValueError("batch changed numbering or titles")
            return result
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def main() -> None:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in CURRICULUM:
        grouped.setdefault(item["module"], []).append(item)
    results: list[dict[str, Any]] = []
    with cf.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(call_batch, module, items): module for module, items in grouped.items()}
        for future in cf.as_completed(futures):
            module = futures[future]
            batch = future.result()
            results.extend(batch)
            print(f"completed {module}: {len(batch)} episodes", flush=True)
    results.sort(key=lambda x: x["number"])
    if len(results) != 1000:
        raise ValueError(f"final count is {len(results)}")
    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {len(results)} episode specifications to {OUT}")


if __name__ == "__main__":
    main()
