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
BATCH_DIR = ROOT / "spec_batches"
BATCH_DIR.mkdir(exist_ok=True)
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

SYSTEM = """You are a careful chemistry educator writing short, self-contained explainer episodes. For every topic, create one hook question, one teaching claim, one misconception correction, one practical takeaway, exactly four concept beats, and one closing answer. The audience is a general learner. Captions are the entire narration, so keep them plain, concrete, and ideally under 40 characters. Each visual action must show chemistry through motion, transformation, connection, comparison, or particle behavior. Use only these idioms: decomposition, space, relationship network, stacking, distribution, particles, molecular model, energy diagram, phase diagram, reaction pathway, or titration curve. Avoid unsafe procedures, unsupported numerical claims, and long equations. Return only the requested JSON."""


def chunks(items: list[dict[str, Any]], n: int) -> list[list[dict[str, Any]]]:
    return [items[i:i+n] for i in range(0, len(items), n)]


def call_batch(batch_id: int, module: str, episodes: list[dict[str, Any]]) -> Path:
    outfile = BATCH_DIR / f"batch_{batch_id:03d}.json"
    if outfile.exists():
        return outfile
    client = OpenAI()
    topic_lines = "\n".join(f"{e['number']}. {e['title']}" for e in episodes)
    prompt = f"""Module: {module.replace('_', ' ')}\n\nTopics:\n{topic_lines}\n\nReturn exactly {len(episodes)} episode objects, preserving each number and title exactly. Make the four beats progressively explanatory: definition, particle or structural cause, visible consequence, and a compact application or distinction."""
    last_error = ""
    for attempt in range(5):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
                response_format={"type": "json_schema", "json_schema": {"name": "episode_batch", "strict": True, "schema": SCHEMA}},
                max_completion_tokens=10000,
            )
            message = response.choices[0].message
            content = message.content
            if not content:
                last_error = f"empty content; finish={response.choices[0].finish_reason}"
                time.sleep(3 * (attempt + 1))
                continue
            data = json.loads(content)
            result = data["episodes"]
            expected = [(e["number"], e["title"]) for e in episodes]
            actual = [(e["number"], e["title"]) for e in result]
            if expected != actual:
                raise ValueError("batch changed numbering or titles")
            outfile.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
            return outfile
        except Exception as exc:
            last_error = repr(exc)
            if attempt == 4:
                break
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"batch {batch_id} failed: {last_error}")


def main() -> None:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in CURRICULUM:
        grouped.setdefault(item["module"], []).append(item)
    jobs: list[tuple[int, str, list[dict[str, Any]]]] = []
    batch_id = 1
    for module, items in grouped.items():
        for part in chunks(items, 20):
            jobs.append((batch_id, module, part))
            batch_id += 1
    with cf.ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(call_batch, bid, module, part): (bid, module) for bid, module, part in jobs}
        for future in cf.as_completed(futures):
            bid, module = futures[future]
            path = future.result()
            print(f"completed batch {bid:03d} ({module}): {path.name}", flush=True)
    all_specs: list[dict[str, Any]] = []
    for bid, _, _ in jobs:
        all_specs.extend(json.loads((BATCH_DIR / f"batch_{bid:03d}.json").read_text()))
    all_specs.sort(key=lambda x: x["number"])
    if len(all_specs) != 1000:
        raise ValueError(f"final count is {len(all_specs)}")
    OUT.write_text(json.dumps(all_specs, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {len(all_specs)} episode specifications to {OUT}")


if __name__ == "__main__":
    main()
