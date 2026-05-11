"""
followup_questions.py
=====================

HireSense AI - AI Follow-up Questions Module

Provides intelligent follow-up question generation based on:
- Candidate's previous answers
- Depth of response analysis
- Gap identification in answers
- Probing for more details
- Clarification requests
"""

from __future__ import annotations

import os
from typing import Dict, Any, Optional, List, Iterator
from langchain_openai import ChatOpenAI
from pydantic import Field, SecretStr
from langchain_core.utils.utils import secret_from_env


# ============================================================================
# OpenRouter Integration
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
# Follow-up Question Types
# ============================================================================

FOLLOWUP_TYPES = {
    "clarification": {
        "name": "Clarification",
        "icon": "🔍",
        "description": "Ask for more details or explanation",
        "prompt_modifier": "Ask a clarifying question to better understand the candidate's answer. Focus on unclear or vague parts."
    },
    "depth": {
        "name": "Go Deeper",
        "icon": "⬇️",
        "description": "Probe for deeper technical or behavioral details",
        "prompt_modifier": "Ask a follow-up that goes deeper into the technical or behavioral aspects. Challenge the candidate to provide more specific details."
    },
    "alternative": {
        "name": "Alternative Scenario",
        "icon": "🔄",
        "description": "Present an alternative scenario or constraint",
        "prompt_modifier": "Present an alternative scenario or add a constraint to the original question. See how the candidate adapts their approach."
    },
    "impact": {
        "name": "Impact & Results",
        "icon": "📊",
        "description": "Ask about outcomes and measurable impact",
        "prompt_modifier": "Ask about the specific outcomes, metrics, or impact of what the candidate described. Focus on quantifiable results."
    },
    "challenge": {
        "name": "Challenge",
        "icon": "⚡",
        "description": "Challenge assumptions or push back on the answer",
        "prompt_modifier": "Respectfully challenge an assumption or aspect of the candidate's answer. Test their ability to defend their position or adapt."
    },
    "learning": {
        "name": "Learning & Growth",
        "icon": "📚",
        "description": "Ask about lessons learned or what they'd do differently",
        "prompt_modifier": "Ask what the candidate learned from the experience or what they would do differently with hindsight."
    }
}


# ============================================================================
# Answer Analysis
# ============================================================================

def analyze_answer_for_followup(
    question: str,
    answer: str,
    *,
    model_name: str = "google/gemini-2.0-flash-001",
    temperature: float = 0.3,
) -> Dict[str, Any]:
    """
    Analyze the candidate's answer to determine the best follow-up approach.
    
    Returns:
        Dict with analysis including:
        - completeness_score (0-100)
        - depth_score (0-100)
        - suggested_followup_types
        - gaps_identified
        - strengths_noted
    """
    llm = ChatOpenRouter(
        model_name=model_name,
        temperature=temperature,
        streaming=False
    )
    
    system_prompt = """You are an expert interview coach analyzing candidate responses.
Analyze the answer and provide a JSON response with:
{
    "completeness_score": <0-100, how complete is the answer>,
    "depth_score": <0-100, how deep/detailed is the answer>,
    "clarity_score": <0-100, how clear and well-structured>,
    "suggested_followup_types": [<list of recommended followup types from: clarification, depth, alternative, impact, challenge, learning>],
    "gaps_identified": [<list of gaps or missing elements in the answer>],
    "strengths_noted": [<list of strong points in the answer>],
    "key_points_mentioned": [<list of key points the candidate made>],
    "areas_to_probe": [<specific areas worth exploring further>]
}

Be objective and constructive in your analysis."""

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"""Analyze this interview exchange:

QUESTION: {question}

CANDIDATE'S ANSWER: {answer}

Provide your analysis as JSON."""
        }
    ]
    
    try:
        response = llm.invoke(messages)
        content = response.content
        
        # Parse JSON from response
        import json
        import re
        
        # Try to extract JSON from the response
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            analysis = json.loads(json_match.group())
            return analysis
    except Exception as e:
        print(f"Analysis error: {e}")
    
    # Return default analysis on error
    return {
        "completeness_score": 50,
        "depth_score": 50,
        "clarity_score": 50,
        "suggested_followup_types": ["depth", "clarification"],
        "gaps_identified": [],
        "strengths_noted": [],
        "key_points_mentioned": [],
        "areas_to_probe": []
    }


# ============================================================================
# Follow-up Question Generation
# ============================================================================

def generate_followup_question(
    original_question: str,
    candidate_answer: str,
    followup_type: str = "depth",
    rag_context: str = "",
    interview_type: str = "Mixed",
    emotional_state: str = "neutral",
    language: str = "en",
    *,
    model_name: str = "google/gemini-2.0-flash-001",
    temperature: float = 0.7,
) -> Iterator[str]:
    """
    Generate an intelligent follow-up question based on the candidate's answer.
    
    Args:
        original_question: The question that was asked
        candidate_answer: The candidate's response
        followup_type: Type of follow-up (clarification, depth, alternative, etc.)
        rag_context: Resume and JD context
        interview_type: Technical/Behavioral/HR/etc.
        emotional_state: stressed/confident/neutral
        language: Language code for the interview
    
    Yields:
        Tokens for streaming display
    """
    llm = ChatOpenRouter(
        model_name=model_name,
        temperature=temperature,
        streaming=True
    )
    
    followup_info = FOLLOWUP_TYPES.get(followup_type, FOLLOWUP_TYPES["depth"])
    
    # Adjust tone based on emotional state
    tone_modifier = ""
    if emotional_state == "stressed":
        tone_modifier = "Be warm and encouraging in your follow-up. Make it feel like a conversation, not an interrogation."
    elif emotional_state == "confident":
        tone_modifier = "You can be more challenging and probing since the candidate seems confident."
    
    # Language instruction
    lang_instruction = ""
    if language != "en":
        from language_support import SUPPORTED_LANGUAGES
        lang_info = SUPPORTED_LANGUAGES.get(language, {})
        lang_name = lang_info.get("name", "English")
        lang_instruction = f"\n\nIMPORTANT: Ask the follow-up question in {lang_name}."
    
    system_prompt = f"""You are HireSense AI, an expert interviewer conducting a {interview_type} interview.
You need to ask a follow-up question based on the candidate's previous answer.

FOLLOW-UP TYPE: {followup_info['name']}
{followup_info['prompt_modifier']}

{tone_modifier}

Guidelines:
1. Reference specific parts of the candidate's answer
2. Make the follow-up feel natural and conversational
3. Don't repeat information already provided
4. Keep the question focused and clear
5. One question at a time
{lang_instruction}"""

    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # Add context if available
    if rag_context:
        messages.append({
            "role": "user",
            "content": f"Candidate background:\n{rag_context[:1500]}"
        })
    
    messages.append({
        "role": "user",
        "content": f"""Based on this exchange, generate a {followup_info['name'].lower()} follow-up question:

ORIGINAL QUESTION: {original_question}

CANDIDATE'S ANSWER: {candidate_answer}

Generate a natural follow-up question:"""
    })
    
    for chunk in llm.stream(messages):
        if hasattr(chunk, 'content'):
            yield chunk.content


def generate_smart_followup(
    original_question: str,
    candidate_answer: str,
    rag_context: str = "",
    interview_type: str = "Mixed",
    emotional_state: str = "neutral",
    language: str = "en",
    *,
    model_name: str = "google/gemini-2.0-flash-001",
    temperature: float = 0.7,
) -> Iterator[str]:
    """
    Automatically analyze the answer and generate the most appropriate follow-up.
    
    This function first analyzes the answer to determine the best follow-up type,
    then generates the follow-up question.
    """
    # First, analyze the answer
    analysis = analyze_answer_for_followup(original_question, candidate_answer)
    
    # Determine best follow-up type based on analysis
    suggested_types = analysis.get("suggested_followup_types", ["depth"])
    
    # Select the most appropriate type
    if analysis.get("completeness_score", 50) < 40:
        followup_type = "clarification"
    elif analysis.get("depth_score", 50) < 40:
        followup_type = "depth"
    elif "impact" in suggested_types and analysis.get("depth_score", 50) > 60:
        followup_type = "impact"
    elif suggested_types:
        followup_type = suggested_types[0]
    else:
        followup_type = "depth"
    
    # Generate the follow-up
    yield from generate_followup_question(
        original_question=original_question,
        candidate_answer=candidate_answer,
        followup_type=followup_type,
        rag_context=rag_context,
        interview_type=interview_type,
        emotional_state=emotional_state,
        language=language,
        model_name=model_name,
        temperature=temperature
    )


# ============================================================================
# Follow-up Decision Logic
# ============================================================================

def should_ask_followup(
    answer: str,
    question_number: int,
    total_questions: int,
    time_elapsed_seconds: float,
    max_followups_per_question: int = 2,
    current_followups: int = 0
) -> Dict[str, Any]:
    """
    Determine whether to ask a follow-up question based on various factors.
    
    Returns:
        Dict with:
        - should_followup: bool
        - reason: str
        - suggested_type: str (if should_followup is True)
    """
    # Don't ask follow-ups if we've hit the limit
    if current_followups >= max_followups_per_question:
        return {
            "should_followup": False,
            "reason": "Maximum follow-ups reached for this question"
        }
    
    # Don't ask follow-ups on very short answers (likely skipped or minimal)
    if len(answer.split()) < 10:
        return {
            "should_followup": False,
            "reason": "Answer too brief for meaningful follow-up"
        }
    
    # Consider time constraints - if running long, skip follow-ups
    avg_time_per_question = 180  # 3 minutes expected per question
    expected_time = question_number * avg_time_per_question
    if time_elapsed_seconds > expected_time * 1.5:
        return {
            "should_followup": False,
            "reason": "Interview running long, proceeding to next question"
        }
    
    # For last question, always allow follow-up for closure
    if question_number == total_questions:
        return {
            "should_followup": True,
            "reason": "Final question - opportunity for deeper exploration",
            "suggested_type": "learning"
        }
    
    # Default: allow follow-up
    return {
        "should_followup": True,
        "reason": "Good opportunity for follow-up",
        "suggested_type": "depth"
    }


# ============================================================================
# Follow-up UI Helpers
# ============================================================================

def get_followup_type_buttons() -> List[Dict]:
    """Get list of follow-up type options for UI buttons."""
    return [
        {
            "type": key,
            "name": info["name"],
            "icon": info["icon"],
            "description": info["description"]
        }
        for key, info in FOLLOWUP_TYPES.items()
    ]


def format_analysis_for_display(analysis: Dict) -> str:
    """Format the answer analysis for display in the UI."""
    completeness = analysis.get("completeness_score", 50)
    depth = analysis.get("depth_score", 50)
    clarity = analysis.get("clarity_score", 50)
    
    # Create visual bars
    def score_bar(score):
        filled = int(score / 10)
        empty = 10 - filled
        return "█" * filled + "░" * empty
    
    output = f"""
**Answer Analysis**

| Metric | Score | |
|--------|-------|---|
| Completeness | {completeness}% | {score_bar(completeness)} |
| Depth | {depth}% | {score_bar(depth)} |
| Clarity | {clarity}% | {score_bar(clarity)} |

"""
    
    strengths = analysis.get("strengths_noted", [])
    if strengths:
        output += "**Strengths:** " + ", ".join(strengths[:3]) + "\n\n"
    
    gaps = analysis.get("gaps_identified", [])
    if gaps:
        output += "**Areas to Explore:** " + ", ".join(gaps[:3]) + "\n"
    
    return output


# ============================================================================
# Conversation Flow Management
# ============================================================================

class FollowupManager:
    """Manages follow-up questions within an interview session."""
    
    def __init__(self, max_followups_per_question: int = 2):
        self.max_followups = max_followups_per_question
        self.followup_counts = {}  # question_num -> count
        self.followup_history = []  # List of all follow-ups asked
    
    def record_followup(self, question_num: int, followup_type: str, question_text: str):
        """Record that a follow-up was asked."""
        if question_num not in self.followup_counts:
            self.followup_counts[question_num] = 0
        self.followup_counts[question_num] += 1
        
        self.followup_history.append({
            "question_num": question_num,
            "followup_type": followup_type,
            "question_text": question_text
        })
    
    def can_ask_followup(self, question_num: int) -> bool:
        """Check if more follow-ups can be asked for this question."""
        current_count = self.followup_counts.get(question_num, 0)
        return current_count < self.max_followups
    
    def get_followup_count(self, question_num: int) -> int:
        """Get the number of follow-ups asked for a question."""
        return self.followup_counts.get(question_num, 0)
    
    def get_total_followups(self) -> int:
        """Get total number of follow-ups asked in the session."""
        return len(self.followup_history)
    
    def reset(self):
        """Reset the manager for a new session."""
        self.followup_counts = {}
        self.followup_history = []
