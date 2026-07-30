"""
interview_arena.py
==================

HireSense AI - Interview Arena Module

Features:
1. RAG Integration - Resume/JD personalization
2. Real-Time Emotion Detection - Webcam analysis
3. Adaptive AI - Optional tone changes from an experimental facial signal
4. TTS Audio - Questions spoken aloud
5. Analytics Dashboard - Stress graphs and composure scores

Tech Stack: OpenRouter.ai for LLM, TensorFlow.js for client-side model inference
"""

from __future__ import annotations

import os
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, Iterator, List, Optional

from langchain_core.utils.utils import secret_from_env
from langchain_openai import ChatOpenAI
from pydantic import Field, SecretStr
from pypdf import PdfReader

import config
import interview_flow
from model_utils import message_text, normalize_question

# ============================================================================
# OpenRouter Integration (Same as V4)
# ============================================================================


class ChatOpenRouter(ChatOpenAI):
    """OpenRouter API wrapper with streaming support."""

    openai_api_key: Optional[SecretStr] = Field(
        alias="api_key",
        default_factory=secret_from_env("OPENROUTER_API_KEY", default=None),
    )

    @property
    def lc_secrets(self) -> Dict[str, str]:
        return {"openai_api_key": "OPENROUTER_API_KEY"}

    def __init__(self, openai_api_key: Optional[str] = None, **kwargs: Any) -> None:
        openai_api_key = openai_api_key or os.environ.get("OPENROUTER_API_KEY")
        if not openai_api_key:
            raise ValueError(
                "OPENROUTER_API_KEY must be set in your environment or passed explicitly."
            )

        try:
            request_timeout = float(
                os.environ.get("OPENROUTER_TIMEOUT_SECONDS", "45")
            )
        except ValueError:
            request_timeout = 45.0
        try:
            max_retries = int(os.environ.get("OPENROUTER_MAX_RETRIES", "2"))
        except ValueError:
            max_retries = 2

        kwargs.setdefault("timeout", max(5.0, min(120.0, request_timeout)))
        kwargs.setdefault("max_retries", max(0, min(5, max_retries)))
        super().__init__(
            base_url="https://openrouter.ai/api/v1",
            openai_api_key=openai_api_key,
            **kwargs,
        )


# ============================================================================
# RAG System - Resume/JD Processing
# ============================================================================


MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 75
MAX_DOCUMENT_CHARACTERS = 60_000


def extract_pdf_text(file_data: bytes) -> str:
    """Extract bounded text from a PDF and reject unsafe or empty input."""
    if not isinstance(file_data, bytes) or not file_data:
        raise ValueError("The uploaded PDF is empty.")
    if len(file_data) > MAX_PDF_BYTES:
        raise ValueError("The PDF is larger than the 10 MB upload limit.")

    reader = PdfReader(BytesIO(file_data))
    if len(reader.pages) > MAX_PDF_PAGES:
        raise ValueError(f"The PDF exceeds the {MAX_PDF_PAGES}-page limit.")

    text: list[str] = []
    for page in reader.pages:
        try:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
        except Exception:
            continue
    extracted = "\n\n".join(text).strip()
    if not extracted:
        raise ValueError(
            "No readable text was found. Use a text-based PDF or paste the text."
        )
    return extracted[:MAX_DOCUMENT_CHARACTERS]


def parse_resume(resume_text: str) -> Dict[str, Any]:
    """Parse resume text to extract key information for RAG."""
    normalized = str(resume_text).strip()
    return {
        "raw_text": normalized[:MAX_DOCUMENT_CHARACTERS],
        "word_count": len(normalized.split()),
        "truncated": len(normalized) > MAX_DOCUMENT_CHARACTERS,
        "extracted_at": datetime.now().isoformat(),
    }


def parse_job_description(jd_text: str) -> Dict[str, Any]:
    """Parse job description to extract requirements."""
    normalized = str(jd_text).strip()
    return {
        "raw_text": normalized[:MAX_DOCUMENT_CHARACTERS],
        "word_count": len(normalized.split()),
        "truncated": len(normalized) > MAX_DOCUMENT_CHARACTERS,
        "extracted_at": datetime.now().isoformat(),
    }


def build_rag_context(resume_data: Dict, jd_data: Dict) -> str:
    """Build RAG context from resume and job description."""
    context = f"""
=== CANDIDATE RESUME ===
{resume_data.get("raw_text", "No resume provided")}

=== JOB DESCRIPTION ===
{jd_data.get("raw_text", "No job description provided")}
"""
    return context.strip()


# ============================================================================
# Interview Type Prompts
# ============================================================================

INTERVIEW_TYPE_PROMPTS = {
    "Technical": """Focus on technical skills, coding problems, system design, and domain expertise.
Ask about:
- Technical projects and implementations
- Problem-solving approaches
- System design and architecture
- Coding best practices
- Technical challenges faced""",
    "Behavioral": """Focus on soft skills using the STAR method (Situation, Task, Action, Result).
Ask about:
- Teamwork and collaboration experiences
- Leadership and initiative
- Conflict resolution
- Time management and prioritization
- Adaptability and learning""",
    "HR": """Focus on culture fit, career goals, and company alignment.
Ask about:
- Career aspirations and goals
- Why this company/role
- Salary expectations (be tactful)
- Work style preferences
- Values and motivations""",
    "Case Study": """Focus on analytical and problem-solving abilities.
Present business scenarios and evaluate:
- Analytical thinking
- Structured problem-solving
- Business acumen
- Communication of complex ideas
- Decision-making process""",
    "Mixed": """Combine technical, behavioral, and HR questions for a comprehensive interview.
Balance between:
- Technical competency
- Soft skills and teamwork
- Culture fit and motivation""",
}

BUILT_IN_QUESTION_BANK = {
    "Technical": [
        "Tell me about the most technically demanding project you have worked on and the decisions you personally owned?",
        "How would you diagnose a production issue when the symptoms are intermittent and the logs are incomplete?",
        "How would you design a service that must remain reliable as traffic grows tenfold?",
        "Describe a technical tradeoff where you chose simplicity over maximum performance, or the reverse?",
        "What testing strategy do you use to prevent regressions in a system with several dependencies?",
        "How do you protect sensitive data throughout storage, processing, and transmission?",
        "How do you approach a task that requires a technology you have never used before?",
        "Give an example of a performance bottleneck you found and how you measured the improvement?",
        "Tell me about a technical disagreement during code review and how the team reached a decision?",
        "If you could rebuild one system from your past work, what would you change and why?",
    ],
    "Behavioral": [
        "Tell me about a time you took ownership of an important result without being asked?",
        "Describe a conflict within a team and the specific steps you took to resolve it?",
        "Tell me about a difficult deadline and how you decided what to prioritize?",
        "Give an example of feedback that changed how you work?",
        "Describe a decision you made with incomplete information and what happened?",
        "Tell me about a mistake you made and how you prevented it from recurring?",
        "Give an example of how you influenced someone when you had no formal authority?",
        "Describe a situation where you had to adapt quickly to a major change?",
        "Tell me about a teammate you helped succeed and what you did?",
        "What professional accomplishment best demonstrates how you create measurable impact?",
    ],
    "HR": [
        "What attracted you to this role, and why is this the right next step for you?",
        "Which parts of your background are most relevant to what this role needs?",
        "What kind of work environment helps you perform at your best?",
        "What are you hoping to learn or develop in your next role?",
        "How do you decide whether a company and team are a good fit for you?",
        "What motivates you when the work becomes repetitive or difficult?",
        "How would your recent manager describe your strongest contribution and your main development area?",
        "What expectations do you have for collaboration with your manager and teammates?",
        "Why are you considering leaving, or why did you leave, your most recent role?",
        "What questions would you ask before deciding whether to accept this position?",
    ],
    "Case Study": [
        "A key product metric falls by 20 percent in one week; how would you structure the investigation?",
        "A client wants a feature that conflicts with the product strategy; how would you evaluate the request?",
        "You have three promising initiatives but resources for only one; how would you choose?",
        "A process is slow, expensive, and poorly documented; how would you improve it?",
        "A new market offers strong growth but limited data; how would you assess whether to enter?",
        "Customer complaints are rising while satisfaction surveys remain stable; how would you explain and investigate this?",
        "A project is behind schedule and its scope cannot be fully delivered; what would you do next?",
        "Two departments report conflicting numbers for the same business metric; how would you resolve it?",
        "A competitor cuts prices substantially; how would you decide whether to respond?",
        "After implementing your recommendation, which measures would you track to determine whether it worked?",
    ],
    "Mixed": [
        "Please introduce yourself and explain which experience best prepares you for this role?",
        "Tell me about a challenging project and the specific contribution you made?",
        "How would you approach a difficult role-related problem that you have not seen before?",
        "Describe a disagreement at work and how you handled it?",
        "Which requirement in this role would stretch you most, and how would you close that gap?",
        "Tell me about a decision where you had to balance speed, quality, and risk?",
        "What measurable result from your work are you most proud of?",
        "How do you communicate complex information to someone without your technical background?",
        "Why does this role fit your longer-term direction?",
        "What would you want the interviewer to remember most about your candidacy?",
    ],
}


def get_builtin_interview_question(
    interview_type: str,
    question_number: int,
    total_questions: int = interview_flow.DEFAULT_MAIN_QUESTION_COUNT,
) -> str:
    """Return a deterministic backup question when live generation is unavailable."""
    if interview_type == "Mixed":
        return interview_flow.fallback_question(
            question_number,
            total_questions,
        )
    questions = BUILT_IN_QUESTION_BANK.get(
        interview_type, BUILT_IN_QUESTION_BANK["Mixed"]
    )
    index = (max(1, int(question_number)) - 1) % len(questions)
    question = questions[index]
    if int(question_number) == 1 and interview_type != "Mixed":
        return f"Welcome to HireSense. To begin, {question[0].lower()}{question[1:]}"
    return question


def _message_content_to_text(content: Any) -> str:
    """Normalize text returned as either a string or content-block list."""
    return message_text(content)


def _looks_like_interview_question(text: str) -> bool:
    """Reject empty or obviously incomplete model responses."""
    cleaned = text.strip()
    if len(cleaned) < 12:
        return False
    if "?" in cleaned:
        return True
    lowered = cleaned.casefold()
    return any(
        phrase in lowered
        for phrase in (
            "tell me",
            "describe ",
            "explain ",
            "walk me through",
            "how would",
            "what would",
            "why ",
        )
    )


# ============================================================================
# Adaptive Interview AI
# ============================================================================

INTERVIEW_SYSTEM_PROMPT_SUPPORTIVE = """You are HireSense AI, a supportive and encouraging AI interviewer.
    Repeated Viva Defense checkpoints were stressed-like. Do not treat this as
    a diagnosis or claim to know the candidate's feelings. Preserve the planned
    competency and difficulty. Your role is to:
1. Ask questions in a warm, friendly manner
2. Provide encouragement and positive reinforcement
3. Give the candidate time to think
4. Use clear, single-part wording
5. Keep the interview progression unchanged

Use the provided resume and job description to ask relevant, personalized questions.
Keep questions clear, patient, and professional."""

INTERVIEW_SYSTEM_PROMPT_CHALLENGING = """You are HireSense AI, a rigorous and challenging AI interviewer.
    An experimental facial model returned a low stress signal, so advanced
    practice mode was selected. Do not claim this measures confidence. Your role is to:
1. Ask probing, in-depth technical questions
2. Challenge their answers with follow-up questions
3. Test the depth of their knowledge
4. Present edge cases and complex scenarios
5. Maintain professional pressure to assess their limits

Use the provided resume and job description to ask relevant, personalized questions.
Push them to demonstrate their expertise. Be professional but demanding."""

INTERVIEW_SYSTEM_PROMPT_NEUTRAL = """You are HireSense AI, a professional AI interviewer.
Your role is to:
1. Ask balanced, fair questions
2. Assess both technical skills and soft skills
3. Use the resume and job description for personalized questions
4. Maintain a professional and neutral tone
5. Provide a realistic interview experience

Start with an introduction and then proceed with questions."""


def get_interview_system_prompt(emotional_state: str) -> str:
    """Get the appropriate system prompt based on emotional state."""
    if emotional_state in {"stress_signal", "stressed"}:
        return INTERVIEW_SYSTEM_PROMPT_SUPPORTIVE
    return INTERVIEW_SYSTEM_PROMPT_NEUTRAL


def generate_interview_question(
    rag_context: str,
    conversation_history: List[Dict[str, str]],
    emotional_state: str = "neutral",
    question_number: int = 1,
    total_questions: int = 5,
    interview_type: str = "Mixed",
    company: str = "general",
    *,
    model_name: str | None = None,
    temperature: float = 0.7,
    orchestrator: Any | None = None,
) -> Iterator[Dict[str, Any]]:
    """
    Generate an interview question using the HireSense 5-agent engine.

    Pipeline: ContentAgent → InsightAgent → ImpactAgent → StrategyAgent → ExecutionAgent

    On the first question, all 5 agents run.
    On subsequent questions, Content + Insight are cached (resume doesn't change),
    but Impact + Strategy + Execution re-run (emotion may have changed).

    Yields intermediate trace events and final question chunks as dicts.
    """
    selected_model = model_name or config.get_openrouter_model()
    phase = interview_flow.phase_context(question_number, total_questions)
    buffered_question = []
    failure_reason = None

    try:
        if orchestrator is None:
            from hiresense_agent import get_orchestrator

            orchestrator = get_orchestrator(
                model_name=selected_model,
                temperature=temperature,
            )

        for step in orchestrator.run_pipeline(
            rag_context=rag_context,
            conversation_history=conversation_history,
            emotional_state=emotional_state,
            question_number=question_number,
            total_questions=total_questions,
            interview_type=interview_type,
            company=company,
            phase=phase,
        ):
            if isinstance(step, dict) and step.get("type") == "question_chunk":
                text = _message_content_to_text(step.get("content"))
                if text:
                    buffered_question.append(text)
            else:
                yield step
    except Exception as exc:
        failure_reason = exc.__class__.__name__

    question_text = normalize_question("".join(buffered_question))
    if not failure_reason and _looks_like_interview_question(question_text):
        yield {
            "type": "question_generation_status",
            "source": "model",
            "model": selected_model,
        }
        yield {"type": "question_chunk", "content": question_text}
        return

    yield {
        "type": "question_generation_status",
        "source": "built_in_fallback",
        "reason": failure_reason or "empty_or_invalid_model_response",
    }
    yield {
        "type": "question_chunk",
        "content": get_builtin_interview_question(
            interview_type,
            question_number,
            total_questions,
        ),
    }


def rephrase_interview_question(
    question: str,
    *,
    language_name: str = "English",
    model_name: str | None = None,
) -> dict[str, str]:
    """Rephrase one question for accessibility without changing its intent."""
    original = str(question).strip()
    if not original:
        return {
            "question": "",
            "source": "unavailable",
            "reason": "empty_question",
        }

    selected_model = model_name or config.get_openrouter_model()
    messages = [
        {
            "role": "system",
            "content": (
                "You rewrite interview questions for accessibility. Preserve the "
                "competency and difficulty being assessed. Use shorter, clearer "
                "sentences and plain language. Ask exactly one question. Do not "
                "add advice, examples, hints, or evaluation criteria. Return only "
                f"the rewritten question in {language_name}."
            ),
        },
        {"role": "user", "content": original},
    ]
    try:
        llm = ChatOpenRouter(
            model_name=selected_model,
            temperature=0.2,
            streaming=False,
            max_tokens=180,
            timeout=15,
            max_retries=0,
        )
        response = llm.invoke(messages)
        rewritten = normalize_question(_message_content_to_text(response.content))
    except Exception as exc:
        return {
            "question": original,
            "source": "unavailable",
            "reason": exc.__class__.__name__,
        }

    if not _looks_like_interview_question(rewritten):
        return {
            "question": original,
            "source": "unavailable",
            "reason": "empty_or_invalid_model_response",
        }
    return {
        "question": rewritten,
        "source": "model_rephrase",
        "model": selected_model,
    }


def evaluate_answer(
    rag_context: str,
    question: str,
    answer: str,
    emotional_state: str = "neutral",
    *,
    model_name: str | None = None,
    temperature: float = 0.3,
) -> Iterator[str]:
    """Evaluate one answer through the transcript-verified rubric."""
    del emotional_state, temperature
    from evidence_scoring import evaluate_interview, format_assessment_markdown

    assessment = evaluate_interview(
        rag_context,
        [
            {"role": "assistant", "content": question},
            {"role": "user", "content": answer},
        ],
        model_name=model_name,
    )
    yield format_assessment_markdown(assessment)


def generate_final_report(
    rag_context: str,
    conversation_history: List[Dict[str, str]],
    stress_timeline: List[Dict[str, Any]],
    *,
    model_name: str | None = None,
    temperature: float = 0.3,
) -> Iterator[str]:
    """Generate the same validated evidence report used by the main app."""
    del stress_timeline, temperature
    from evidence_scoring import evaluate_interview, format_assessment_markdown

    assessment = evaluate_interview(
        rag_context,
        conversation_history,
        model_name=model_name,
    )
    yield format_assessment_markdown(assessment)


# ============================================================================
# Analytics & Visualization Data
# ============================================================================


def calculate_composure_metrics(
    stress_timeline: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Calculate composure metrics from stress timeline."""
    valid_entries = [
        entry
        for entry in stress_timeline
        if isinstance(entry.get("stress_level"), (int, float))
        and not isinstance(entry.get("stress_level"), bool)
        and 0 <= float(entry["stress_level"]) <= 1
    ]
    if not valid_entries:
        return {
            "available": False,
            "average_stress": None,
            "composure_score": None,
            "stress_variance": None,
            "recovery_rate": None,
            "peak_stress_time": None,
            "peak_stress_value": None,
            "calmest_moment": None,
            "calmest_value": None,
            "total_readings": 0,
        }

    stress_values = [float(entry["stress_level"]) for entry in valid_entries]
    timestamps = [
        entry.get("timestamp", index * 5) for index, entry in enumerate(valid_entries)
    ]

    avg_stress = sum(stress_values) / len(stress_values)
    composure_score = (1 - avg_stress) * 100

    # Calculate variance
    variance = sum((x - avg_stress) ** 2 for x in stress_values) / len(stress_values)

    # Find peak and calm moments
    max_idx = stress_values.index(max(stress_values))
    min_idx = stress_values.index(min(stress_values))

    # Calculate recovery rate (how quickly stress decreases after peaks)
    recovery_events = []
    for i in range(1, len(stress_values)):
        if stress_values[i] < stress_values[i - 1]:
            recovery_events.append(stress_values[i - 1] - stress_values[i])

    recovery_rate = (
        sum(recovery_events) / len(recovery_events) if recovery_events else 0
    )

    return {
        "available": True,
        "average_stress": avg_stress,
        "composure_score": composure_score,
        "stress_variance": variance,
        "recovery_rate": recovery_rate,
        "peak_stress_time": timestamps[max_idx] if timestamps else None,
        "peak_stress_value": max(stress_values),
        "calmest_moment": timestamps[min_idx] if timestamps else None,
        "calmest_value": min(stress_values),
        "total_readings": len(stress_values),
    }


def prepare_chart_data(stress_timeline: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Prepare data for stress timeline chart."""
    if not stress_timeline:
        return {"labels": [], "stress": [], "calm_signal": []}

    labels = []
    stress_data = []
    calm_signal_data = []

    for i, entry in enumerate(stress_timeline):
        stress_level = entry.get("stress_level")
        if (
            not isinstance(stress_level, (int, float))
            or isinstance(stress_level, bool)
            or not 0 <= float(stress_level) <= 1
        ):
            continue
        timestamp = entry.get("timestamp", i * 5)
        if timestamp < 60:
            labels.append(f"{timestamp}s")
        else:
            labels.append(f"{timestamp // 60}m {timestamp % 60}s")
        stress_data.append(round(stress_level * 100, 1))
        calm_signal_data.append(round((1 - stress_level) * 100, 1))

    return {"labels": labels, "stress": stress_data, "calm_signal": calm_signal_data}


# ============================================================================
# TTS Integration (Browser-based)
# ============================================================================


def get_tts_script() -> str:
    """Return JavaScript code for browser-based TTS."""
    return """
    <script>
    function speakText(text) {
        if ('speechSynthesis' in window) {
            // Cancel any ongoing speech
            window.speechSynthesis.cancel();
            
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 0.9;
            utterance.pitch = 1.0;
            utterance.volume = 1.0;
            
            // Try to use a professional voice
            const voices = window.speechSynthesis.getVoices();
            const preferredVoice = voices.find(v => 
                v.name.includes('Google') || 
                v.name.includes('Microsoft') ||
                v.name.includes('Samantha')
            );
            if (preferredVoice) {
                utterance.voice = preferredVoice;
            }
            
            window.speechSynthesis.speak(utterance);
        }
    }
    
    // Load voices
    if ('speechSynthesis' in window) {
        speechSynthesis.getVoices();
    }
    </script>
    """


# ============================================================================
# Model Inference Helper (for TensorFlow.js in browser)
# ============================================================================


def get_emotion_model_config() -> Dict[str, Any]:
    """Return configuration for the emotion detection model."""
    return {
        "model_name": "VivaDefense_FaceSensor",
        "input_shape": [48, 48, 1],  # Grayscale 48x48
        "output": "estimated_stress_signal",
        "model_url": "app/static/emotion_model/model.json",
        "preprocessing": {
            "resize": [48, 48],
            "grayscale": True,
            "normalize": True,  # Divide by 255
            "face_detection": True,  # Detect face first, then crop
        },
        "thresholds": {"calm": 0.4, "stressed": 0.6},
        "disclaimer": "Experimental practice signal, not candidate confidence.",
    }
