"""Natural, phase-based interview planning for HireSense voice practice."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class InterviewPhase:
    """One deliberate stage in a realistic interview progression."""

    key: str
    name: str
    difficulty: str
    purpose: str
    interviewer_instruction: str
    fallback_question: str
    allow_followup: bool = True


INTERVIEW_PHASES: tuple[InterviewPhase, ...] = (
    InterviewPhase(
        key="introduction",
        name="Introduction",
        difficulty="easy",
        purpose="Help the candidate settle in and establish a concise overview.",
        interviewer_instruction=(
            "Welcome the candidate as Maya, then ask for a concise professional "
            "introduction and why this opportunity is relevant."
        ),
        fallback_question=(
            "Hi, I am Maya. Thanks for joining me today. To begin, could you "
            "briefly introduce yourself and explain what brings you to this role?"
        ),
        allow_followup=False,
    ),
    InterviewPhase(
        key="motivation",
        name="Motivation and fit",
        difficulty="easy",
        purpose="Understand genuine motivation and alignment with the role.",
        interviewer_instruction=(
            "Acknowledge the introduction briefly. Ask what attracted the "
            "candidate to this role and connect the question to the supplied job."
        ),
        fallback_question=(
            "Thank you. What interested you in this role, and which part of the "
            "job description feels most connected to your goals?"
        ),
        allow_followup=False,
    ),
    InterviewPhase(
        key="experience",
        name="Relevant experience",
        difficulty="medium",
        purpose="Explore one resume example and establish personal ownership.",
        interviewer_instruction=(
            "Choose a relevant project or experience from the resume. Ask what "
            "the candidate personally owned, without asking several questions."
        ),
        fallback_question=(
            "Let us talk about your experience. Which project on your resume best "
            "shows that you can succeed in this role, and what did you personally own?"
        ),
    ),
    InterviewPhase(
        key="collaboration",
        name="Behavioural evidence",
        difficulty="medium",
        purpose="Explore collaboration, judgment, and a concrete outcome.",
        interviewer_instruction=(
            "Ask for one specific behavioural example involving teamwork, "
            "conflict, feedback, ownership, or a difficult deadline."
        ),
        fallback_question=(
            "Tell me about a time you worked through a disagreement or difficult "
            "collaboration. What did you do, and what was the outcome?"
        ),
    ),
    InterviewPhase(
        key="role_depth",
        name="Role depth",
        difficulty="medium",
        purpose="Test practical depth in an important requirement from the job.",
        interviewer_instruction=(
            "Select one important job requirement and ask how the candidate has "
            "used it in practice. Prefer a requirement supported by the resume."
        ),
        fallback_question=(
            "Now I would like to go a little deeper. Choose one core requirement "
            "from this role and walk me through how you have applied it in practice?"
        ),
    ),
    InterviewPhase(
        key="problem_solving",
        name="Problem solving",
        difficulty="hard",
        purpose="Evaluate a structured response to ambiguity and constraints.",
        interviewer_instruction=(
            "Present one realistic role-related scenario with incomplete "
            "information or a time constraint. Ask how the candidate would respond."
        ),
        fallback_question=(
            "Imagine you face an important role-related problem with incomplete "
            "information and a short deadline. How would you structure your response?"
        ),
    ),
    InterviewPhase(
        key="advanced_challenge",
        name="Advanced challenge",
        difficulty="hard",
        purpose="Probe tradeoffs, scaling, risk, and decision quality.",
        interviewer_instruction=(
            "Build on a prior answer when possible. Add one meaningful constraint "
            "and ask the candidate to explain the tradeoffs they would make."
        ),
        fallback_question=(
            "Let us make that more challenging. If your first solution had to "
            "handle ten times the workload with no increase in team size, what "
            "tradeoffs would you make?"
        ),
    ),
    InterviewPhase(
        key="closing",
        name="Closing",
        difficulty="reflection",
        purpose="Give the candidate a final opportunity to strengthen the case.",
        interviewer_instruction=(
            "Signal that the interview is closing. Ask what the interviewer "
            "should remember most or what important evidence has not been covered."
        ),
        fallback_question=(
            "Before we finish, what is the strongest reason we should consider "
            "you for this role, and is there anything important we have not covered?"
        ),
        allow_followup=False,
    ),
)

DEFAULT_MAIN_QUESTION_COUNT = len(INTERVIEW_PHASES)
MAX_TOTAL_FOLLOWUPS = 3


def phase_for_question(
    question_number: int,
    total_questions: int = DEFAULT_MAIN_QUESTION_COUNT,
) -> InterviewPhase:
    """Map any supported session length onto the ordered interview phases."""
    total = max(1, int(total_questions))
    number = max(1, min(int(question_number), total))
    phase_index = min(
        len(INTERVIEW_PHASES) - 1,
        ((number - 1) * len(INTERVIEW_PHASES)) // total,
    )
    if number == total:
        phase_index = len(INTERVIEW_PHASES) - 1
    return INTERVIEW_PHASES[phase_index]


def phase_context(
    question_number: int,
    total_questions: int = DEFAULT_MAIN_QUESTION_COUNT,
) -> dict[str, Any]:
    """Return a serializable phase description for the question engine."""
    phase = phase_for_question(question_number, total_questions)
    value = asdict(phase)
    value["question_number"] = max(1, int(question_number))
    value["total_questions"] = max(1, int(total_questions))
    return value


def fallback_question(
    question_number: int,
    total_questions: int = DEFAULT_MAIN_QUESTION_COUNT,
) -> str:
    """Return the phase-appropriate disclosed fallback question."""
    return phase_for_question(question_number, total_questions).fallback_question


def latest_delivery_guidance(conversation_history: list[dict[str, Any]]) -> str:
    """Turn the latest coaching signal into restrained interviewer guidance."""
    latest: dict[str, Any] | None = None
    for entry in reversed(conversation_history):
        if entry.get("role") != "user":
            continue
        speech_stats = entry.get("speech_stats")
        if not isinstance(speech_stats, dict):
            break
        candidate = speech_stats.get("delivery_confidence")
        if isinstance(candidate, dict):
            latest = candidate
        break

    if not latest:
        return (
            "Use a calm professional tone and follow the planned progression. "
            "Do not infer the candidate's emotions."
        )

    score = latest.get("score")
    reliability = str(latest.get("reliability", "Low"))
    if not isinstance(score, (int, float)) or reliability == "Low":
        return (
            "The delivery signal is not reliable enough to adapt the interview. "
            "Continue with clear, neutral wording."
        )
    if score < 45:
        return (
            "Use a short acknowledgment and clear single-part wording. Keep the "
            "planned competency and difficulty unchanged."
        )
    if score >= 75:
        return (
            "Use a concise acknowledgment and proceed with the planned challenge. "
            "A relevant constraint or tradeoff is appropriate."
        )
    return (
        "Use a natural acknowledgment and continue with the planned difficulty. "
        "Ask one focused question at a time."
    )

