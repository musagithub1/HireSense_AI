# Third-Party Notices

HireSense AI is distributed under the MIT License. External packages, browser
runtimes, model runtimes, and third-party assets retain their own copyright
and license terms.

The main third-party projects used directly by this repository include:

- Streamlit and its component library
- LangChain, LangSmith, and the OpenAI-compatible client
- Supabase JavaScript
- TensorFlow.js
- `@vladmandic/face-api` and its Tiny Face Detector assets
- React and React DOM
- Three.js
- Vite
- Expo, React Native, and React Native WebView
- pandas, Pydantic, pypdf, Requests, and python-dotenv

Exact versions are recorded in:

- `requirements.txt`
- `requirements-dev.txt`
- `emotion_detector/frontend/package-lock.json`
- `voice_input/frontend/package-lock.json`
- `persistence/frontend/package-lock.json`
- `mobile/package-lock.json`

The trained Viva Defense model and its TensorFlow.js conversion are included
for the practice feature described in `docs/MODEL_INTEGRITY.md`. The model was
created by the HireSense project author from FER2013-derived expression data.
Its source project is
`https://github.com/musagithub1/Viva-Defense-Face-Sensor`. The trained output
must not be presented as a calibrated probability, medical measurement, lie
detector, biometric identification system, or hiring-decision signal.

Maya's interviewer uses original project portrait frames rendered locally on a
project-authored curved surface through Three.js. No stock avatar, third-party
character mesh, motion file, or public figure likeness is bundled.

The HireSense name and logo identify this project. The MIT License does not
grant trademark rights or imply endorsement of modified deployments.

Before redistributing a modified bundle, review the license metadata and
notices shipped with every dependency you retain.
