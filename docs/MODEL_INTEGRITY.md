# Model integrity record

## Finding

The original archive contained two different model artifacts:

- `models/viva_defense_final.keras`, a nontrivial Keras model with trained
  batch-normalization parameters and nonzero learned values.
- A root TensorFlow.js LayersModel whose weights matched initialization
  patterns and whose outputs stayed near 0.5 for very different inputs.

The original webcam path did not use either model reliably. It calculated a
display value from frame brightness and motion, while an unused loader
silently generated synthetic values after load failures.

The unrelated TensorFlow.js model and every synthetic fallback were removed.
The supplied Keras model was exported as the GraphModel used by the browser.

## Packaged hashes

SHA-256:

| Artifact | Hash |
|---|---|
| `models/viva_defense_final.keras` | `5c2800f0613272e0c7b99ef894db8027b7a40a386bea04e212f7c132aa6fe61c` |
| `static/emotion_model/model.json` | `315a8e66eca64375fc8a2aa824a67f3f0ead2267198cf98097ed5ffeb4c3d0aa` |
| `static/emotion_model/group1-shard1of2.bin` | `7ba9967a46263f6f5c2bb92f056813be232c7e79eb9abcd5f1cf40f4b026e2cb` |
| `static/emotion_model/group1-shard2of2.bin` | `21ce9e688c9c69700e8bfd079656a9b62b9a89fea6b1191ac93dc2664d852e20` |

## Structural checks

The packaged GraphModel has:

- Input signature `[-1, 48, 48, 1]`
- Output signature `[-1, 1]`
- 149 graph nodes
- 53 weight specifications
- 5,093,564 bytes of weight data across two complete shards

## Cross-runtime inference check

Known inputs were evaluated in Keras before export and in TensorFlow.js after
export.

| Input | Keras | TensorFlow.js |
|---|---:|---:|
| All black | 0.731987 | 0.731970 |
| All white | 0.517777 | 0.517531 |

The small difference is consistent with conversion/runtime numerical
variation. The browser verification script allows a tolerance of 0.002 and
also requires the two outputs to differ by at least 0.1.

Run:

```bash
cd emotion_detector/frontend
npm install
npm run verify:model
```

## Limitations

The archive contains no training dataset, class-balance record, holdout
evaluation, demographic performance analysis, or calibration evidence.
Therefore:

- The output is labelled an estimated facial stress signal.
- It is not labelled confidence.
- Missing values remain unavailable.
- It has zero weight in the practice grade.
- It must not be used for medical, deception, employment, or hiring decisions.
