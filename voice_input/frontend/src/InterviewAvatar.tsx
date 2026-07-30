import React, { useEffect, useRef, useState } from "react";

import {
  MayaAvatar3D,
  type MayaState,
  type MayaViseme,
} from "./MayaAvatar3D";

export type InterviewState = MayaState;

type InterviewAvatarProps = {
  interviewState: InterviewState;
  interviewerName?: string;
  allowInterrupt?: boolean;
  supportMode?: boolean;
  spokenText?: string;
  onInterrupt?: () => void;
};

type VisemeDetail = {
  viseme?: MayaViseme;
  intensity?: number;
};

const STATE_COPY: Record<
  InterviewState,
  { label: string; detail: string }
> = {
  ready: {
    label: "Ready",
    detail: "Your AI interviewer is ready",
  },
  listening: {
    label: "Listening",
    detail: "Take your time and speak naturally",
  },
  processing: {
    label: "Thinking",
    detail: "Preparing the next response",
  },
  speaking: {
    label: "Speaking",
    detail: "You can interrupt at any time",
  },
  paused: {
    label: "Paused",
    detail: "Your place is safely preserved",
  },
  error: {
    label: "Audio unavailable",
    detail: "Continue with the written question",
  },
  offline: {
    label: "Connection lost",
    detail: "Your transcript is safely preserved",
  },
};

function StaticAvatarFallback({
  interviewerName,
}: {
  interviewerName: string;
}) {
  return (
    <svg
      className="interviewer-fallback"
      viewBox="0 0 240 280"
      role="img"
      aria-label={`Portrait of ${interviewerName}`}
    >
      <defs>
        <linearGradient id="fallback-jacket" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#26375f" />
          <stop offset="100%" stopColor="#111a35" />
        </linearGradient>
        <radialGradient id="fallback-skin" cx="42%" cy="28%" r="72%">
          <stop offset="0%" stopColor="#f0c0aa" />
          <stop offset="100%" stopColor="#d28d78" />
        </radialGradient>
      </defs>
      <path
        d="M22 280c5-48 39-74 80-80h36c41 6 75 32 80 80H22Z"
        fill="url(#fallback-jacket)"
      />
      <path d="m91 206 29 42 29-42-14-9h-30l-14 9Z" fill="#f0efff" />
      <path
        d="M63 94c0-55 24-86 58-86 41 0 65 35 62 88l-7 91c-19 21-93 21-113-2V94Z"
        fill="#21182b"
      />
      <path
        d="M78 88c3-42 22-62 44-62 30 0 50 27 49 68l-3 40c-3 39-21 61-46 61-27 0-45-25-47-64l3-43Z"
        fill="url(#fallback-skin)"
      />
      <path
        d="M78 90c2-46 20-69 48-69 26 0 45 18 50 52-18-4-32-16-40-35-14 25-33 40-58 52Z"
        fill="#21182b"
      />
      <ellipse cx="103" cy="116" rx="9" ry="6" fill="#fffaf5" />
      <ellipse cx="142" cy="116" rx="9" ry="6" fill="#fffaf5" />
      <circle cx="104" cy="116" r="3.8" fill="#5b3f32" />
      <circle cx="141" cy="116" r="3.8" fill="#5b3f32" />
      <path
        d="M93 101c8-5 16-5 23-1M130 100c8-4 16-3 22 2"
        fill="none"
        stroke="#3c2430"
        strokeLinecap="round"
        strokeWidth="3.4"
      />
      <path
        d="M122 119c0 9-2 18-5 25 4 3 9 3 13 0"
        fill="none"
        stroke="#bd7767"
        strokeLinecap="round"
        strokeWidth="2.3"
      />
      <path
        className="fallback-mouth"
        d="M108 158c9 4 19 4 29 0-6 10-22 11-29 0Z"
        fill="#8f4a57"
      />
    </svg>
  );
}

export default function InterviewAvatar({
  interviewState,
  interviewerName = "Maya",
  allowInterrupt = true,
  supportMode = false,
  spokenText = "",
  onInterrupt,
}: InterviewAvatarProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const avatarRef = useRef<MayaAvatar3D | null>(null);
  const [usingFallback, setUsingFallback] = useState(false);
  const stateCopy = STATE_COPY[interviewState] ?? STATE_COPY.ready;
  const canInterrupt = allowInterrupt && interviewState === "speaking";

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;

    try {
      avatarRef.current = new MayaAvatar3D({
        canvas,
        onUnavailable: () => {
          avatarRef.current?.destroy();
          avatarRef.current = null;
          setUsingFallback(true);
        },
      });
    } catch {
      avatarRef.current = null;
      setUsingFallback(true);
    }

    return () => {
      avatarRef.current?.destroy();
      avatarRef.current = null;
    };
  }, []);

  useEffect(() => {
    avatarRef.current?.setState(interviewState);
  }, [interviewState]);

  useEffect(() => {
    avatarRef.current?.setSupportMode(supportMode);
  }, [supportMode]);

  useEffect(() => {
    const handleViseme = (event: Event) => {
      const detail = (event as CustomEvent<VisemeDetail>).detail ?? {};
      avatarRef.current?.setViseme(detail);
    };
    window.addEventListener("hiresense:maya-viseme", handleViseme);
    return () =>
      window.removeEventListener("hiresense:maya-viseme", handleViseme);
  }, []);

  return (
    <section
      className="interviewer-card"
      data-state={interviewState}
      data-support={supportMode ? "true" : "false"}
      aria-label={`${interviewerName}, HireSense 3D AI interviewer. ${stateCopy.label}.`}
    >
      <div className="interviewer-visual">
        <div className="avatar-orbit avatar-orbit-one" aria-hidden="true" />
        <div className="avatar-orbit avatar-orbit-two" aria-hidden="true" />
        <div className="avatar-signal-ring" aria-hidden="true" />
        <canvas
          ref={canvasRef}
          className={`maya-3d-canvas${usingFallback ? " hidden" : ""}`}
          data-avatar-engine="threejs"
          data-spoken-text-length={spokenText.length}
          aria-hidden="true"
        />
        {usingFallback ? (
          <StaticAvatarFallback interviewerName={interviewerName} />
        ) : null}
        <span className="avatar-depth-label" aria-hidden="true">
          3D
        </span>
        <div className="avatar-wave" aria-hidden="true">
          {Array.from({ length: 9 }, (_, index) => (
            <span key={index} />
          ))}
        </div>
      </div>

      <div className="interviewer-copy">
        <div>
          <strong>{interviewerName}</strong>
          <span>HireSense AI interviewer</span>
        </div>
        <div className="avatar-state-copy" aria-live="polite">
          <span className="avatar-state-dot" />
          <span>
            <b>{stateCopy.label}</b>
            <small>{stateCopy.detail}</small>
          </span>
        </div>
      </div>

      {canInterrupt ? (
        <button
          className="interrupt-interviewer"
          type="button"
          onClick={onInterrupt}
          aria-label={`Interrupt ${interviewerName} and start answering`}
        >
          <span aria-hidden="true">◼</span>
          Interrupt interviewer
        </button>
      ) : null}
    </section>
  );
}
