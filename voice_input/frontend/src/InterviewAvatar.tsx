import React from "react";

export type InterviewState =
  | "ready"
  | "listening"
  | "processing"
  | "speaking"
  | "paused"
  | "error"
  | "offline";

type InterviewAvatarProps = {
  interviewState: InterviewState;
  interviewerName?: string;
  allowInterrupt?: boolean;
  onInterrupt?: () => void;
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

export default function InterviewAvatar({
  interviewState,
  interviewerName = "Maya",
  allowInterrupt = true,
  onInterrupt,
}: InterviewAvatarProps) {
  const stateCopy = STATE_COPY[interviewState] ?? STATE_COPY.ready;
  const canInterrupt = allowInterrupt && interviewState === "speaking";

  return (
    <section
      className="interviewer-card"
      data-state={interviewState}
      aria-label={`${interviewerName}, HireSense AI interviewer. ${stateCopy.label}.`}
    >
      <div className="interviewer-visual" aria-hidden="true">
        <div className="avatar-orbit avatar-orbit-one" />
        <div className="avatar-orbit avatar-orbit-two" />
        <div className="avatar-signal-ring" />

        <svg
          className="interviewer-svg"
          viewBox="0 0 280 300"
          role="img"
          aria-label={`Animated portrait of ${interviewerName}`}
        >
          <defs>
            <linearGradient id="avatar-jacket" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#202a4a" />
              <stop offset="100%" stopColor="#11182f" />
            </linearGradient>
            <linearGradient id="avatar-shirt" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#f5f3ff" />
              <stop offset="100%" stopColor="#c4b5fd" />
            </linearGradient>
            <linearGradient id="avatar-hair" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#251b31" />
              <stop offset="100%" stopColor="#130e20" />
            </linearGradient>
            <radialGradient id="avatar-skin" cx="42%" cy="30%" r="72%">
              <stop offset="0%" stopColor="#f5c9b5" />
              <stop offset="100%" stopColor="#d9977f" />
            </radialGradient>
            <filter id="avatar-shadow" x="-30%" y="-30%" width="160%" height="180%">
              <feDropShadow
                dx="0"
                dy="10"
                stdDeviation="10"
                floodColor="#050812"
                floodOpacity=".28"
              />
            </filter>
          </defs>

          <g className="avatar-body" filter="url(#avatar-shadow)">
            <path
              className="avatar-shoulders"
              d="M31 300c6-52 38-78 82-87h54c44 9 76 35 82 87H31Z"
              fill="url(#avatar-jacket)"
            />
            <path
              d="m107 218 33 50 33-50-17-11h-32l-17 11Z"
              fill="url(#avatar-shirt)"
            />
            <path
              d="m105 218 35 50-20 32H72c5-37 17-62 33-82Z"
              fill="#18213d"
            />
            <path
              d="m175 218-35 50 20 32h48c-5-37-17-62-33-82Z"
              fill="#18213d"
            />
          </g>

          <g className="avatar-head">
            <path
              className="avatar-hair-back"
              d="M75 104c0-58 29-92 67-92 45 0 71 37 68 93l-8 93c-22 22-104 23-126-2l-1-92Z"
              fill="url(#avatar-hair)"
            />
            <path
              className="avatar-neck"
              d="M119 178h43l5 42c-17 16-37 16-54 0l6-42Z"
              fill="#d99a83"
            />
            <ellipse cx="79" cy="123" rx="13" ry="21" fill="#dea088" />
            <ellipse cx="204" cy="123" rx="13" ry="21" fill="#dea088" />
            <path
              className="avatar-face"
              d="M88 94c3-45 27-66 54-66 34 0 58 29 56 72l-3 44c-3 41-25 65-54 65-31 0-52-27-54-68l1-47Z"
              fill="url(#avatar-skin)"
            />
            <path
              d="M88 95c3-48 24-73 58-73 29 0 52 19 58 56-20-4-38-18-47-38-16 27-39 43-69 55Z"
              fill="url(#avatar-hair)"
            />
            <path
              d="M91 92c-3 28-3 65 7 92-19-19-28-49-22-85 5-35 22-62 50-73-21 17-32 38-35 66Z"
              fill="#1a1325"
            />
            <path
              d="M197 82c9 34 5 76-4 105 19-18 26-54 19-89-6-32-24-58-52-68 20 15 32 31 37 52Z"
              fill="#171022"
            />

            <path
              className="avatar-brow avatar-brow-left"
              d="M104 109c9-6 20-6 29-1"
              fill="none"
              stroke="#4a2930"
              strokeLinecap="round"
              strokeWidth="4"
            />
            <path
              className="avatar-brow avatar-brow-right"
              d="M151 108c9-5 20-4 27 2"
              fill="none"
              stroke="#4a2930"
              strokeLinecap="round"
              strokeWidth="4"
            />

            <g className="avatar-eyes">
              <ellipse cx="119" cy="125" rx="11" ry="8" fill="#fffaf8" />
              <ellipse cx="166" cy="125" rx="11" ry="8" fill="#fffaf8" />
              <circle className="avatar-pupil avatar-pupil-left" cx="121" cy="125" r="4.6" fill="#473a52" />
              <circle className="avatar-pupil avatar-pupil-right" cx="164" cy="125" r="4.6" fill="#473a52" />
              <circle cx="122.4" cy="123.5" r="1.4" fill="#ffffff" />
              <circle cx="165.4" cy="123.5" r="1.4" fill="#ffffff" />
              <path
                className="avatar-eyelid avatar-eyelid-left"
                d="M107 124c7-9 18-10 25 0-8 5-17 5-25 0Z"
                fill="#e5ad98"
              />
              <path
                className="avatar-eyelid avatar-eyelid-right"
                d="M153 124c7-9 18-9 25 1-8 5-17 5-25-1Z"
                fill="#e5ad98"
              />
            </g>

            <path
              d="M141 127c-1 11-3 22-7 31 5 4 11 4 16 0"
              fill="none"
              stroke="#bd7767"
              strokeLinecap="round"
              strokeWidth="2.6"
            />
            <ellipse cx="106" cy="153" rx="12" ry="6" fill="#e58d86" opacity=".17" />
            <ellipse cx="178" cy="153" rx="12" ry="6" fill="#e58d86" opacity=".17" />

            <g className="avatar-mouth">
              <path
                className="avatar-mouth-fill"
                d="M124 174c10 4 22 4 34 0-6 16-27 17-34 0Z"
                fill="#6f3044"
              />
              <path
                className="avatar-teeth"
                d="M127 176c9 2 19 2 28 0-6 6-21 7-28 0Z"
                fill="#fff8f4"
              />
              <path
                className="avatar-mouth-line"
                d="M124 174c10 4 22 4 34 0"
                fill="none"
                stroke="#8f4a57"
                strokeLinecap="round"
                strokeWidth="2.4"
              />
            </g>
          </g>

          <g className="avatar-thinking-dots">
            <circle cx="204" cy="46" r="5" />
            <circle cx="220" cy="34" r="5" />
            <circle cx="238" cy="25" r="5" />
          </g>

          <g className="avatar-wave">
            <rect x="92" y="278" width="5" height="8" rx="2.5" />
            <rect x="103" y="273" width="5" height="18" rx="2.5" />
            <rect x="114" y="267" width="5" height="30" rx="2.5" />
            <rect x="125" y="271" width="5" height="22" rx="2.5" />
            <rect x="136" y="264" width="5" height="36" rx="2.5" />
            <rect x="147" y="270" width="5" height="24" rx="2.5" />
            <rect x="158" y="266" width="5" height="32" rx="2.5" />
            <rect x="169" y="273" width="5" height="18" rx="2.5" />
            <rect x="180" y="278" width="5" height="8" rx="2.5" />
          </g>
        </svg>
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
