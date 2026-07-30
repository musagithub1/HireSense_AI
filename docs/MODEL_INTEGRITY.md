# Viva Defense model integrity record

## Provenance

The bundled camera model is Mussa Khan's Viva Defense CNN:

- Source repository:
  `https://github.com/musagithub1/Viva-Defense-Face-Sensor`
- Reviewed source commit:
  `f6dfaec3fae94985f66e01963e98d8e4c6db57e2`
- Training source: FER2013-derived 48 by 48 grayscale facial images
- Final mapped dataset described by the project: 29,262 images
- Model input: one 48 by 48 grayscale face crop
- Model output: one sigmoid value toward the stressed-like training class

The training mapping is:

| FER2013 labels | Viva Defense class |
|---|---|
| Happy, Neutral | Confident-like |
| Fear, Anger, Sadness | Stressed-like |
| Surprise, Disgust | Excluded |

## Reported evaluation

The repository's notebook and README report results on a 5,820-image holdout
set:

| Metric | Reported result |
|---|---:|
| Accuracy | About 85.1% |
| ROC AUC | 0.9349 |
| Confident-like recall | About 85.3% |
| Stressed-like recall | About 84.8% |

ROC AUC and accuracy are different metrics. The model must not be described as
having 93.49% accuracy.

## Packaged artifacts

The original HireSense archive contained:

- `models/viva_defense_final.keras`, a nontrivial trained Keras model
- An unrelated root TensorFlow.js LayersModel whose outputs stayed near 0.5
- A webcam path that used brightness and motion instead of the trained model
- A fallback path that could generate synthetic values

The unrelated model, brightness heuristic, and synthetic fallback were
removed. The supplied Keras model was exported as the TensorFlow.js GraphModel
that now runs in the browser.

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

The small difference is consistent with conversion and runtime numerical
variation. The browser verification script allows a tolerance of 0.002 and
also requires the two outputs to differ by at least 0.1.

Run:

```bash
cd emotion_detector/frontend
npm install
npm run verify:model
```

## Runtime safeguards

- Camera use requires explicit candidate opt-in.
- Face detection and CNN inference run inside the browser.
- Frames, images, face crops, and video are never uploaded or saved.
- HireSense records at most one numeric checkpoint when an answer is submitted.
- Missing camera, face, or model data stays unavailable.
- No random, neutral, or simulated value replaces a missing reading.
- Facial output has zero weight in transcript evidence scoring.
- A single reading never changes Maya's tone.
- Repeated stressed-like checkpoints may soften wording only. They do not
  change the planned competency, difficulty, or follow-up decision.

## Limitations

The available project materials do not establish:

- External validity in real interviews or vivas
- Demographic fairness across skin tone, age, gender presentation, disability,
  culture, lighting, camera quality, or pose
- Calibration as a probability of internal confidence or stress
- Construct validity for competence, truthfulness, personality, or hiring
  suitability

Therefore, HireSense labels the classes confident-like and stressed-like
expressions. It does not claim to read a person's internal state and must not
be used for employment decisions, medical assessment, deception detection, or
biometric identification.

## Project acknowledgements

The Viva Defense repository credits Dr. Mumtaz Zahoor and Ayesha Khalid for
guidance and support, and Abdul Haseeb and M saad Arshad for development
discussions and encouragement.
