"""Integrity tests for the browser emotion-model export."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import webcam_component

ROOT = Path(__file__).parents[1]
MODEL_DIR = ROOT / "static" / "emotion_model"
SOURCE_MODEL_SHA256 = (
    "5c2800f0613272e0c7b99ef894db8027b7a40a386bea04e212f7c132aa6fe61c"
)


def test_graph_model_manifest_and_signature() -> None:
    manifest = json.loads((MODEL_DIR / "model.json").read_text())

    assert manifest["format"] == "graph-model"
    assert len(manifest["modelTopology"]["node"]) >= 100
    assert len(manifest["weightsManifest"][0]["weights"]) >= 50

    input_signature = manifest["signature"]["inputs"]["input_image"]
    output_signature = manifest["signature"]["outputs"]["output_0"]
    assert input_signature["dtype"] == "DT_FLOAT"
    assert [dim["size"] for dim in input_signature["tensorShape"]["dim"]] == [
        "-1",
        "48",
        "48",
        "1",
    ]
    assert [dim["size"] for dim in output_signature["tensorShape"]["dim"]] == [
        "-1",
        "1",
    ]


def test_weight_shards_are_complete() -> None:
    manifest = json.loads((MODEL_DIR / "model.json").read_text())
    group = manifest["weightsManifest"][0]
    dtype_bytes = {"float32": 4, "int32": 4, "bool": 1}
    expected_bytes = sum(
        math.prod(spec["shape"]) * dtype_bytes[spec["dtype"]]
        for spec in group["weights"]
    )
    shards = [MODEL_DIR / name for name in group["paths"]]

    assert all(path.is_file() for path in shards)
    assert sum(path.stat().st_size for path in shards) == expected_bytes


def test_source_model_and_browser_assets_are_packaged() -> None:
    source_model = ROOT / "models" / "viva_defense_final.keras"
    assert source_model.stat().st_size > 1_000_000
    assert hashlib.sha256(source_model.read_bytes()).hexdigest() == (
        SOURCE_MODEL_SHA256
    )
    assert (
        ROOT / "static" / "face_models" / "tiny_face_detector_model.bin"
    ).stat().st_size > 100_000


def test_viva_defense_metrics_are_named_accurately() -> None:
    assert webcam_component.MODEL_NAME == "Viva Defense CNN"
    assert webcam_component.MODEL_TEST_ACCURACY == 0.851
    assert webcam_component.MODEL_ROC_AUC == 0.9349
    assert webcam_component.MODEL_TEST_ACCURACY != (
        webcam_component.MODEL_ROC_AUC
    )
