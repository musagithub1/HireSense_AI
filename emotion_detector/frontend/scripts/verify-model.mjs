import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import * as tf from "@tensorflow/tfjs";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const modelDir = path.resolve(scriptDir, "../../../static/emotion_model");
const manifest = JSON.parse(
  await fs.readFile(path.join(modelDir, "model.json"), "utf8"),
);
const group = manifest.weightsManifest[0];
const shards = await Promise.all(
  group.paths.map((name) => fs.readFile(path.join(modelDir, name))),
);
const combined = Buffer.concat(shards);
const weightData = combined.buffer.slice(
  combined.byteOffset,
  combined.byteOffset + combined.byteLength,
);

const model = await tf.loadGraphModel({
  load: async () => ({
    modelTopology: manifest.modelTopology,
    weightSpecs: group.weights,
    weightData,
    format: manifest.format,
    generatedBy: manifest.generatedBy,
    convertedBy: manifest.convertedBy,
    signature: manifest.signature,
    userDefinedMetadata: manifest.userDefinedMetadata,
  }),
});

async function score(input) {
  const output = model.predict(input);
  const tensor =
    output && typeof output.data === "function"
      ? output
      : Array.isArray(output)
        ? output[0]
        : Object.values(output)[0];
  const value = (await tensor.data())[0];
  input.dispose();
  if (Array.isArray(output)) output.forEach((item) => item.dispose());
  else if (output && typeof output.dispose === "function") output.dispose();
  else Object.values(output).forEach((item) => item.dispose());
  return value;
}

const black = await score(tf.zeros([1, 48, 48, 1]));
const white = await score(tf.ones([1, 48, 48, 1]));

if (Math.abs(black - 0.73197) > 0.002) {
  throw new Error(`Unexpected black-frame output: ${black}`);
}
if (Math.abs(white - 0.51753) > 0.002) {
  throw new Error(`Unexpected white-frame output: ${white}`);
}
if (Math.abs(black - white) < 0.1) {
  throw new Error("Model outputs do not respond sufficiently to different inputs.");
}

console.log(
  `Verified trained GraphModel: black=${black.toFixed(6)}, white=${white.toFixed(6)}`,
);
model.dispose();
