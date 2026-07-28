#!/usr/bin/env python3
"""Convert the trusted trained Keras emotion model to a TF.js GraphModel.

The source model was saved by Keras without explicit output shapes on four
Lambda reduction layers. Newer Keras versions require those shapes while
deserializing. This script repairs a temporary copy only, loads the weights,
exports a TensorFlow SavedModel, and converts it for browser inference.

This is a maintainer tool. TensorFlow and tensorflowjs are not runtime
dependencies of the Streamlit application.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import types
import zipfile
from pathlib import Path


def _patched_keras_archive(source: Path, destination: Path) -> None:
    """Copy a Keras archive and add missing Lambda output shapes."""
    with zipfile.ZipFile(source, "r") as archive:
        members = {name: archive.read(name) for name in archive.namelist()}

    config = json.loads(members["config.json"])
    for layer in config["config"]["layers"]:
        if layer.get("class_name") != "Lambda":
            continue

        input_shape = layer.get("build_config", {}).get("input_shape")
        if not input_shape or len(input_shape) != 4:
            raise ValueError(
                f"Cannot infer Lambda output shape for {layer.get('name')!r}"
            )
        layer["config"]["output_shape"] = [
            int(input_shape[1]),
            int(input_shape[2]),
            1,
        ]

    members["config.json"] = json.dumps(config, separators=(",", ":")).encode()
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, data in members.items():
            archive.writestr(name, data)


def convert(source: Path, destination: Path) -> None:
    """Convert ``source`` to a TensorFlow.js GraphModel in ``destination``."""
    import keras
    import tensorflow as tf

    with tempfile.TemporaryDirectory(prefix="hiresense-model-") as temp_dir:
        temp = Path(temp_dir)
        patched_model = temp / "patched.keras"
        saved_model = temp / "saved_model"
        _patched_keras_archive(source, patched_model)

        model = keras.models.load_model(
            patched_model,
            compile=False,
            safe_mode=False,
        )
        for layer in model.layers:
            if isinstance(layer, keras.layers.Lambda):
                layer.function.__globals__["tf"] = tf
        model.export(saved_model)

        if destination.exists():
            shutil.rmtree(destination)
        destination.mkdir(parents=True)

        # tensorflowjs imports TensorFlow Decision Forests only to register its
        # optional custom ops. This model contains no TF-DF layers, and recent
        # TF-DF wheels can require a protobuf runtime that conflicts with
        # TensorFlow itself. A local empty module keeps this conversion focused
        # on the standard TensorFlow ops the model actually uses.
        sys.modules["tensorflow_decision_forests"] = types.ModuleType(
            "tensorflow_decision_forests"
        )
        sys.modules["tensorflow_hub"] = types.ModuleType("tensorflow_hub")
        from tensorflowjs.converters import tf_saved_model_conversion_v2

        tf_saved_model_conversion_v2.convert_tf_saved_model(
            str(saved_model),
            str(destination),
            signature_def="serve",
            saved_model_tags="serve",
            use_structured_outputs_names=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "source",
        nargs="?",
        type=Path,
        default=Path("models/viva_defense_final.keras"),
    )
    parser.add_argument(
        "destination",
        nargs="?",
        type=Path,
        default=Path("static/emotion_model"),
    )
    args = parser.parse_args()
    convert(args.source.resolve(), args.destination.resolve())


if __name__ == "__main__":
    main()
