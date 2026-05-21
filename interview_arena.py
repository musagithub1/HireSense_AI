"""
interview_arena.py
==================

HireSense AI - Interview Arena Module

Features:
1. RAG Integration - Resume/JD personalization
2. Real-Time Emotion Detection - Webcam analysis
3. Adaptive AI - Supportive when stressed, challenging when confident
4. TTS Audio - Questions spoken aloud
5. Analytics Dashboard - Stress graphs and composure scores

Tech Stack: OpenRouter.ai for LLM, TensorFlow.js for client-side model inference
"""

from __future__ import annotations

# Load .env file first
try:
    import config  # This loads the .env file
except ImportError:
    pass  # config module may not be available in standalone usage

import os
import json
import base64
import time
from io import BytesIO
from typing import Dict, Any, Optional, List, Tuple, Iterator
from datetime import datetime
import re

from langchain_openai import ChatOpenAI
from pydantic import Field, SecretStr
from langchain_core.utils.utils import secret_from_env

try:
    from pypdf import PdfReader
except ImportError:
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        try:
            from PyPDF3 import PdfReader
        except ImportError:
            try:
                from PyPDF4 import PdfReader
            except ImportError:
                PdfReader = None


# ============================================================================
# OpenRouter Integration (Same as V4)
# ============================================================================

class ChatOpenRouter(ChatOpenAI):
    """OpenRouter API wrapper with streaming support."""

    openai_api_key: Optional[SecretStr] = Field(
        alias="api_key", default_factory=secret_from_env("OPENROUTER_API_KEY", default=None)
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

        super().__init__(
            base_url="https://openrouter.ai/api/v1",
            openai_api_key=openai_api_key,
            **kwargs,
        )


# ============================================================================
# RAG System - Resume/JD Processing
# ============================================================================

def extract_pdf_text(file_data: bytes) -> str:
    """Extract all text from a PDF given its binary data."""
    if PdfReader is None:
        raise ImportError("No PDF parser library (pypdf or PyPDF2) is available in the environment. Please ensure pypdf is installed.")
    
    reader = PdfReader(BytesIO(file_data))
    text: list[str] = []
    for page in reader.pages:
        try:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
        except Exception:
            continue
    return "\n\n".join(text)


def parse_resume(resume_text: str) -> Dict[str, Any]:
    """Parse resume text to extract key information for RAG."""
    return {
        "raw_text": resume_text,
        "word_count": len(resume_text.split()),
        "extracted_at": datetime.now().isoformat()
    }


def parse_job_description(jd_text: str) -> Dict[str, Any]:
    """Parse job description to extract requirements."""
    return {
        "raw_text": jd_text,
        "word_count": len(jd_text.split()),
        "extracted_at": datetime.now().isoformat()
    }


def build_rag_context(resume_data: Dict, jd_data: Dict) -> str:
    """Build RAG context from resume and job description."""
    context = f"""
=== CANDIDATE RESUME ===
{resume_data.get('raw_text', 'No resume provided')}

=== JOB DESCRIPTION ===
{jd_data.get('raw_text', 'No job description provided')}
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
- Culture fit and motivation"""
}


# ============================================================================
# Adaptive Interview AI
# ============================================================================

INTERVIEW_SYSTEM_PROMPT_SUPPORTIVE = """You are HireSense AI, a supportive and encouraging AI interviewer.
The candidate appears to be nervous or stressed. Your role is to:
1. Ask questions in a warm, friendly manner
2. Provide encouragement and positive reinforcement
3. Give the candidate time to think
4. Offer hints if they struggle
5. Focus on building their confidence

Use the provided resume and job description to ask relevant, personalized questions.
Keep questions clear and not overly complex. Be patient and understanding."""

INTERVIEW_SYSTEM_PROMPT_CHALLENGING = """You are HireSense AI, a rigorous and challenging AI interviewer.
The candidate appears confident and composed. Your role is to:
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
    if emotional_state == "stressed":
        return INTERVIEW_SYSTEM_PROMPT_SUPPORTIVE
    elif emotional_state == "confident":
        return INTERVIEW_SYSTEM_PROMPT_CHALLENGING
    else:
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
    model_name: str = "google/gemini-2.0-flash-001",
    temperature: float = 0.7,
) -> Iterator[Dict[str, Any]]:
    """
    Generate an interview question using the Antigravity 5-Agent Pipeline.
    
    Pipeline: ContentAgent → InsightAgent → ImpactAgent → StrategyAgent → ExecutionAgent
    
    On the first question, all 5 agents run.
    On subsequent questions, Content + Insight are cached (resume doesn't change),
    but Impact + Strategy + Execution re-run (emotion may have changed).
    
    Yields intermediate trace events and final question chunks as dicts.
    """
    try:
        from antigravity_agent import get_orchestrator
    except ImportError as e:
        raise ImportError(f"antigravity_agent module error: {e}")

    orchestrator = get_orchestrator(model_name=model_name, temperature=temperature)
    
    # Run the full 5-agent pipeline
    for step in orchestrator.run_pipeline(
        rag_context=rag_context,
        conversation_history=conversation_history,
        emotional_state=emotional_state,
        question_number=question_number,
        total_questions=total_questions,
        interview_type=interview_type,
        company=company,
    ):
        yield step


def evaluate_answer(
    rag_context: str,
    question: str,
    answer: str,
    emotional_state: str = "neutral",
    *,
    model_name: str = "google/gemini-2.0-flash-001",
    temperature: float = 0.3,
) -> Iterator[str]:
    """
    Evaluate the candidate's answer and provide feedback.
    
    Yields tokens for streaming display.
    """
    llm = ChatOpenRouter(
        model_name=model_name,
        temperature=temperature,
        streaming=True
    )
    
    tone = "encouraging and supportive" if emotional_state == "stressed" else "constructive and direct"
    
    system_prompt = f"""You are an expert AI interview evaluator. Evaluate the candidate's answer.
Be {tone} in your feedback. Provide:
1. A brief assessment of the answer quality (1-2 sentences)
2. Key strengths identified
3. Areas for improvement (if any)
4. A score from 1-10

Keep your response concise and actionable."""

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"""Context about the candidate:
{rag_context[:2000]}

Question asked: {question}

Candidate's answer: {answer}

Please evaluate this answer."""
        }
    ]
    
    for chunk in llm.stream(messages):
        if hasattr(chunk, 'content'):
            yield chunk.content


def generate_final_report(
    rag_context: str,
    conversation_history: List[Dict[str, str]],
    stress_timeline: List[Dict[str, Any]],
    *,
    model_name: str = "google/gemini-2.0-flash-001",
    temperature: float = 0.3,
) -> Iterator[str]:
    """
    Generate a comprehensive interview report card.
    
    Yields tokens for streaming display.
    """
    llm = ChatOpenRouter(
        model_name=model_name,
        temperature=temperature,
        streaming=True
    )
    
    # Calculate stress statistics
    if stress_timeline:
        stress_values = [entry.get("stress_level", 0.5) for entry in stress_timeline]
        avg_stress = sum(stress_values) / len(stress_values)
        max_stress = max(stress_values)
        min_stress = min(stress_values)
        composure_score = (1 - avg_stress) * 100
    else:
        avg_stress = 0.5
        max_stress = 0.5
        min_stress = 0.5
        composure_score = 50
    
    # Format conversation for analysis
    conversation_text = ""
    for entry in conversation_history:
        role = "HireSense AI" if entry["role"] == "assistant" else "Candidate"
        conversation_text += f"{role}: {entry['content']}\n\n"
    
    system_prompt = """You are HireSense AI's expert interview analyst. Generate a comprehensive HireSense Report.
Include:
1. Overall Performance Summary
2. Technical Competency Assessment
3. Communication Skills Evaluation
4. Composure and Stress Management Analysis
5. Strengths Demonstrated
6. Areas for Improvement
7. Final Recommendation (Hire/Consider/Pass)
8. Personalized Tips for Future Interviews

Be thorough but concise. Use markdown formatting."""

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"""Generate an interview report card based on:

=== CANDIDATE BACKGROUND ===
{rag_context[:1500]}

=== INTERVIEW TRANSCRIPT ===
{conversation_text[:3000]}

=== STRESS ANALYTICS ===
- Average Stress Level: {avg_stress:.2%}
- Peak Stress: {max_stress:.2%}
- Lowest Stress: {min_stress:.2%}
- Composure Score: {composure_score:.1f}/100

Please generate a detailed report card."""
        }
    ]
    
    for chunk in llm.stream(messages):
        if hasattr(chunk, 'content'):
            yield chunk.content


# ============================================================================
# Analytics & Visualization Data
# ============================================================================

def calculate_composure_metrics(stress_timeline: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate composure metrics from stress timeline."""
    if not stress_timeline:
        return {
            "average_stress": 0.5,
            "composure_score": 50,
            "stress_variance": 0,
            "recovery_rate": 0,
            "peak_stress_time": None,
            "calmest_moment": None
        }
    
    stress_values = [entry.get("stress_level", 0.5) for entry in stress_timeline]
    timestamps = [entry.get("timestamp", 0) for entry in stress_timeline]
    
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
        if stress_values[i] < stress_values[i-1]:
            recovery_events.append(stress_values[i-1] - stress_values[i])
    
    recovery_rate = sum(recovery_events) / len(recovery_events) if recovery_events else 0
    
    return {
        "average_stress": avg_stress,
        "composure_score": composure_score,
        "stress_variance": variance,
        "recovery_rate": recovery_rate,
        "peak_stress_time": timestamps[max_idx] if timestamps else None,
        "peak_stress_value": max(stress_values),
        "calmest_moment": timestamps[min_idx] if timestamps else None,
        "calmest_value": min(stress_values),
        "total_readings": len(stress_values)
    }


def prepare_chart_data(stress_timeline: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Prepare data for stress timeline chart."""
    if not stress_timeline:
        return {"labels": [], "stress": [], "confidence": []}
    
    labels = []
    stress_data = []
    confidence_data = []
    
    for i, entry in enumerate(stress_timeline):
        # Create time labels (in seconds or minutes)
        timestamp = entry.get("timestamp", i * 5)
        if timestamp < 60:
            labels.append(f"{timestamp}s")
        else:
            labels.append(f"{timestamp // 60}m {timestamp % 60}s")
        
        stress_level = entry.get("stress_level", 0.5)
        stress_data.append(round(stress_level * 100, 1))
        confidence_data.append(round((1 - stress_level) * 100, 1))
    
    return {
        "labels": labels,
        "stress": stress_data,
        "confidence": confidence_data
    }


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
        "output_classes": ["Confident", "Stressed"],  # sigmoid: 0 = Confident, 1 = Stressed
        "preprocessing": {
            "resize": [48, 48],
            "grayscale": True,
            "normalize": True,  # Divide by 255
            "face_detection": True  # Detect face first, then crop
        },
        "threshold": 0.5  # Above 0.5 = Stressed, Below 0.5 = Confident
    }


def get_tfjs_inference_script() -> str:
    """Return JavaScript code for TensorFlow.js model inference."""
    return """
    <script src="https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@4.17.0/dist/tf.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/@mediapipe/face_detection/face_detection.js"></script>
    <script>
    let emotionModel = null;
    let faceDetector = null;
    
    async function loadEmotionModel(modelPath) {
        try {
            emotionModel = await tf.loadLayersModel(modelPath);
            console.log('Emotion model loaded successfully');
            return true;
        } catch (error) {
            console.error('Failed to load emotion model:', error);
            return false;
        }
    }
    
    async function preprocessFrame(imageData, targetSize = [48, 48]) {
        // Convert to tensor
        let tensor = tf.browser.fromPixels(imageData, 1); // Grayscale
        
        // Resize
        tensor = tf.image.resizeBilinear(tensor, targetSize);
        
        // Normalize to [0, 1]
        tensor = tensor.div(255.0);
        
        // Add batch dimension
        tensor = tensor.expandDims(0);
        
        return tensor;
    }
    
    async function detectEmotion(imageData) {
        if (!emotionModel) {
            console.warn('Model not loaded');
            return { stress_level: 0.5, state: 'unknown' };
        }
        
        try {
            const tensor = await preprocessFrame(imageData);
            const prediction = await emotionModel.predict(tensor);
            const stressLevel = (await prediction.data())[0];
            
            // Cleanup
            tensor.dispose();
            prediction.dispose();
            
            return {
                stress_level: stressLevel,
                state: stressLevel > 0.5 ? 'stressed' : 'confident',
                confidence: Math.abs(stressLevel - 0.5) * 2
            };
        } catch (error) {
            console.error('Emotion detection error:', error);
            return { stress_level: 0.5, state: 'unknown' };
        }
    }
    </script>
    """
