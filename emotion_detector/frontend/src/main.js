import * as faceapi from "@vladmandic/face-api";
import * as tf from "@tensorflow/tfjs";
import { Streamlit } from "streamlit-component-lib";

import "./style.css";

const INFERENCE_INTERVAL_MS = 350;
const STREAMLIT_UPDATE_INTERVAL_MS = 4000;
const HISTORY_SIZE = 9;
const NO_FACE_TIMEOUT_MS = 2500;

const video = document.querySelector("#camera");
const overlay = document.querySelector("#overlay");
const overlayContext = overlay.getContext("2d");
const faceCrop = document.querySelector("#face-crop");
const cropContext = faceCrop.getContext("2d", { willReadFrequently: true });
const placeholder = document.querySelector("#camera-placeholder");
const modelBadge = document.querySelector("#model-badge");
const stateLabel = document.querySelector("#state-label");
const scoreLabel = document.querySelector("#score-label");
const scoreTrack = document.querySelector(".score-track");
const scoreFill = document.querySelector("#score-fill");
const statusMessage = document.querySelector("#status-message");

let started = false;
let stopped = false;
let model = null;
let mediaStream = null;
let scoreHistory = [];
let sampleCount = 0;
let lastFaceAt = 0;
let lastSentAt = 0;
let lastPayloadSignature = "";
let componentArgs = {
  model_url: "app/static/emotion_model/model.json",
  face_models_url: "app/static/face_models/",
  model_name: "Viva Defense CNN",
  model_version: "viva-defense-fer2013-v1",
};

function assetUrl(path) {
  return new URL(path, document.referrer || window.location.href).href;
}

function setBadge(text, kind) {
  modelBadge.textContent = text;
  modelBadge.className = `badge badge-${kind}`;
}

function stateFromScore(score) {
  if (score < 0.4) return "confident_like";
  if (score > 0.6) return "stressed_like";
  return "uncertain";
}

function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2
    ? sorted[middle]
    : (sorted[middle - 1] + sorted[middle]) / 2;
}

function readingPayload({
  status,
  stressScore = null,
  message,
  errorCode = null,
}) {
  const validScore = Number.isFinite(stressScore)
    ? Math.min(1, Math.max(0, stressScore))
    : null;
  return {
    status,
    stress_score: validScore,
    confident_score: validScore === null ? null : 1 - validScore,
    calm_score: validScore === null ? null : 1 - validScore,
    state: validScore === null ? "unavailable" : stateFromScore(validScore),
    sample_count: sampleCount,
    measured_at: Date.now(),
    model_name: componentArgs.model_name,
    model_version: componentArgs.model_version,
    model_loaded: model !== null,
    error_code: errorCode,
    message,
  };
}

function sendReading(payload, force = false) {
  const now = Date.now();
  const signature = JSON.stringify({
    status: payload.status,
    state: payload.state,
    score:
      payload.stress_score === null
        ? null
        : Math.round(payload.stress_score * 100),
    error: payload.error_code,
  });

  if (!force && now - lastSentAt < STREAMLIT_UPDATE_INTERVAL_MS) {
    return;
  }
  if (!force && signature === lastPayloadSignature && payload.status !== "ready") {
    return;
  }

  lastSentAt = now;
  lastPayloadSignature = signature;
  Streamlit.setComponentValue(payload);
}

function renderUnavailable(title, message, status = "unavailable") {
  stateLabel.textContent = title;
  scoreLabel.textContent = "No reading";
  scoreTrack.setAttribute("aria-valuenow", "0");
  scoreFill.style.width = "0";
  scoreFill.style.background = "#64748b";
  statusMessage.textContent = message;
  if (status !== "loading") {
    sendReading(readingPayload({ status, message }));
  }
}

function renderScore(score) {
  const percent = Math.round(score * 100);
  const state = stateFromScore(score);
  const labels = {
    confident_like: "Confident-like expression",
    uncertain: "Expression signal uncertain",
    stressed_like: "Stressed-like expression",
  };
  const colors = {
    confident_like: "#22c55e",
    uncertain: "#f59e0b",
    stressed_like: "#ef4444",
  };

  stateLabel.textContent = labels[state];
  scoreLabel.textContent = `${percent}% toward stressed-like`;
  scoreTrack.setAttribute("aria-valuenow", String(percent));
  scoreFill.style.width = `${percent}%`;
  scoreFill.style.background = colors[state];
  statusMessage.textContent = `Model output smoothed from ${scoreHistory.length} recent face samples.`;
}

function fitOverlay() {
  const width = Math.max(1, Math.round(video.clientWidth));
  const height = Math.max(1, Math.round(video.clientHeight));
  if (overlay.width !== width || overlay.height !== height) {
    overlay.width = width;
    overlay.height = height;
  }
}

function drawFaceBox(box, score) {
  fitOverlay();
  const scaleX = overlay.width / video.videoWidth;
  const scaleY = overlay.height / video.videoHeight;
  const x = overlay.width - (box.x + box.width) * scaleX;
  const y = box.y * scaleY;
  const width = box.width * scaleX;
  const height = box.height * scaleY;

  overlayContext.clearRect(0, 0, overlay.width, overlay.height);
  const state = stateFromScore(score);
  overlayContext.strokeStyle =
    state === "confident_like"
      ? "#4ade80"
      : state === "stressed_like"
        ? "#f87171"
        : "#fbbf24";
  overlayContext.lineWidth = 2;
  overlayContext.strokeRect(x, y, width, height);
}

function cropFace(box) {
  const padding = Math.max(box.width, box.height) * 0.14;
  const size = Math.min(
    Math.max(box.width, box.height) + padding * 2,
    video.videoWidth,
    video.videoHeight,
  );
  const centerX = box.x + box.width / 2;
  const centerY = box.y + box.height / 2;
  const sourceX = Math.max(0, Math.min(video.videoWidth - size, centerX - size / 2));
  const sourceY = Math.max(
    0,
    Math.min(video.videoHeight - size, centerY - size / 2),
  );

  cropContext.save();
  cropContext.clearRect(0, 0, 48, 48);
  cropContext.filter = "grayscale(100%)";
  cropContext.drawImage(
    video,
    sourceX,
    sourceY,
    size,
    size,
    0,
    0,
    48,
    48,
  );
  cropContext.restore();
}

async function inferStressScore() {
  const input = tf.tidy(() =>
    tf.browser.fromPixels(faceCrop, 1).toFloat().div(255).expandDims(0),
  );
  let output = null;
  try {
    output = model.predict(input);
    const tensors = Array.isArray(output)
      ? output
      : output && typeof output.data === "function"
        ? [output]
        : Object.values(output || {});
    const tensor = tensors[0];
    if (!tensor || typeof tensor.data !== "function") {
      throw new Error("The model did not return a tensor.");
    }
    const values = await tensor.data();
    const score = Number(values[0]);
    if (!Number.isFinite(score)) {
      throw new Error("The model returned a non-finite score.");
    }
    return Math.min(1, Math.max(0, score));
  } finally {
    input.dispose();
    const tensors = Array.isArray(output)
      ? output
      : output && typeof output.dispose === "function"
        ? [output]
        : Object.values(output || {});
    tensors.forEach((tensor) => tensor?.dispose?.());
  }
}

async function processFrame() {
  if (stopped) return;

  if (video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
    window.setTimeout(processFrame, INFERENCE_INTERVAL_MS);
    return;
  }

  try {
    const detection = await faceapi.detectSingleFace(
      video,
      new faceapi.TinyFaceDetectorOptions({
        inputSize: 224,
        scoreThreshold: 0.55,
      }),
    );

    if (!detection) {
      overlayContext.clearRect(0, 0, overlay.width, overlay.height);
      if (lastFaceAt && Date.now() - lastFaceAt > NO_FACE_TIMEOUT_MS) {
        renderUnavailable("No face detected", "Move into view and face the camera.");
      }
      window.setTimeout(processFrame, INFERENCE_INTERVAL_MS);
      return;
    }

    lastFaceAt = Date.now();
    cropFace(detection.box);
    const score = await inferStressScore();
    sampleCount += 1;
    scoreHistory.push(score);
    if (scoreHistory.length > HISTORY_SIZE) scoreHistory.shift();

    const smoothedScore = median(scoreHistory);
    drawFaceBox(detection.box, smoothedScore);
    renderScore(smoothedScore);
    sendReading(
      readingPayload({
        status: "ready",
        stressScore: smoothedScore,
        message: "Live Viva Defense expression reading.",
      }),
    );
  } catch (error) {
    console.error("HireSense inference failed", error);
    setBadge("Inference error", "error");
    renderUnavailable(
      "Reading unavailable",
      "The model loaded, but inference failed. Reload the page to retry.",
      "error",
    );
  }

  window.setTimeout(processFrame, INFERENCE_INTERVAL_MS);
}

async function start() {
  if (started) return;
  started = true;
  renderUnavailable(
    "Initializing",
    "Loading the trained model and face detector.",
    "loading",
  );

  try {
    await tf.ready();
    const modelUrl = assetUrl(componentArgs.model_url);
    const faceModelUrl = assetUrl(componentArgs.face_models_url);
    [model] = await Promise.all([
      tf.loadGraphModel(modelUrl),
      faceapi.nets.tinyFaceDetector.loadFromUri(faceModelUrl),
    ]);
    setBadge("Viva Defense ready", "ready");
  } catch (error) {
    console.error("HireSense model loading failed", error);
    setBadge("Model unavailable", "error");
    renderUnavailable(
      "Model unavailable",
      "The trained model could not be loaded. No simulated score is being shown.",
      "error",
    );
    sendReading(
      readingPayload({
        status: "error",
        message: "The trained model could not be loaded.",
        errorCode: "MODEL_LOAD_FAILED",
      }),
      true,
    );
    return;
  }

  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: "user",
        width: { ideal: 640 },
        height: { ideal: 480 },
      },
      audio: false,
    });
    video.srcObject = mediaStream;
    await video.play();
    placeholder.classList.add("hidden");
    statusMessage.textContent = "Looking for a face.";
    Streamlit.setFrameHeight();
    processFrame();
  } catch (error) {
    console.error("HireSense camera access failed", error);
    setBadge("Camera unavailable", "error");
    renderUnavailable(
      "Camera unavailable",
      "Allow camera access in your browser, then reload the page.",
      "error",
    );
    sendReading(
      readingPayload({
        status: "error",
        message: "Camera access was denied or unavailable.",
        errorCode: "CAMERA_ACCESS_FAILED",
      }),
      true,
    );
  }
}

function stop() {
  stopped = true;
  mediaStream?.getTracks().forEach((track) => track.stop());
  model?.dispose();
}

Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, (event) => {
  componentArgs = { ...componentArgs, ...event.detail.args };
  Streamlit.setFrameHeight();
  start();
});
window.addEventListener("beforeunload", stop);
Streamlit.setComponentReady();
Streamlit.setFrameHeight();
