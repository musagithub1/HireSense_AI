import React from "react";
import { createRoot } from "react-dom/client";
import { Streamlit } from "streamlit-component-lib";

import InterviewAvatar from "./InterviewAvatar.tsx";
import "./style.css";

const app = document.querySelector("#app");
const title = document.querySelector("#title");
const statePill = document.querySelector("#state-pill");
const languageLabel = document.querySelector("#language-label");
const micButton = document.querySelector("#mic");
const pauseButton = document.querySelector("#pause");
const status = document.querySelector("#status");
const transcript = document.querySelector("#transcript");
const interimTranscript = document.querySelector("#interim-transcript");
const clearButton = document.querySelector("#clear");
const submitButton = document.querySelector("#submit");
const endButton = document.querySelector("#end");
const interviewStage = document.querySelector("#interview-stage");
const interviewAvatar = document.querySelector("#interview-avatar");
const questionWrap = document.querySelector("#question-wrap");
const questionLabel = document.querySelector("#question-label");
const question = document.querySelector("#question");
const audioFallback = document.querySelector("#audio-fallback");
const audioFallbackMessage = document.querySelector("#audio-fallback-message");
const playQuestionButton = document.querySelector("#play-question");
const rephraseButton = document.querySelector("#rephrase-question");
const progressWrap = document.querySelector("#progress-wrap");
const progressLabel = document.querySelector("#progress-label");
const progressTrack = document.querySelector(".progress-track");
const progressFill = document.querySelector("#progress-fill");
const answerControls = document.querySelector("#answer-controls");
const speakerStatus = document.querySelector("#speaker-status");
const speedSelect = document.querySelector("#speech-speed");
const responseTimeSelect = document.querySelector("#response-time");
const captionsButton = document.querySelector("#captions");

const SpeechRecognition =
  window.SpeechRecognition || window.webkitSpeechRecognition;
const fillerTerms = ["um", "uh", "like", "you know", "basically", "actually"];
const STATE_LABELS = {
  ready: "Ready",
  listening: "Listening",
  processing: "Processing",
  speaking: "Speaking",
  paused: "Paused",
  error: "Audio unavailable",
  offline: "Connection lost",
};

let args = {
  mode: "standard",
  language_code: "en-US",
  language_label: "English",
  question_text: "",
  question_label: "Interview question",
  question_num: 1,
  total_questions: 1,
  question_revision: 0,
  tts_speed: 1,
  tts_enabled: false,
  interviewer_name: "Maya",
  allow_interrupt: true,
  support_mode: false,
};
let recognition = null;
let listening = false;
let submitted = false;
let speaking = false;
let stopRequested = false;
let audioActivated = false;
let paused = false;
let connectionLost = !navigator.onLine;
let captionsEnabled = true;
let finalText = "";
let interimText = "";
let silenceTimer = null;
let responseMode = "adaptive";
let autoSubmitDelay = 0;
let activeQuestionKey = "";
let speechRunId = 0;
let mediaStream = null;
let audioContext = null;
let audioSource = null;
let analyser = null;
let audioSamples = null;
let audioInputPromise = null;
let vadFrame = null;
let vadActive = false;
let vadReady = false;
let noiseFloor = 0.008;
let consecutiveVoiceFrames = 0;
let speechDetected = false;
let listeningStartedAt = 0;
let firstSpeechAt = 0;
let lastVoiceActivityAt = 0;
let lastTranscriptEventAt = 0;
let silenceStartedAt = 0;
let pauseCount = 0;
let pauseTotalMs = 0;
let recognitionConfidenceTotal = 0;
let recognitionConfidenceWeight = 0;
let questionActivatedAt = 0;
let autoSubmitted = false;
let interviewState = connectionLost ? "offline" : "ready";
let activeSpeech = null;

const ADAPTIVE_SILENCE_MS = 1900;
const TRANSCRIPT_SETTLE_MS = 220;
const MIN_SPEECH_MS = 550;
const MIN_COUNTED_PAUSE_MS = 350;
const avatarRoot = createRoot(interviewAvatar);

function resize() {
  window.requestAnimationFrame(() => Streamlit.setFrameHeight(app.scrollHeight + 4));
}

function renderAvatar() {
  avatarRoot.render(
    React.createElement(InterviewAvatar, {
      interviewState,
      interviewerName: args.interviewer_name || "Maya",
      allowInterrupt: Boolean(args.allow_interrupt),
      supportMode: Boolean(args.support_mode),
      spokenText: args.question_text || "",
      onInterrupt: interruptInterviewer,
    }),
  );
  resize();
}

function showState(state, message = "", kind = "") {
  const resolvedState = STATE_LABELS[state] ? state : "ready";
  interviewState = resolvedState;
  statePill.textContent = STATE_LABELS[resolvedState];
  statePill.dataset.state = resolvedState;

  const target = args.mode === "speaker" ? speakerStatus : status;
  target.textContent = message;
  target.className =
    args.mode === "speaker"
      ? `speaker-status${kind ? ` ${kind}` : ""}`
      : kind;
  renderAvatar();
  resize();
}

function showAudioFallback(reason = "") {
  const message = reason
    ? `${reason} Read the written question below and continue normally.`
    : "Read the written question below and continue normally.";
  audioFallbackMessage.textContent = message;
  audioFallback.classList.remove("hidden");
  questionWrap.classList.add("audio-fallback-active");
  setCaptions(true);
  window.requestAnimationFrame(() => question.focus({ preventScroll: true }));
  resize();
}

function hideAudioFallback() {
  audioFallback.classList.add("hidden");
  questionWrap.classList.remove("audio-fallback-active");
}

function audioStreamIsLive() {
  return Boolean(
    mediaStream &&
      mediaStream.getAudioTracks().some((track) => track.readyState === "live"),
  );
}

function setAudioTracksEnabled(enabled) {
  if (!mediaStream) return;
  for (const track of mediaStream.getAudioTracks()) {
    track.enabled = Boolean(enabled);
  }
}

async function prepareAudioInput() {
  if (audioStreamIsLive() && analyser && audioContext) {
    if (audioContext.state === "suspended") {
      try {
        await audioContext.resume();
      } catch {
        // Speech recognition remains available if Web Audio cannot resume.
      }
    }
    vadReady = true;
    return true;
  }
  if (!navigator.mediaDevices?.getUserMedia) return false;
  if (audioInputPromise) return audioInputPromise;

  audioInputPromise = (async () => {
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
        },
        video: false,
      });
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (!AudioContextClass) return false;
      audioContext = new AudioContextClass();
      audioSource = audioContext.createMediaStreamSource(mediaStream);
      analyser = audioContext.createAnalyser();
      analyser.fftSize = 1024;
      analyser.smoothingTimeConstant = 0.25;
      audioSamples = new Float32Array(analyser.fftSize);
      audioSource.connect(analyser);
      setAudioTracksEnabled(false);
      vadReady = true;
      return true;
    } catch {
      vadReady = false;
      return false;
    } finally {
      audioInputPromise = null;
    }
  })();
  return audioInputPromise;
}

function stopVadMonitoring() {
  vadActive = false;
  setAudioTracksEnabled(false);
  interviewAvatar.style.setProperty("--voice-level", "0");
  interviewAvatar.style.setProperty("--voice-ring-opacity", "0.35");
  interviewAvatar.style.setProperty("--voice-ring-scale", "1");
  if (vadFrame !== null) {
    window.cancelAnimationFrame(vadFrame);
    vadFrame = null;
  }
}

function closeAudioInput() {
  stopVadMonitoring();
  if (mediaStream) {
    for (const track of mediaStream.getTracks()) track.stop();
  }
  if (audioContext && audioContext.state !== "closed") {
    audioContext.close().catch(() => {});
  }
  mediaStream = null;
  audioContext = null;
  audioSource = null;
  analyser = null;
  audioSamples = null;
  vadReady = false;
}

function adaptiveSubmissionReady(now) {
  return Boolean(
    responseMode === "adaptive" &&
      vadReady &&
      speechDetected &&
      finalText.trim() &&
      !interimText.trim() &&
      !submitted &&
      !paused &&
      now - listeningStartedAt >= MIN_SPEECH_MS &&
      now - lastVoiceActivityAt >= ADAPTIVE_SILENCE_MS &&
      now - lastTranscriptEventAt >= TRANSCRIPT_SETTLE_MS,
  );
}

function monitorVoiceActivity() {
  if (!vadActive || !analyser || !audioSamples) {
    vadFrame = null;
    return;
  }

  analyser.getFloatTimeDomainData(audioSamples);
  let energy = 0;
  for (let index = 0; index < audioSamples.length; index += 1) {
    energy += audioSamples[index] * audioSamples[index];
  }
  const rms = Math.sqrt(energy / audioSamples.length);
  const threshold = Math.max(0.018, Math.min(0.12, noiseFloor * 3.2));
  const voiceFrame = rms >= threshold;
  const now = performance.now();
  const visualLevel = Math.max(
    0,
    Math.min(1, (rms - noiseFloor) / Math.max(0.025, threshold * 2.4)),
  );
  interviewAvatar.style.setProperty("--voice-level", visualLevel.toFixed(3));
  interviewAvatar.style.setProperty(
    "--voice-ring-opacity",
    (0.35 + visualLevel * 0.5).toFixed(3),
  );
  interviewAvatar.style.setProperty(
    "--voice-ring-scale",
    (1 + visualLevel * 0.12).toFixed(3),
  );

  if (voiceFrame) {
    consecutiveVoiceFrames += 1;
    if (consecutiveVoiceFrames >= 3) {
      if (!firstSpeechAt) firstSpeechAt = now;
      if (silenceStartedAt) {
        const pauseDuration = now - silenceStartedAt;
        if (pauseDuration >= MIN_COUNTED_PAUSE_MS) {
          pauseCount += 1;
          pauseTotalMs += pauseDuration;
        }
        silenceStartedAt = 0;
      }
      speechDetected = true;
      lastVoiceActivityAt = now;
    }
  } else {
    consecutiveVoiceFrames = 0;
    if (
      speechDetected &&
      !silenceStartedAt &&
      now - lastVoiceActivityAt >= MIN_COUNTED_PAUSE_MS
    ) {
      silenceStartedAt = lastVoiceActivityAt;
    }
    if (!speechDetected || now - lastVoiceActivityAt > 1400) {
      noiseFloor = Math.max(
        0.003,
        Math.min(0.035, noiseFloor * 0.96 + rms * 0.04),
      );
    }
  }

  if (adaptiveSubmissionReady(now)) {
    autoSubmitted = true;
    sendAction("answer");
    return;
  }
  vadFrame = window.requestAnimationFrame(monitorVoiceActivity);
}

function startVadMonitoring({ reset = false } = {}) {
  if (!vadReady || !analyser || submitted || paused) return;
  stopVadMonitoring();
  setAudioTracksEnabled(true);
  vadActive = true;
  if (reset || !listeningStartedAt) {
    speechDetected = false;
    consecutiveVoiceFrames = 0;
    listeningStartedAt = performance.now();
    firstSpeechAt = 0;
    lastVoiceActivityAt = listeningStartedAt;
    lastTranscriptEventAt = listeningStartedAt;
    silenceStartedAt = 0;
    pauseCount = 0;
    pauseTotalMs = 0;
    recognitionConfidenceTotal = 0;
    recognitionConfidenceWeight = 0;
    autoSubmitted = false;
  }
  vadFrame = window.requestAnimationFrame(monitorVoiceActivity);
}

function renderTranscript() {
  if (transcript.value !== finalText) {
    const active = document.activeElement === transcript;
    const selectionStart = transcript.selectionStart;
    const selectionEnd = transcript.selectionEnd;
    transcript.value = finalText;
    if (active) {
      const nextStart = Math.min(selectionStart, transcript.value.length);
      const nextEnd = Math.min(selectionEnd, transcript.value.length);
      transcript.setSelectionRange(nextStart, nextEnd);
    }
  }
  interimTranscript.textContent = interimText
    ? `Listening: ${interimText}`
    : finalText
      ? "You can correct the transcript before submitting."
      : "Your words will appear here while you speak.";
  interimTranscript.classList.toggle("active", Boolean(interimText));
  submitButton.disabled = !finalText.trim() || submitted;
  transcript.disabled = submitted;
  resize();
}

function stopRecognition() {
  window.clearTimeout(silenceTimer);
  silenceTimer = null;
  stopVadMonitoring();
  stopRequested = true;
  if (recognition) {
    try {
      recognition.stop();
    } catch {
      // Stopping an already-ended recognition session is safe.
    }
  }
}

function speechStats(text) {
  const words = text.trim().split(/\s+/).filter(Boolean);
  const lower = text.toLowerCase();
  let hesitations = 0;
  for (const term of fillerTerms) {
    const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    hesitations += (lower.match(new RegExp(`\\b${escaped}\\b`, "g")) || []).length;
  }
  const recognitionConfidence =
    recognitionConfidenceWeight > 0
      ? recognitionConfidenceTotal / recognitionConfidenceWeight
      : null;
  const metric = (value) =>
    Number.isFinite(value) && value >= 0 ? Math.round(value) : null;
  return {
    word_count: words.length,
    hesitations,
    recognition_confidence:
      recognitionConfidence === null
        ? null
        : Math.round(recognitionConfidence * 1000) / 1000,
    response_start_ms: metric(
      firstSpeechAt && listeningStartedAt
        ? firstSpeechAt - listeningStartedAt
        : null,
    ),
    speaking_duration_ms: metric(
      firstSpeechAt && lastVoiceActivityAt
        ? lastVoiceActivityAt - firstSpeechAt
        : null,
    ),
    pause_count: pauseCount,
    pause_ms: metric(pauseTotalMs),
    manual_submit: !autoSubmitted,
  };
}

function latencyStats(now = performance.now()) {
  const metric = (value) =>
    Number.isFinite(value) && value >= 0 ? Math.round(value) : null;
  return {
    capture_ms: metric(listeningStartedAt ? now - listeningStartedAt : null),
    end_of_speech_ms: metric(
      lastVoiceActivityAt ? now - lastVoiceActivityAt : null,
    ),
    transcript_finalize_ms: metric(
      lastVoiceActivityAt && lastTranscriptEventAt
        ? lastTranscriptEventAt - lastVoiceActivityAt
        : null,
    ),
    question_to_listen_ms: metric(
      questionActivatedAt && listeningStartedAt
        ? listeningStartedAt - questionActivatedAt
        : null,
    ),
    response_mode:
      responseMode === "adaptive"
        ? "adaptive"
        : autoSubmitDelay > 0
          ? "fixed"
          : "manual",
    adaptive_vad: responseMode === "adaptive" && vadReady,
    auto_submitted: autoSubmitted,
  };
}

function sendAction(action = "answer") {
  const answer = finalText.trim();
  if (action === "answer" && !answer) return;
  submitted = true;
  stopRecognition();
  micButton.classList.remove("listening");
  micButton.textContent =
    action === "answer" ? "✓" : action === "end" ? "⏹" : "…";
  showState(
    "processing",
    action === "answer"
      ? "HireSense is processing your answer."
      : action === "rephrase"
        ? "HireSense is rephrasing the question."
        : "Ending interview.",
    "active",
  );
  const stats = speechStats(answer);
  Streamlit.setComponentValue({
    action,
    answer: action === "answer" ? answer : "",
    submission_id: `${Date.now()}-${crypto.getRandomValues(new Uint32Array(1))[0]}`,
    latency: latencyStats(),
    ...stats,
  });
  if (action === "end") closeAudioInput();
}

function startSilenceTimer() {
  window.clearTimeout(silenceTimer);
  if (
    args.mode !== "live" ||
    !finalText.trim() ||
    submitted ||
    paused ||
    (responseMode !== "adaptive" && autoSubmitDelay <= 0)
  ) {
    return;
  }

  if (responseMode === "adaptive") {
    if (vadReady) {
      showState(
        "listening",
        "Listening. HireSense will continue when you finish speaking.",
        "active",
      );
      silenceTimer = window.setTimeout(() => {
        if (!submitted && finalText.trim() && !interimText.trim()) {
          autoSubmitted = true;
          sendAction("answer");
        }
      }, 2200);
      return;
    }
    autoSubmitDelay = 1600;
  }
  showState(
    "listening",
    `Listening. I will submit after ${autoSubmitDelay / 1000} seconds of silence.`,
    "active",
  );
  silenceTimer = window.setTimeout(() => sendAction("answer"), autoSubmitDelay);
}

function makeRecognition() {
  if (!SpeechRecognition) return null;
  const instance = new SpeechRecognition();
  instance.continuous = args.mode === "live";
  instance.interimResults = true;
  instance.maxAlternatives = 1;
  instance.lang = args.language_code;

  instance.onstart = () => {
    stopRequested = false;
    listening = true;
    if (!listeningStartedAt) {
      listeningStartedAt = performance.now();
      lastVoiceActivityAt = listeningStartedAt;
      lastTranscriptEventAt = listeningStartedAt;
    }
    micButton.classList.add("listening");
    micButton.textContent = "⏹";
    micButton.setAttribute("aria-label", "Stop listening");
    showState("listening", "Listening. Speak naturally.", "active");
    startVadMonitoring();
  };
  instance.onresult = (event) => {
    lastTranscriptEventAt = performance.now();
    interimText = "";
    let receivedFinal = false;
    for (let index = event.resultIndex; index < event.results.length; index += 1) {
      const result = event.results[index];
      if (result.isFinal) {
        const segment = result[0].transcript;
        finalText = `${finalText} ${segment}`.trim();
        const confidence = Number(result[0].confidence);
        const segmentWeight = Math.max(
          1,
          segment.trim().split(/\s+/).filter(Boolean).length,
        );
        if (Number.isFinite(confidence) && confidence > 0 && confidence <= 1) {
          recognitionConfidenceTotal += confidence * segmentWeight;
          recognitionConfidenceWeight += segmentWeight;
        }
        receivedFinal = true;
      } else {
        interimText += result[0].transcript;
        window.clearTimeout(silenceTimer);
        if (!vadReady) lastVoiceActivityAt = performance.now();
      }
    }
    renderTranscript();
    if (receivedFinal && !interimText.trim()) startSilenceTimer();
  };
  instance.onerror = (event) => {
    listening = false;
    micButton.classList.remove("listening");
    micButton.textContent = "🎙";
    micButton.setAttribute("aria-label", "Start listening");
    if (event.error === "network") {
      paused = true;
      pauseButton.textContent = "Resume";
      showState(
        connectionLost ? "offline" : "error",
        "The browser speech service could not be reached. Resume to try again.",
        "error",
      );
      return;
    }
    if (!["aborted", "no-speech"].includes(event.error)) {
      const messages = {
        "not-allowed": "Microphone permission was denied.",
        "audio-capture": "No working microphone was found.",
      };
      paused = true;
      pauseButton.textContent = "Resume";
      showState(
        "error",
        messages[event.error] || `Speech recognition error: ${event.error}`,
        "error",
      );
    }
  };
  instance.onend = () => {
    const shouldRestart =
      !stopRequested &&
      !submitted &&
      !speaking &&
      !paused &&
      !connectionLost &&
      audioActivated &&
      args.mode === "live";
    stopRequested = false;
    listening = false;
    recognition = null;
    micButton.classList.remove("listening");
    micButton.textContent = "🎙";
    micButton.setAttribute("aria-label", "Start listening");
    if (shouldRestart) {
      window.setTimeout(startRecognition, 250);
    } else if (!submitted && !paused && !connectionLost) {
      showState(
        "ready",
        finalText
          ? "Review or correct the transcript, then submit it."
          : "Select the microphone to try again.",
      );
    }
  };
  return instance;
}

async function startRecognition() {
  if (submitted || speaking || args.mode === "speaker") return;
  if (connectionLost) {
    showState("offline", "Reconnect to continue.", "error");
    return;
  }
  if (!SpeechRecognition) {
    paused = false;
    showState(
      "error",
      "Live speech recognition is not supported here. Type your answer in the transcript box.",
      "error",
    );
    micButton.disabled = true;
    return;
  }
  await prepareAudioInput();
  if (submitted || speaking || paused || connectionLost) return;
  if (listening) {
    stopRecognition();
    return;
  }
  paused = false;
  pauseButton.textContent = "Pause";
  recognition = makeRecognition();
  try {
    recognition.start();
  } catch {
    paused = true;
    showState(
      "error",
      "The microphone could not be started. Resume to try again.",
      "error",
    );
  }
}

function resetTranscript() {
  submitted = false;
  finalText = "";
  interimText = "";
  speechDetected = false;
  consecutiveVoiceFrames = 0;
  listeningStartedAt = 0;
  firstSpeechAt = 0;
  lastVoiceActivityAt = 0;
  lastTranscriptEventAt = 0;
  silenceStartedAt = 0;
  pauseCount = 0;
  pauseTotalMs = 0;
  recognitionConfidenceTotal = 0;
  recognitionConfidenceWeight = 0;
  autoSubmitted = false;
  stopRecognition();
  micButton.disabled = false;
  micButton.textContent = "🎙";
  micButton.setAttribute("aria-label", "Start listening");
  submitButton.textContent =
    args.mode === "live" ? "I'm done" : "Use this answer";
  renderTranscript();
  if (connectionLost) {
    showState("offline", "Reconnect to continue.", "error");
  } else if (paused) {
    showState("paused", "Interview paused. Select Resume when you are ready.");
  } else {
    showState("ready", "Select the microphone to start speaking.");
  }
}

function cancelSpeech(code = "cancelled", reason = "") {
  const currentSpeech = activeSpeech;
  if (currentSpeech) {
    currentSpeech.finish({
      ok: false,
      code,
      reason,
      interrupted: code === "interrupted",
    });
  }
  speaking = false;
  emitMayaViseme("rest", 0);
  playQuestionButton.disabled = false;
  if (window.speechSynthesis) window.speechSynthesis.cancel();
}

function emitMayaViseme(viseme = "rest", intensity = 1) {
  window.dispatchEvent(
    new CustomEvent("hiresense:maya-viseme", {
      detail: {
        viseme,
        intensity: Math.max(0, Math.min(1, Number(intensity) || 0)),
      },
    }),
  );
}

function visemeAtBoundary(text, charIndex) {
  const segment = String(text || "")
    .slice(Math.max(0, Number(charIndex) || 0), (Number(charIndex) || 0) + 18)
    .toLocaleLowerCase(args.language_code || "en-US");
  const vowel = segment.match(/[aeiou]/)?.[0] || "";
  const map = { a: "A", e: "E", i: "I", o: "O", u: "U" };
  return map[vowel] || "A";
}

function handleSpeechStart(runId) {
  if (!activeSpeech || activeSpeech.runId !== runId) return;
  activeSpeech.started = true;
  speaking = true;
  emitMayaViseme("A", 0.52);
  hideAudioFallback();
  showState(
    "speaking",
    `${args.interviewer_name || "Maya"} is asking the question.`,
    "active",
  );
}

function handleSpeechEnd(runId) {
  if (!activeSpeech || activeSpeech.runId !== runId) return;
  emitMayaViseme("rest", 0);
  activeSpeech.finish({ ok: true, code: "ended", reason: "" });
}

function handleSpeechPause(runId) {
  if (!activeSpeech || activeSpeech.runId !== runId) return;
  emitMayaViseme("rest", 0);
  showState("paused", "Interviewer paused. Select Resume to continue.");
}

function handleSpeechResume(runId) {
  if (!activeSpeech || activeSpeech.runId !== runId) return;
  emitMayaViseme("A", 0.45);
  showState(
    "speaking",
    `${args.interviewer_name || "Maya"} is continuing the question.`,
    "active",
  );
}

function handleSpeechError(runId, event) {
  if (!activeSpeech || activeSpeech.runId !== runId) return;
  emitMayaViseme("rest", 0);
  const errorCode = String(event?.error || "playback_error");
  activeSpeech.finish({
    ok: false,
    code: "audio_error",
    reason:
      errorCode === "playback_error"
        ? "Speech playback failed."
        : `Speech playback failed: ${errorCode}.`,
  });
}

function handleSpeechBoundary(runId, event) {
  if (!activeSpeech || activeSpeech.runId !== runId) return;
  emitMayaViseme(
    visemeAtBoundary(args.question_text, event?.charIndex),
    event?.name === "sentence" ? 0.48 : 0.9,
  );
}

function speakQuestion() {
  const runId = ++speechRunId;
  return new Promise((resolve) => {
    if (!window.speechSynthesis || !window.SpeechSynthesisUtterance) {
      resolve({
        ok: false,
        code: "unsupported",
        reason: "Speech playback is unavailable in this browser.",
      });
      return;
    }
    if (!args.question_text) {
      resolve({
        ok: false,
        code: "missing_question",
        reason: "No spoken question is available.",
      });
      return;
    }

    let settled = false;
    let startTimer = null;
    let finishTimer = null;

    const finish = (result) => {
      if (settled) return;
      settled = true;
      speaking = false;
      emitMayaViseme("rest", 0);
      playQuestionButton.disabled = false;
      window.clearTimeout(startTimer);
      window.clearTimeout(finishTimer);
      if (activeSpeech?.runId === runId) activeSpeech = null;
      resolve(result);
    };

    activeSpeech = {
      runId,
      started: false,
      finish,
    };
    speaking = true;
    playQuestionButton.disabled = true;
    stopRecognition();
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(args.question_text);
    utterance.lang = args.language_code;
    utterance.rate = args.tts_speed;
    utterance.onstart = () => handleSpeechStart(runId);
    utterance.onend = () => handleSpeechEnd(runId);
    utterance.onpause = () => handleSpeechPause(runId);
    utterance.onresume = () => handleSpeechResume(runId);
    utterance.onerror = (event) => handleSpeechError(runId, event);
    utterance.onboundary = (event) => handleSpeechBoundary(runId, event);

    try {
      window.speechSynthesis.speak(utterance);
    } catch {
      finish({
        ok: false,
        code: "audio_error",
        reason: "Speech playback could not be started.",
      });
      return;
    }

    startTimer = window.setTimeout(() => {
      if (activeSpeech?.runId === runId && !activeSpeech.started) {
        finish({
          ok: false,
          code: "autoplay_blocked",
          reason: "Your browser blocked automatic audio.",
        });
        window.speechSynthesis.cancel();
      }
    }, 2500);

    const estimatedDuration = Math.min(
      120000,
      Math.max(15000, args.question_text.length * 95),
    );
    finishTimer = window.setTimeout(() => {
      finish({
        ok: false,
        code: "timeout",
        reason: "Speech playback timed out.",
      });
      window.speechSynthesis.cancel();
    }, estimatedDuration);
  });
}

function interruptInterviewer() {
  if (!speaking || !args.allow_interrupt) return;
  cancelSpeech(
    "interrupted",
    "The interviewer was interrupted so you can answer.",
  );
  showState(
    "ready",
    "Interviewer stopped. Starting your microphone.",
    "success",
  );
}

async function playQuestion({ startMicrophone = false } = {}) {
  if (connectionLost) {
    showState("offline", "Reconnect to continue.", "error");
    return;
  }
  paused = false;
  pauseButton.textContent = "Pause";
  audioActivated = true;
  updateLiveControlVisibility();
  hideAudioFallback();
  playQuestionButton.textContent =
    args.mode === "live" ? "Hear question again" : "Hear question";
  if (window.speechSynthesis) window.speechSynthesis.getVoices();
  const microphoneReady = startMicrophone
    ? prepareAudioInput()
    : Promise.resolve(false);
  showState("speaking", "Preparing the question.");
  const result = await speakQuestion();

  if (!result.ok) {
    if (
      ["paused", "question_changed", "offline", "unload", "cancelled"].includes(
        result.code,
      )
    ) {
      return;
    }
    if (result.interrupted) {
      if (startMicrophone && !submitted) {
        await microphoneReady;
        if (!connectionLost && !paused) startRecognition();
      }
      return;
    }

    paused = false;
    pauseButton.textContent = "Pause";
    showAudioFallback(result.reason);
    showState(
      "error",
      "Audio is unavailable. Read the question on screen and answer normally.",
      "error",
    );
    if (startMicrophone && !submitted) {
      await microphoneReady;
      if (!connectionLost) startRecognition();
    }
    return;
  }

  if (startMicrophone && !submitted) {
    await microphoneReady;
    showState("ready", "Question complete. Starting your microphone.", "success");
    startRecognition();
  } else {
    showState("ready", "Question played. You can replay it at any time.", "success");
  }
}

async function beginLiveQuestion() {
  resetTranscript();
  await playQuestion({ startMicrophone: true });
}

function pauseInterview() {
  if (connectionLost) return;
  if (!paused) {
    paused = true;
    stopRecognition();
    pauseButton.textContent = "Resume";
    if (speaking && activeSpeech && window.speechSynthesis) {
      window.speechSynthesis.pause();
      handleSpeechPause(activeSpeech.runId);
    } else {
      showState("paused", "Interview paused. Your transcript is preserved.");
    }
    return;
  }

  paused = false;
  pauseButton.textContent = "Pause";
  if (activeSpeech && window.speechSynthesis?.paused) {
    window.speechSynthesis.resume();
    handleSpeechResume(activeSpeech.runId);
  } else if (args.mode === "live" && audioActivated && !submitted) {
    startRecognition();
  } else {
    showState("ready", "Ready to continue.");
  }
}

function setCaptions(enabled) {
  captionsEnabled = enabled;
  question.classList.toggle("caption-hidden", !captionsEnabled);
  captionsButton.textContent = captionsEnabled ? "Captions on" : "Captions off";
  captionsButton.setAttribute("aria-pressed", String(captionsEnabled));
  resize();
}

function updateLiveControlVisibility() {
  const live = args.mode === "live";
  const speakerOnly = args.mode === "speaker";
  app.dataset.audioActive = String(audioActivated);
  pauseButton.classList.toggle(
    "hidden",
    speakerOnly || (live && !audioActivated),
  );
  endButton.classList.toggle("hidden", !live || !audioActivated);
  submitButton.classList.toggle("hidden", live && !audioActivated);
}

function applyArgs(nextArgs) {
  args = { ...args, ...nextArgs };
  const live = args.mode === "live";
  const speakerOnly = args.mode === "speaker";
  const hasQuestion = Boolean(args.question_text);
  const canSpeakQuestion = hasQuestion && Boolean(args.tts_enabled);

  app.dataset.mode = args.mode;
  title.textContent = live ? "Live answer" : "Voice answer";
  languageLabel.textContent = args.language_label || args.language_code;
  answerControls.classList.toggle("hidden", speakerOnly);
  speakerStatus.classList.toggle("hidden", !speakerOnly);
  interviewStage.classList.toggle(
    "hidden",
    !hasQuestion || (!live && !speakerOnly && !args.tts_enabled),
  );
  playQuestionButton.classList.toggle("hidden", !canSpeakQuestion);
  rephraseButton.classList.toggle("hidden", !hasQuestion || speakerOnly);
  progressWrap.classList.add("hidden");
  updateLiveControlVisibility();
  submitButton.textContent = live ? "I'm done" : "Use this answer";
  question.textContent = args.question_text;
  questionLabel.textContent = args.question_label || "Interview question";
  progressLabel.textContent = `Question ${args.question_num} of ${args.total_questions}`;
  const progressPercent = Math.min(
    100,
    (args.question_num / Math.max(1, args.total_questions)) * 100,
  );
  progressFill.style.width = `${progressPercent}%`;
  progressTrack.setAttribute("aria-valuenow", String(Math.round(progressPercent)));
  const requestedSpeed = String(args.tts_speed);
  speedSelect.value = [...speedSelect.options].some(
    (option) => option.value === requestedSpeed,
  )
    ? requestedSpeed
    : "1";

  const questionKey = `${args.question_revision}:${args.question_num}:${args.question_text}`;
  if (questionKey !== activeQuestionKey) {
    questionActivatedAt = performance.now();
    cancelSpeech("question_changed", "A new question is ready.");
    stopRecognition();
    hideAudioFallback();
    paused = false;
    pauseButton.textContent = "Pause";
    activeQuestionKey = questionKey;
    resetTranscript();
    playQuestionButton.textContent =
      live && !audioActivated ? "Start interview" : "Hear question";

    if (live) {
      if (audioActivated) {
        window.setTimeout(beginLiveQuestion, 0);
      } else {
        showState(
          "ready",
          "Select Start interview to hear the question and enable your microphone.",
        );
      }
    } else if (canSpeakQuestion && audioActivated) {
      window.setTimeout(() => playQuestion(), 0);
    } else if (speakerOnly) {
      showState("ready", "Select Hear question to play it aloud.");
    } else {
      showState(
        "ready",
        canSpeakQuestion
          ? "Question ready. Hear it aloud or use the microphone."
          : "Select the microphone to start speaking.",
      );
    }
  }
  setCaptions(captionsEnabled);
  renderAvatar();
  resize();
}

micButton.addEventListener("click", () => {
  if (args.mode === "live" && !audioActivated) {
    beginLiveQuestion();
  } else {
    startRecognition();
  }
});
pauseButton.addEventListener("click", pauseInterview);
playQuestionButton.addEventListener("click", () => {
  if (args.mode === "live") {
    if (!audioActivated) {
      beginLiveQuestion();
    } else {
      playQuestion({ startMicrophone: true });
    }
  } else {
    playQuestion();
  }
});
rephraseButton.addEventListener("click", () => sendAction("rephrase"));
clearButton.addEventListener("click", () => {
  resetTranscript();
  if (args.mode === "live" && audioActivated && !paused) startRecognition();
});
submitButton.addEventListener("click", () => sendAction("answer"));
endButton.addEventListener("click", () => sendAction("end"));
transcript.addEventListener("input", () => {
  finalText = transcript.value;
  interimText = "";
  window.clearTimeout(silenceTimer);
  renderTranscript();
  showState(
    listening ? "listening" : "ready",
    "Transcript edited. Submit when it is correct.",
    listening ? "active" : "",
  );
});
speedSelect.addEventListener("change", () => {
  args.tts_speed = Number(speedSelect.value) || 1;
  showState("ready", `Speech speed set to ${speedSelect.selectedOptions[0].text}.`);
});
responseTimeSelect.addEventListener("change", () => {
  if (responseTimeSelect.value === "adaptive") {
    responseMode = "adaptive";
    autoSubmitDelay = 0;
  } else {
    autoSubmitDelay = Number(responseTimeSelect.value);
    responseMode = autoSubmitDelay > 0 ? "fixed" : "manual";
  }
  const label = responseTimeSelect.selectedOptions[0].text;
  showState("ready", `Response timing set to ${label}.`);
  startSilenceTimer();
});
captionsButton.addEventListener("click", () => setCaptions(!captionsEnabled));

window.addEventListener("offline", () => {
  connectionLost = true;
  paused = true;
  stopRecognition();
  cancelSpeech("offline", "The connection was lost.");
  closeAudioInput();
  pauseButton.textContent = "Resume";
  showState("offline", "Connection lost. Your transcript is preserved.", "error");
});
window.addEventListener("online", () => {
  connectionLost = false;
  paused = true;
  pauseButton.textContent = "Resume";
  showState("paused", "Connection restored. Select Resume when you are ready.");
});
window.addEventListener("beforeunload", () => {
  stopRecognition();
  cancelSpeech("unload", "The interview view is closing.");
  closeAudioInput();
});

Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, (event) => {
  applyArgs(event.detail.args || {});
});
Streamlit.setComponentReady();
renderTranscript();
showState(
  connectionLost ? "offline" : "ready",
  connectionLost ? "Reconnect to continue." : "Voice controls ready.",
);
