import React, { useEffect, useRef, useState } from "react";

import {
  MayaAvatar3D,
  type MayaState,
  type MayaViseme,
} from "./MayaAvatar3D";
import mayaNeutralUrl from "./assets/maya-neutral.webp";

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
    <img
      className="interviewer-fallback"
      src={mayaNeutralUrl}
      alt={`Portrait of ${interviewerName}`}
    />
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
