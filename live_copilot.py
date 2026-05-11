"""
live_copilot.py
===============

HireSense AI - Live Interview Copilot Module

Provides real-time, on-screen assistance during actual interviews:
- Real-time speech transcription
- Smart answer suggestions based on resume and job description
- STAR method response structuring
- Key points reminder from resume
- Confidence boosting prompts
- Interview question detection and categorization
"""

from __future__ import annotations

import os
import json
import re
from typing import Dict, Any, Optional, List, Iterator, Tuple
from dataclasses import dataclass
from datetime import datetime
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
# Copilot Data Classes
# ============================================================================

@dataclass
class CopilotSuggestion:
    """Represents a suggestion from the copilot."""
    suggestion_type: str  # talking_point, star_structure, key_skill, confidence_boost
    content: str
    priority: str  # high, medium, low
    related_question: Optional[str] = None
    timestamp: Optional[str] = None


@dataclass
class DetectedQuestion:
    """Represents a detected interview question."""
    question_text: str
    question_type: str  # technical, behavioral, hr, situational
    keywords: List[str]
    detected_at: str


@dataclass
class CopilotSession:
    """Represents a copilot session state."""
    session_id: str
    resume_context: str
    jd_context: str
    detected_questions: List[DetectedQuestion]
    suggestions_history: List[CopilotSuggestion]
    transcript: List[Dict[str, str]]
    started_at: str
    is_active: bool = True


# ============================================================================
# Question Detection
# ============================================================================

QUESTION_PATTERNS = {
    "behavioral": [
        r"tell me about a time",
        r"describe a situation",
        r"give me an example",
        r"how did you handle",
        r"what would you do if",
        r"have you ever",
        r"share an experience",
        r"walk me through",
    ],
    "technical": [
        r"how would you implement",
        r"what is the difference between",
        r"explain how .* works",
        r"design a system",
        r"write a function",
        r"what data structure",
        r"time complexity",
        r"optimize",
        r"debug",
        r"architecture",
    ],
    "hr": [
        r"why do you want",
        r"where do you see yourself",
        r"what are your strengths",
        r"what are your weaknesses",
        r"salary expectations",
        r"why should we hire",
        r"tell me about yourself",
        r"why are you leaving",
    ],
    "situational": [
        r"what if",
        r"imagine that",
        r"suppose",
        r"how would you approach",
        r"if you were",
    ]
}


def detect_question_type(text: str) -> Tuple[bool, str, List[str]]:
    """
    Detect if text contains an interview question and categorize it.
    
    Returns:
        Tuple of (is_question, question_type, matched_keywords)
    """
    text_lower = text.lower()
    
    # Check if it's a question (ends with ? or contains question patterns)
    is_question = "?" in text or any(
        re.search(pattern, text_lower) 
        for patterns in QUESTION_PATTERNS.values() 
        for pattern in patterns
    )
    
    if not is_question:
        return False, "", []
    
    # Categorize the question
    matched_keywords = []
    question_type = "general"
    max_matches = 0
    
    for q_type, patterns in QUESTION_PATTERNS.items():
        matches = [p for p in patterns if re.search(p, text_lower)]
        if len(matches) > max_matches:
            max_matches = len(matches)
            question_type = q_type
            matched_keywords = matches
    
    return True, question_type, matched_keywords


# ============================================================================
# Smart Suggestion Generation
# ============================================================================

def generate_smart_suggestion(
    question: str,
    question_type: str,
    resume_context: str,
    jd_context: str,
    conversation_history: List[Dict[str, str]] = None,
    *,
    model_name: str = "google/gemini-2.0-flash-001",
    temperature: float = 0.4,
) -> Iterator[str]:
    """
    Generate smart suggestions for answering an interview question.
    
    Yields tokens for streaming display.
    """
    llm = ChatOpenRouter(
        model_name=model_name,
        temperature=temperature,
        streaming=True
    )
    
    system_prompt = f"""You are a real-time interview copilot assistant. Your job is to help the candidate answer interview questions effectively during a LIVE interview.

CRITICAL RULES:
1. Be CONCISE - the candidate needs to read this quickly during the interview
2. Provide BULLET POINTS, not paragraphs
3. Focus on KEY TALKING POINTS they can expand on verbally
4. Include relevant METRICS and EXAMPLES from their resume
5. For behavioral questions, use STAR format (Situation, Task, Action, Result)

Question Type: {question_type.upper()}

CANDIDATE'S RESUME:
{resume_context[:2000]}

JOB DESCRIPTION:
{jd_context[:1500]}
"""

    if question_type == "behavioral":
        user_prompt = f"""The interviewer just asked: "{question}"

Provide a STAR-structured response outline:
• S (Situation): [1 sentence setup]
• T (Task): [What was your responsibility]
• A (Action): [2-3 key actions you took]
• R (Result): [Quantifiable outcome if possible]

Also suggest 1-2 relevant experiences from the resume to mention."""

    elif question_type == "technical":
        user_prompt = f"""The interviewer just asked: "{question}"

Provide:
• KEY CONCEPTS to mention (3-4 bullet points)
• APPROACH outline (step-by-step)
• RELEVANT EXPERIENCE from resume to reference
• Any EDGE CASES or considerations to mention"""

    elif question_type == "hr":
        user_prompt = f"""The interviewer just asked: "{question}"

Provide:
• MAIN POINTS to cover (3-4 bullets)
• How to CONNECT your answer to this specific role/company
• AUTHENTIC examples from your background
• What NOT to say (brief warning if applicable)"""

    else:
        user_prompt = f"""The interviewer just asked: "{question}"

Provide:
• KEY TALKING POINTS (3-4 bullets)
• RELEVANT EXPERIENCE to mention
• How to structure your response
• Strong CLOSING statement"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    # Add conversation context if available
    if conversation_history:
        context_msg = "Recent conversation context:\n"
        for entry in conversation_history[-4:]:
            context_msg += f"- {entry.get('role', 'unknown')}: {entry.get('content', '')[:100]}...\n"
        messages.insert(1, {"role": "user", "content": context_msg})
    
    for chunk in llm.stream(messages):
        if hasattr(chunk, 'content'):
            yield chunk.content


def generate_confidence_boost(
    emotional_state: str = "neutral",
    *,
    model_name: str = "google/gemini-2.0-flash-001",
) -> str:
    """Generate a quick confidence-boosting message based on emotional state."""
    
    boosts = {
        "stressed": [
            "💪 Take a breath. You've prepared for this. Trust your experience.",
            "🌟 Remember: They invited YOU. They see your potential.",
            "✨ Pause is powerful. Take a moment to think - it shows confidence.",
            "🎯 Focus on one point at a time. You've got this!",
        ],
        "nervous": [
            "😊 Nerves mean you care. Channel that energy positively!",
            "🔥 You're doing great. Keep going!",
            "💡 Remember your achievements. You earned this interview.",
            "🚀 Every answer is a chance to shine. Take it!",
        ],
        "confident": [
            "⭐ Great energy! Keep that momentum going.",
            "🎯 You're in the zone. Stay focused and authentic.",
            "💪 Strong presence! Remember to also listen actively.",
            "✨ Excellent! Don't forget to ask thoughtful questions too.",
        ],
        "neutral": [
            "👍 You're doing well. Stay engaged and present.",
            "🎯 Good pace. Remember to show enthusiasm for the role.",
            "💡 Connect your answers to the job requirements.",
            "🌟 Be yourself - authenticity wins interviews.",
        ]
    }
    
    import random
    messages = boosts.get(emotional_state, boosts["neutral"])
    return random.choice(messages)


def extract_key_resume_points(
    resume_text: str,
    job_description: str,
    *,
    model_name: str = "google/gemini-2.0-flash-001",
    temperature: float = 0.2,
) -> Dict[str, Any]:
    """
    Extract key points from resume that are most relevant to the job.
    Returns a structured summary for quick reference during interview.
    """
    llm = ChatOpenRouter(
        model_name=model_name,
        temperature=temperature,
        streaming=False
    )
    
    system_prompt = """Extract the most important points from this resume that are relevant to the job description.
Format as JSON for quick reference during an interview:
{
    "key_achievements": ["achievement 1 with metric", "achievement 2 with metric"],
    "relevant_skills": ["skill 1", "skill 2", "skill 3"],
    "experience_highlights": ["highlight 1", "highlight 2"],
    "unique_value_props": ["what makes this candidate stand out"],
    "numbers_to_remember": ["$X revenue", "Y% improvement", "Z team members"],
    "projects_to_mention": ["project 1 - brief description", "project 2 - brief description"]
}"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"RESUME:\n{resume_text[:3000]}\n\nJOB DESCRIPTION:\n{job_description[:1500]}"}
    ]
    
    try:
        response = llm.invoke(messages)
        content = response.content
        
        # Extract JSON
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"Key points extraction error: {e}")
    
    return {
        "key_achievements": [],
        "relevant_skills": [],
        "experience_highlights": [],
        "unique_value_props": [],
        "numbers_to_remember": [],
        "projects_to_mention": []
    }


# ============================================================================
# Copilot Component HTML/JS
# ============================================================================

def get_copilot_component_html(
    resume_context: str = "",
    jd_context: str = "",
    key_points: Dict[str, Any] = None,
    session_id: str = "default"
) -> str:
    """
    Generate HTML/JS code for the live interview copilot component.
    
    Features:
    - Real-time speech-to-text transcription
    - Question detection
    - Smart suggestion display
    - Quick reference panel
    - Confidence boosters
    """
    
    key_points_json = json.dumps(key_points or {})
    
    return f'''
<!DOCTYPE html>
<html>
<head>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        .copilot-container {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-radius: 16px;
            padding: 20px;
            color: white;
            max-height: 600px;
            overflow-y: auto;
        }}
        
        .copilot-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        
        .copilot-title {{
            font-size: 18px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .copilot-title .icon {{
            font-size: 24px;
        }}
        
        .status-badge {{
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        
        .status-badge.listening {{
            background: rgba(76, 175, 80, 0.2);
            color: #4CAF50;
        }}
        
        .status-badge.processing {{
            background: rgba(255, 193, 7, 0.2);
            color: #FFC107;
        }}
        
        .status-badge.idle {{
            background: rgba(158, 158, 158, 0.2);
            color: #9E9E9E;
        }}
        
        .pulse-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: currentColor;
            animation: pulse 1.5s infinite;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; transform: scale(1); }}
            50% {{ opacity: 0.5; transform: scale(0.8); }}
        }}
        
        .section {{
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 15px;
        }}
        
        .section-title {{
            font-size: 14px;
            font-weight: 600;
            color: #64B5F6;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .transcript-box {{
            background: rgba(0,0,0,0.3);
            border-radius: 8px;
            padding: 12px;
            min-height: 60px;
            max-height: 100px;
            overflow-y: auto;
            font-size: 14px;
            line-height: 1.5;
            color: #E0E0E0;
        }}
        
        .detected-question {{
            background: linear-gradient(135deg, #FF6B6B 0%, #FF8E53 100%);
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 10px;
            font-weight: 500;
        }}
        
        .question-type-badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            background: rgba(255,255,255,0.2);
            margin-bottom: 8px;
            text-transform: uppercase;
        }}
        
        .suggestion-box {{
            background: rgba(76, 175, 80, 0.1);
            border-left: 3px solid #4CAF50;
            border-radius: 0 8px 8px 0;
            padding: 12px;
            margin-bottom: 10px;
        }}
        
        .suggestion-content {{
            font-size: 14px;
            line-height: 1.6;
            white-space: pre-wrap;
        }}
        
        .suggestion-content strong {{
            color: #81C784;
        }}
        
        .key-points-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }}
        
        .key-point-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            padding: 10px;
        }}
        
        .key-point-title {{
            font-size: 11px;
            color: #90CAF9;
            text-transform: uppercase;
            margin-bottom: 6px;
        }}
        
        .key-point-list {{
            font-size: 12px;
            color: #E0E0E0;
        }}
        
        .key-point-list li {{
            margin-bottom: 4px;
            list-style: none;
            padding-left: 12px;
            position: relative;
        }}
        
        .key-point-list li::before {{
            content: "•";
            position: absolute;
            left: 0;
            color: #64B5F6;
        }}
        
        .confidence-boost {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 8px;
            padding: 12px;
            text-align: center;
            font-size: 14px;
            font-weight: 500;
            margin-top: 10px;
        }}
        
        .control-buttons {{
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }}
        
        .control-btn {{
            flex: 1;
            padding: 12px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            transition: all 0.2s;
        }}
        
        .control-btn.primary {{
            background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
            color: white;
        }}
        
        .control-btn.secondary {{
            background: rgba(255,255,255,0.1);
            color: white;
        }}
        
        .control-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }}
        
        .control-btn:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }}
        
        .typing-indicator {{
            display: flex;
            gap: 4px;
            padding: 8px;
        }}
        
        .typing-indicator span {{
            width: 8px;
            height: 8px;
            background: #64B5F6;
            border-radius: 50%;
            animation: typing 1.4s infinite;
        }}
        
        .typing-indicator span:nth-child(2) {{ animation-delay: 0.2s; }}
        .typing-indicator span:nth-child(3) {{ animation-delay: 0.4s; }}
        
        @keyframes typing {{
            0%, 100% {{ transform: translateY(0); }}
            50% {{ transform: translateY(-5px); }}
        }}
        
        .hidden {{
            display: none !important;
        }}
    </style>
</head>
<body>
    <div class="copilot-container">
        <div class="copilot-header">
            <div class="copilot-title">
                <span class="icon">🤖</span>
                <span>Interview Copilot</span>
            </div>
            <div id="status-badge" class="status-badge idle">
                <span class="pulse-dot"></span>
                <span id="status-text">Ready</span>
            </div>
        </div>
        
        <!-- Live Transcript Section -->
        <div class="section">
            <div class="section-title">
                <span>🎤</span>
                <span>Live Transcript</span>
            </div>
            <div id="transcript-box" class="transcript-box">
                Click "Start Listening" to begin real-time transcription...
            </div>
        </div>
        
        <!-- Detected Question Section -->
        <div id="question-section" class="section hidden">
            <div class="section-title">
                <span>❓</span>
                <span>Detected Question</span>
            </div>
            <div id="detected-question" class="detected-question">
                <span id="question-type-badge" class="question-type-badge">BEHAVIORAL</span>
                <div id="question-text"></div>
            </div>
        </div>
        
        <!-- AI Suggestion Section -->
        <div id="suggestion-section" class="section hidden">
            <div class="section-title">
                <span>💡</span>
                <span>Smart Suggestion</span>
            </div>
            <div id="typing-indicator" class="typing-indicator hidden">
                <span></span><span></span><span></span>
            </div>
            <div id="suggestion-box" class="suggestion-box">
                <div id="suggestion-content" class="suggestion-content"></div>
            </div>
        </div>
        
        <!-- Key Points Quick Reference -->
        <div class="section">
            <div class="section-title">
                <span>📋</span>
                <span>Quick Reference</span>
            </div>
            <div class="key-points-grid">
                <div class="key-point-card">
                    <div class="key-point-title">Key Achievements</div>
                    <ul id="achievements-list" class="key-point-list"></ul>
                </div>
                <div class="key-point-card">
                    <div class="key-point-title">Numbers to Remember</div>
                    <ul id="numbers-list" class="key-point-list"></ul>
                </div>
                <div class="key-point-card">
                    <div class="key-point-title">Relevant Skills</div>
                    <ul id="skills-list" class="key-point-list"></ul>
                </div>
                <div class="key-point-card">
                    <div class="key-point-title">Projects to Mention</div>
                    <ul id="projects-list" class="key-point-list"></ul>
                </div>
            </div>
        </div>
        
        <!-- Confidence Boost -->
        <div id="confidence-boost" class="confidence-boost">
            💪 You've prepared for this. Trust your experience!
        </div>
        
        <!-- Control Buttons -->
        <div class="control-buttons">
            <button id="start-btn" class="control-btn primary" onclick="toggleListening()">
                <span>🎙️</span>
                <span>Start Listening</span>
            </button>
            <button id="clear-btn" class="control-btn secondary" onclick="clearTranscript()">
                <span>🗑️</span>
                <span>Clear</span>
            </button>
        </div>
    </div>
    
    <script>
        // Key points data from Python
        const keyPoints = {key_points_json};
        
        // State
        let isListening = false;
        let recognition = null;
        let fullTranscript = '';
        let lastQuestionTime = 0;
        const QUESTION_COOLDOWN = 5000; // 5 seconds between question detections
        
        // Question patterns
        const questionPatterns = {{
            behavioral: [
                /tell me about a time/i,
                /describe a situation/i,
                /give me an example/i,
                /how did you handle/i,
                /what would you do if/i,
                /have you ever/i,
                /share an experience/i,
                /walk me through/i
            ],
            technical: [
                /how would you implement/i,
                /what is the difference between/i,
                /explain how .* works/i,
                /design a system/i,
                /write a function/i,
                /what data structure/i,
                /time complexity/i,
                /optimize/i,
                /debug/i,
                /architecture/i
            ],
            hr: [
                /why do you want/i,
                /where do you see yourself/i,
                /what are your strengths/i,
                /what are your weaknesses/i,
                /salary expectations/i,
                /why should we hire/i,
                /tell me about yourself/i,
                /why are you leaving/i
            ],
            situational: [
                /what if/i,
                /imagine that/i,
                /suppose/i,
                /how would you approach/i,
                /if you were/i
            ]
        }};
        
        // Confidence boost messages
        const confidenceBoosts = [
            "💪 You've prepared for this. Trust your experience!",
            "🌟 Remember: They invited YOU. They see your potential.",
            "✨ Take your time. Thoughtful answers impress more than rushed ones.",
            "🎯 Focus on your achievements. You have great examples!",
            "🚀 You're doing great. Stay confident and authentic!",
            "💡 Connect your answer to what they need. You've got this!"
        ];
        
        // Initialize key points display
        function initKeyPoints() {{
            const lists = {{
                'achievements-list': keyPoints.key_achievements || [],
                'numbers-list': keyPoints.numbers_to_remember || [],
                'skills-list': keyPoints.relevant_skills || [],
                'projects-list': keyPoints.projects_to_mention || []
            }};
            
            for (const [listId, items] of Object.entries(lists)) {{
                const list = document.getElementById(listId);
                if (list && items.length > 0) {{
                    list.innerHTML = items.slice(0, 3).map(item => `<li>${{item}}</li>`).join('');
                }} else if (list) {{
                    list.innerHTML = '<li style="color: #666;">No data yet</li>';
                }}
            }}
        }}
        
        // Detect question type
        function detectQuestion(text) {{
            const now = Date.now();
            if (now - lastQuestionTime < QUESTION_COOLDOWN) return null;
            
            // Check if it contains a question mark or question patterns
            const hasQuestionMark = text.includes('?');
            let detectedType = null;
            
            for (const [type, patterns] of Object.entries(questionPatterns)) {{
                for (const pattern of patterns) {{
                    if (pattern.test(text)) {{
                        detectedType = type;
                        break;
                    }}
                }}
                if (detectedType) break;
            }}
            
            if (hasQuestionMark || detectedType) {{
                lastQuestionTime = now;
                return {{
                    text: text,
                    type: detectedType || 'general'
                }};
            }}
            
            return null;
        }}
        
        // Show detected question
        function showDetectedQuestion(question) {{
            const section = document.getElementById('question-section');
            const badge = document.getElementById('question-type-badge');
            const textEl = document.getElementById('question-text');
            
            badge.textContent = question.type.toUpperCase();
            textEl.textContent = question.text;
            section.classList.remove('hidden');
            
            // Generate suggestion
            generateSuggestion(question);
        }}
        
        // Generate AI suggestion (simulated - in real app, this would call the backend)
        function generateSuggestion(question) {{
            const suggestionSection = document.getElementById('suggestion-section');
            const typingIndicator = document.getElementById('typing-indicator');
            const suggestionBox = document.getElementById('suggestion-box');
            const suggestionContent = document.getElementById('suggestion-content');
            
            suggestionSection.classList.remove('hidden');
            typingIndicator.classList.remove('hidden');
            suggestionBox.classList.add('hidden');
            
            // Simulate AI response (in real implementation, this calls the Python backend)
            setTimeout(() => {{
                typingIndicator.classList.add('hidden');
                suggestionBox.classList.remove('hidden');
                
                let suggestion = '';
                if (question.type === 'behavioral') {{
                    suggestion = `<strong>STAR Structure:</strong>
                    
• <strong>S (Situation):</strong> Set the context briefly
• <strong>T (Task):</strong> What was your responsibility?
• <strong>A (Action):</strong> What specific steps did YOU take?
• <strong>R (Result):</strong> What was the outcome? Use metrics!

<strong>💡 Tip:</strong> Reference a relevant project from your resume.`;
                }} else if (question.type === 'technical') {{
                    suggestion = `<strong>Approach:</strong>

• Start by clarifying requirements
• Discuss your thought process out loud
• Consider edge cases
• Mention relevant experience from your resume

<strong>💡 Tip:</strong> It's okay to think before answering.`;
                }} else if (question.type === 'hr') {{
                    suggestion = `<strong>Key Points:</strong>

• Be authentic and specific
• Connect your answer to this role
• Show enthusiasm for the company
• Highlight your unique value

<strong>💡 Tip:</strong> Research-backed answers impress!`;
                }} else {{
                    suggestion = `<strong>General Tips:</strong>

• Take a moment to structure your thoughts
• Be specific with examples
• Keep it concise but complete
• End with a strong conclusion`;
                }}
                
                suggestionContent.innerHTML = suggestion;
            }}, 1500);
        }}
        
        // Update confidence boost
        function updateConfidenceBoost() {{
            const boost = document.getElementById('confidence-boost');
            const randomBoost = confidenceBoosts[Math.floor(Math.random() * confidenceBoosts.length)];
            boost.textContent = randomBoost;
        }}
        
        // Toggle listening
        function toggleListening() {{
            if (isListening) {{
                stopListening();
            }} else {{
                startListening();
            }}
        }}
        
        // Start listening
        function startListening() {{
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {{
                alert('Speech recognition is not supported in this browser. Please use Chrome or Edge.');
                return;
            }}
            
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'en-US';
            
            recognition.onstart = () => {{
                isListening = true;
                updateStatus('listening', 'Listening...');
                document.getElementById('start-btn').innerHTML = '<span>⏹️</span><span>Stop Listening</span>';
            }};
            
            recognition.onresult = (event) => {{
                let interimTranscript = '';
                let finalTranscript = '';
                
                for (let i = event.resultIndex; i < event.results.length; i++) {{
                    const transcript = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {{
                        finalTranscript += transcript + ' ';
                        
                        // Check for questions in final transcript
                        const question = detectQuestion(transcript);
                        if (question) {{
                            showDetectedQuestion(question);
                            updateConfidenceBoost();
                        }}
                    }} else {{
                        interimTranscript += transcript;
                    }}
                }}
                
                if (finalTranscript) {{
                    fullTranscript += finalTranscript;
                }}
                
                document.getElementById('transcript-box').textContent = 
                    fullTranscript + (interimTranscript ? '...' + interimTranscript : '');
                
                // Auto-scroll transcript
                const transcriptBox = document.getElementById('transcript-box');
                transcriptBox.scrollTop = transcriptBox.scrollHeight;
            }};
            
            recognition.onerror = (event) => {{
                console.error('Speech recognition error:', event.error);
                if (event.error !== 'no-speech') {{
                    updateStatus('idle', 'Error: ' + event.error);
                }}
            }};
            
            recognition.onend = () => {{
                if (isListening) {{
                    // Restart if still supposed to be listening
                    recognition.start();
                }}
            }};
            
            recognition.start();
        }}
        
        // Stop listening
        function stopListening() {{
            isListening = false;
            if (recognition) {{
                recognition.stop();
            }}
            updateStatus('idle', 'Ready');
            document.getElementById('start-btn').innerHTML = '<span>🎙️</span><span>Start Listening</span>';
        }}
        
        // Update status badge
        function updateStatus(status, text) {{
            const badge = document.getElementById('status-badge');
            const statusText = document.getElementById('status-text');
            
            badge.className = 'status-badge ' + status;
            statusText.textContent = text;
        }}
        
        // Clear transcript
        function clearTranscript() {{
            fullTranscript = '';
            document.getElementById('transcript-box').textContent = 'Click "Start Listening" to begin real-time transcription...';
            document.getElementById('question-section').classList.add('hidden');
            document.getElementById('suggestion-section').classList.add('hidden');
        }}
        
        // Send data to Streamlit
        function sendToStreamlit(data) {{
            if (window.parent && window.parent.postMessage) {{
                window.parent.postMessage({{
                    type: 'streamlit:setComponentValue',
                    value: data
                }}, '*');
            }}
        }}
        
        // Initialize on load
        initKeyPoints();
        
        // Rotate confidence boosts every 30 seconds
        setInterval(updateConfidenceBoost, 30000);
    </script>
</body>
</html>
'''


# ============================================================================
# Streamlit Integration Functions
# ============================================================================

def render_copilot_component(
    resume_text: str,
    jd_text: str,
    height: int = 650
) -> None:
    """
    Render the live interview copilot component in Streamlit.
    
    Args:
        resume_text: The candidate's resume text
        jd_text: The job description text
        height: Component height in pixels
    """
    import streamlit.components.v1 as components
    
    # Extract key points for quick reference
    key_points = extract_key_resume_points(resume_text, jd_text)
    
    # Generate the HTML
    html_code = get_copilot_component_html(
        resume_context=resume_text,
        jd_context=jd_text,
        key_points=key_points
    )
    
    # Render the component
    components.html(html_code, height=height, scrolling=True)


def get_copilot_sidebar_widget() -> str:
    """
    Returns a compact sidebar widget HTML for the copilot.
    Shows status and quick tips.
    """
    return '''
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 15px;
        color: white;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    ">
        <div style="font-size: 16px; font-weight: 600; margin-bottom: 10px;">
            🤖 Copilot Active
        </div>
        <div style="font-size: 12px; opacity: 0.9;">
            Real-time assistance is ready. The copilot will detect questions and provide smart suggestions.
        </div>
    </div>
    '''
