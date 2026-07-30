# Privacy and Responsible Use

HireSense AI is intended for interview practice and learning. It is not a
validated hiring-decision system, lie detector, medical device, or biometric
assessment product.

## Required principles

- Use candidate answers, role requirements, and verifiable transcript evidence
  for feedback.
- Do not score or rank people by facial appearance, inferred emotion, accent,
  voice characteristics, age, gender, race, disability, or other protected or
  biometric traits.
- Treat the speaking-delivery estimate as private coaching feedback only. Do
  not use it to accept, reject, rank, or screen candidates.
- Treat the optional Viva Defense output as a private expression-coaching
  signal, not a measurement of inner confidence or stress.
- Keep the facial signal out of hiring decisions, question difficulty,
  follow-up selection, competency scores, and answer feedback. Repeated
  stressed-like checkpoints may only make interviewer wording calmer and
  clearer.
- Let candidates review and correct speech-recognition transcripts before
  scoring.
- Explain when a built-in fallback question is used because a model is
  unavailable.
- Show insufficient evidence instead of inventing a score.

## Data minimization

Collect only what the practice session needs. By default:

- Save only submitted and confirmed transcripts.
- Do not save partial microphone transcripts or microphone volume samples.
- Request webcam access only after explicit opt-in.
- Process webcam frames locally in the browser. Do not upload, record, or save
  frames, face crops, photos, or video.
- Save only question-level numeric expression summaries when the candidate
  enabled the feature, and keep them attached to the candidate's private
  practice record.
- Store the original resume PDF only after the user has consented to private
  account storage during sign-in.
- Keep storage private and protected by Row Level Security.
- Give users a way to download or delete their data.
- Define and publish a retention period for public deployments.

## Deployment responsibilities

Anyone deploying a modified version is responsible for:

- Clear consent and a plain-language privacy notice
- Regional privacy, employment, accessibility, and data-protection rules
- Model-provider and speech-service terms
- Secure secret management and access review
- Incident response and credential rotation
- Testing with the languages, browsers, and devices they claim to support
- Human review of any feedback used beyond personal practice

## Multilingual use

Preserve the original question and confirmed transcript. Translation may be
shown as an additional field, but it should not replace the original evidence.
Do not penalize code-switching, accent, or speech-recognition errors.

## Known limitations

- Browser speech recognition varies by browser, device, language, and network.
- Generated questions and evaluations can still be incorrect.
- Resume and job-description extraction can omit context.
- The bundled facial model is not documented as a calibrated measurement and
  has not been externally validated in real interviews or audited for
  demographic fairness. It should remain an optional, non-decision practice
  signal.
- The model's reported ROC AUC of 0.9349 is not 93.49% accuracy. The reported
  test accuracy is about 85.1% on the project's FER2013-derived holdout set.
- Happy and neutral source labels were mapped to confident-like, while fear,
  anger, and sadness were mapped to stressed-like. Those dataset labels do not
  reveal a person's internal emotional state.
- Reliability labels describe evidence coverage, not a candidate's future job
  performance.
- Speaking-delivery estimates can be affected by microphone quality, browser
  transcription, disability, language, and environment. They do not reveal a
  person's internal confidence or emotional state.
