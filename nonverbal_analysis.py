"""
nonverbal_analysis.py
=====================

HireSense AI - Advanced Non-Verbal Feedback Analysis Module

Analyzes recorded interview sessions for non-verbal communication cues:
- Eye Contact: Tracks gaze direction to determine camera engagement
- Posture: Analyzes body positioning for confidence indicators
- Filler Words: Detects and counts verbal fillers (um, ah, like, etc.)

Uses client-side computer vision (TensorFlow.js, MediaPipe) and 
speech-to-text analysis for comprehensive feedback.
"""

from __future__ import annotations

import os
import json
import re
from typing import Dict, Any, Optional, List, Iterator, Tuple
from dataclasses import dataclass, asdict
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
# Data Classes
# ============================================================================

@dataclass
class EyeContactMetrics:
    """Metrics for eye contact analysis."""
    total_duration_seconds: float
    looking_at_camera_seconds: float
    looking_away_seconds: float
    eye_contact_percentage: float
    longest_eye_contact_streak: float
    average_gaze_duration: float
    look_away_count: int
    rating: str  # excellent, good, needs_improvement, poor
    feedback: str


@dataclass
class PostureMetrics:
    """Metrics for posture analysis."""
    total_frames_analyzed: int
    good_posture_frames: int
    slouching_frames: int
    leaning_frames: int
    posture_score: float  # 0-100
    confidence_indicators: List[str]
    improvement_areas: List[str]
    rating: str  # excellent, good, needs_improvement, poor
    feedback: str


@dataclass
class FillerWordMetrics:
    """Metrics for filler word analysis."""
    total_words_spoken: int
    total_filler_words: int
    filler_word_percentage: float
    filler_breakdown: Dict[str, int]  # {"um": 5, "like": 3, etc.}
    words_per_minute: float
    filler_words_per_minute: float
    rating: str  # excellent, good, needs_improvement, poor
    feedback: str
    worst_offenders: List[Tuple[str, int]]


@dataclass
class NonVerbalAnalysisResult:
    """Complete non-verbal analysis result."""
    session_id: str
    analysis_timestamp: str
    video_duration_seconds: float
    eye_contact: EyeContactMetrics
    posture: PostureMetrics
    filler_words: FillerWordMetrics
    overall_score: float  # 0-100
    overall_rating: str
    key_strengths: List[str]
    areas_for_improvement: List[str]
    personalized_tips: List[str]


# ============================================================================
# Filler Words Configuration
# ============================================================================

FILLER_WORDS = {
    "um": {"weight": 1.0, "category": "hesitation"},
    "uh": {"weight": 1.0, "category": "hesitation"},
    "ah": {"weight": 0.8, "category": "hesitation"},
    "er": {"weight": 0.8, "category": "hesitation"},
    "like": {"weight": 0.7, "category": "verbal_tic"},
    "you know": {"weight": 0.6, "category": "verbal_tic"},
    "i mean": {"weight": 0.5, "category": "clarification"},
    "basically": {"weight": 0.5, "category": "filler"},
    "actually": {"weight": 0.4, "category": "filler"},
    "literally": {"weight": 0.5, "category": "filler"},
    "so": {"weight": 0.3, "category": "transition"},
    "well": {"weight": 0.3, "category": "transition"},
    "right": {"weight": 0.4, "category": "verbal_tic"},
    "okay": {"weight": 0.3, "category": "transition"},
    "kind of": {"weight": 0.5, "category": "hedging"},
    "sort of": {"weight": 0.5, "category": "hedging"},
}


# ============================================================================
# Rating Thresholds
# ============================================================================

EYE_CONTACT_THRESHOLDS = {
    "excellent": 80,  # 80%+ eye contact
    "good": 65,
    "needs_improvement": 50,
    "poor": 0
}

POSTURE_THRESHOLDS = {
    "excellent": 85,
    "good": 70,
    "needs_improvement": 55,
    "poor": 0
}

FILLER_WORD_THRESHOLDS = {
    "excellent": 2,  # Less than 2% filler words
    "good": 5,
    "needs_improvement": 10,
    "poor": 100
}


# ============================================================================
# Analysis Functions
# ============================================================================

def analyze_filler_words(transcript: str, duration_seconds: float) -> FillerWordMetrics:
    """
    Analyze transcript for filler word usage.
    
    Args:
        transcript: The speech-to-text transcript
        duration_seconds: Total duration of the recording in seconds
    
    Returns:
        FillerWordMetrics with detailed analysis
    """
    # Normalize transcript
    text = transcript.lower()
    
    # Count total words
    words = re.findall(r'\b\w+\b', text)
    total_words = len(words)
    
    # Count filler words
    filler_breakdown = {}
    total_filler_count = 0
    
    for filler, config in FILLER_WORDS.items():
        # Use word boundary matching for single words
        if " " in filler:
            # Multi-word fillers
            count = len(re.findall(rf'\b{re.escape(filler)}\b', text))
        else:
            # Single word fillers
            count = len(re.findall(rf'\b{re.escape(filler)}\b', text))
        
        if count > 0:
            filler_breakdown[filler] = count
            total_filler_count += count
    
    # Calculate metrics
    filler_percentage = (total_filler_count / max(total_words, 1)) * 100
    words_per_minute = (total_words / max(duration_seconds, 1)) * 60
    filler_per_minute = (total_filler_count / max(duration_seconds, 1)) * 60
    
    # Determine rating
    if filler_percentage < FILLER_WORD_THRESHOLDS["excellent"]:
        rating = "excellent"
    elif filler_percentage < FILLER_WORD_THRESHOLDS["good"]:
        rating = "good"
    elif filler_percentage < FILLER_WORD_THRESHOLDS["needs_improvement"]:
        rating = "needs_improvement"
    else:
        rating = "poor"
    
    # Get worst offenders
    worst_offenders = sorted(filler_breakdown.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Generate feedback
    feedback = _generate_filler_feedback(rating, filler_breakdown, filler_percentage, worst_offenders)
    
    return FillerWordMetrics(
        total_words_spoken=total_words,
        total_filler_words=total_filler_count,
        filler_word_percentage=round(filler_percentage, 2),
        filler_breakdown=filler_breakdown,
        words_per_minute=round(words_per_minute, 1),
        filler_words_per_minute=round(filler_per_minute, 2),
        rating=rating,
        feedback=feedback,
        worst_offenders=worst_offenders
    )


def _generate_filler_feedback(
    rating: str, 
    breakdown: Dict[str, int], 
    percentage: float,
    worst_offenders: List[Tuple[str, int]]
) -> str:
    """Generate personalized feedback for filler word usage."""
    
    if rating == "excellent":
        return (
            "Excellent verbal fluency! You used very few filler words, which makes your "
            "communication sound confident and polished. Keep up the great work!"
        )
    elif rating == "good":
        return (
            f"Good verbal fluency with {percentage:.1f}% filler words. "
            f"Your most common filler is '{worst_offenders[0][0]}' ({worst_offenders[0][1]} times). "
            "Try pausing briefly instead of using fillers when gathering your thoughts."
        )
    elif rating == "needs_improvement":
        top_fillers = ", ".join([f"'{w}'" for w, _ in worst_offenders[:3]])
        return (
            f"Your filler word usage ({percentage:.1f}%) is above average. "
            f"Focus on reducing: {top_fillers}. "
            "Practice pausing silently instead of filling gaps with these words. "
            "Recording yourself and reviewing can help build awareness."
        )
    else:
        return (
            f"High filler word usage detected ({percentage:.1f}%). This can undermine "
            "your credibility and make you appear less confident. "
            "Key areas to work on: practice with deliberate pauses, slow down your speech, "
            "and prepare key talking points in advance. Consider joining a speaking group "
            "like Toastmasters for structured practice."
        )


def calculate_eye_contact_rating(percentage: float) -> str:
    """Calculate rating based on eye contact percentage."""
    if percentage >= EYE_CONTACT_THRESHOLDS["excellent"]:
        return "excellent"
    elif percentage >= EYE_CONTACT_THRESHOLDS["good"]:
        return "good"
    elif percentage >= EYE_CONTACT_THRESHOLDS["needs_improvement"]:
        return "needs_improvement"
    else:
        return "poor"


def calculate_posture_rating(score: float) -> str:
    """Calculate rating based on posture score."""
    if score >= POSTURE_THRESHOLDS["excellent"]:
        return "excellent"
    elif score >= POSTURE_THRESHOLDS["good"]:
        return "good"
    elif score >= POSTURE_THRESHOLDS["needs_improvement"]:
        return "needs_improvement"
    else:
        return "poor"


def calculate_overall_score(
    eye_contact: EyeContactMetrics,
    posture: PostureMetrics,
    filler_words: FillerWordMetrics
) -> Tuple[float, str]:
    """
    Calculate overall non-verbal communication score.
    
    Weights:
    - Eye Contact: 35%
    - Posture: 30%
    - Filler Words: 35%
    """
    # Convert filler word percentage to a score (inverse relationship)
    filler_score = max(0, 100 - (filler_words.filler_word_percentage * 5))
    
    # Weighted average
    overall = (
        eye_contact.eye_contact_percentage * 0.35 +
        posture.posture_score * 0.30 +
        filler_score * 0.35
    )
    
    # Determine rating
    if overall >= 85:
        rating = "excellent"
    elif overall >= 70:
        rating = "good"
    elif overall >= 55:
        rating = "needs_improvement"
    else:
        rating = "poor"
    
    return round(overall, 1), rating


def generate_personalized_tips(
    eye_contact: EyeContactMetrics,
    posture: PostureMetrics,
    filler_words: FillerWordMetrics
) -> List[str]:
    """Generate personalized improvement tips based on analysis."""
    tips = []
    
    # Eye contact tips
    if eye_contact.rating in ["needs_improvement", "poor"]:
        tips.append(
            "👁️ **Eye Contact:** Position your webcam at eye level and place a small sticker "
            "near the camera lens to remind yourself where to look."
        )
        if eye_contact.look_away_count > 10:
            tips.append(
                "👁️ **Reduce Glancing:** You looked away frequently. If you need to reference notes, "
                "position them closer to your camera or use a second monitor near the camera."
            )
    
    # Posture tips
    if posture.rating in ["needs_improvement", "poor"]:
        tips.append(
            "🪑 **Posture:** Sit with your back straight and shoulders relaxed. "
            "Consider using a chair with good lumbar support or a posture corrector."
        )
        if "slouching" in posture.improvement_areas:
            tips.append(
                "🪑 **Slouching Alert:** Set a reminder to check your posture every few minutes "
                "during practice sessions until good posture becomes habitual."
            )
    
    # Filler word tips
    if filler_words.rating in ["needs_improvement", "poor"]:
        if filler_words.worst_offenders:
            worst = filler_words.worst_offenders[0][0]
            tips.append(
                f"🗣️ **Filler Words:** Your most common filler is '{worst}'. "
                "Practice replacing it with a brief pause. Silence is more powerful than fillers."
            )
        tips.append(
            "🗣️ **Speaking Pace:** Slow down your speech slightly. Speaking too fast often "
            "leads to more filler words as your brain catches up."
        )
    
    # General tips based on overall performance
    if not tips:
        tips.append(
            "✨ **Great Job!** Your non-verbal communication is strong. "
            "Continue practicing to maintain these skills under pressure."
        )
    
    return tips


def identify_strengths_and_improvements(
    eye_contact: EyeContactMetrics,
    posture: PostureMetrics,
    filler_words: FillerWordMetrics
) -> Tuple[List[str], List[str]]:
    """Identify key strengths and areas for improvement."""
    strengths = []
    improvements = []
    
    # Eye contact
    if eye_contact.rating in ["excellent", "good"]:
        strengths.append(f"Strong eye contact ({eye_contact.eye_contact_percentage:.0f}% engagement)")
    else:
        improvements.append(f"Eye contact needs work ({eye_contact.eye_contact_percentage:.0f}% engagement)")
    
    # Posture
    if posture.rating in ["excellent", "good"]:
        strengths.append(f"Confident posture (score: {posture.posture_score:.0f}/100)")
    else:
        improvements.append(f"Posture could be improved (score: {posture.posture_score:.0f}/100)")
    
    # Filler words
    if filler_words.rating in ["excellent", "good"]:
        strengths.append(f"Minimal filler words ({filler_words.filler_word_percentage:.1f}%)")
    else:
        improvements.append(f"Reduce filler words ({filler_words.filler_word_percentage:.1f}% of speech)")
    
    return strengths, improvements


# ============================================================================
# AI-Powered Detailed Analysis
# ============================================================================

def generate_detailed_analysis_report(
    analysis_result: NonVerbalAnalysisResult,
    interview_context: Optional[str] = None
) -> Iterator[str]:
    """
    Generate a detailed AI-powered analysis report.
    
    Args:
        analysis_result: The complete non-verbal analysis result
        interview_context: Optional context about the interview type/role
    
    Yields:
        Streaming chunks of the analysis report
    """
    llm = ChatOpenRouter(
        model="google/gemini-2.0-flash-001",
        temperature=0.7,
        streaming=True
    )
    
    prompt = f"""You are an expert interview coach analyzing a candidate's non-verbal communication 
from a recorded mock interview session. Provide detailed, actionable feedback.

## Analysis Data

**Overall Score:** {analysis_result.overall_score}/100 ({analysis_result.overall_rating})

### Eye Contact Analysis
- Eye contact percentage: {analysis_result.eye_contact.eye_contact_percentage}%
- Longest eye contact streak: {analysis_result.eye_contact.longest_eye_contact_streak:.1f} seconds
- Times looked away: {analysis_result.eye_contact.look_away_count}
- Rating: {analysis_result.eye_contact.rating}

### Posture Analysis
- Posture score: {analysis_result.posture.posture_score}/100
- Good posture frames: {analysis_result.posture.good_posture_frames}/{analysis_result.posture.total_frames_analyzed}
- Confidence indicators: {', '.join(analysis_result.posture.confidence_indicators) or 'None detected'}
- Areas to improve: {', '.join(analysis_result.posture.improvement_areas) or 'None'}
- Rating: {analysis_result.posture.rating}

### Filler Word Analysis
- Total words spoken: {analysis_result.filler_words.total_words_spoken}
- Filler word percentage: {analysis_result.filler_words.filler_word_percentage}%
- Words per minute: {analysis_result.filler_words.words_per_minute}
- Most common fillers: {', '.join([f"'{w}' ({c}x)" for w, c in analysis_result.filler_words.worst_offenders[:3]]) or 'None'}
- Rating: {analysis_result.filler_words.rating}

{f"### Interview Context: {interview_context}" if interview_context else ""}

## Your Task

Write a comprehensive, encouraging feedback report that:

1. **Summary** (2-3 sentences): Overall impression of the candidate's non-verbal communication
2. **Strengths** (bullet points): What they did well
3. **Areas for Growth** (bullet points): Specific, actionable improvements
4. **Practice Exercises**: 2-3 specific exercises they can do to improve their weakest area
5. **Motivation**: End with an encouraging note about their potential

Use a supportive, coaching tone. Be specific and reference the actual numbers from the analysis.
Format using Markdown with headers and bullet points."""

    for chunk in llm.stream(prompt):
        yield chunk.content


# ============================================================================
# Client-Side Analysis Component (HTML/JS)
# ============================================================================

def get_nonverbal_analysis_component_html(video_blob_url: str, height: int = 600) -> str:
    """
    Generate HTML/JS component for client-side non-verbal analysis.
    
    Uses:
    - MediaPipe Face Mesh for eye tracking
    - MediaPipe Pose for posture detection
    - Web Speech API for transcript generation
    
    Args:
        video_blob_url: URL to the recorded video blob
        height: Component height in pixels
    
    Returns:
        HTML string with embedded JavaScript
    """
    return f'''
    <div id="nonverbal-analysis-container" style="
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 16px;
        padding: 24px;
        color: white;
        height: {height}px;
        overflow-y: auto;
    ">
        <h2 style="margin: 0 0 20px 0; display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 28px;">🔍</span>
            Non-Verbal Communication Analysis
        </h2>
        
        <!-- Analysis Progress -->
        <div id="analysis-progress" style="margin-bottom: 24px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <span>Analyzing your interview...</span>
                <span id="progress-percent">0%</span>
            </div>
            <div style="
                background: rgba(255,255,255,0.1);
                border-radius: 10px;
                height: 8px;
                overflow: hidden;
            ">
                <div id="progress-bar" style="
                    background: linear-gradient(90deg, #4CAF50, #8BC34A);
                    height: 100%;
                    width: 0%;
                    transition: width 0.3s ease;
                "></div>
            </div>
            <div id="analysis-status" style="
                margin-top: 12px;
                font-size: 14px;
                color: rgba(255,255,255,0.7);
            ">Initializing analysis...</div>
        </div>
        
        <!-- Hidden Video Element -->
        <video id="analysis-video" src="{video_blob_url}" style="display: none;" crossorigin="anonymous"></video>
        
        <!-- Results Container (hidden initially) -->
        <div id="results-container" style="display: none;">
            <!-- Overall Score -->
            <div id="overall-score-card" style="
                background: rgba(255,255,255,0.1);
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 20px;
                text-align: center;
            ">
                <div style="font-size: 48px; font-weight: bold;" id="overall-score">--</div>
                <div style="font-size: 14px; color: rgba(255,255,255,0.7);">Overall Score</div>
                <div id="overall-rating" style="
                    display: inline-block;
                    padding: 4px 12px;
                    border-radius: 20px;
                    font-size: 12px;
                    margin-top: 8px;
                    background: rgba(76, 175, 80, 0.3);
                ">--</div>
            </div>
            
            <!-- Metrics Grid -->
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 20px;">
                <!-- Eye Contact -->
                <div class="metric-card" style="
                    background: rgba(255,255,255,0.05);
                    border-radius: 12px;
                    padding: 16px;
                    border-left: 4px solid #2196F3;
                ">
                    <div style="font-size: 24px; margin-bottom: 8px;">👁️</div>
                    <div style="font-size: 24px; font-weight: bold;" id="eye-contact-score">--%</div>
                    <div style="font-size: 12px; color: rgba(255,255,255,0.7);">Eye Contact</div>
                    <div id="eye-contact-rating" style="
                        font-size: 11px;
                        padding: 2px 8px;
                        border-radius: 10px;
                        display: inline-block;
                        margin-top: 8px;
                    ">--</div>
                </div>
                
                <!-- Posture -->
                <div class="metric-card" style="
                    background: rgba(255,255,255,0.05);
                    border-radius: 12px;
                    padding: 16px;
                    border-left: 4px solid #9C27B0;
                ">
                    <div style="font-size: 24px; margin-bottom: 8px;">🪑</div>
                    <div style="font-size: 24px; font-weight: bold;" id="posture-score">--</div>
                    <div style="font-size: 12px; color: rgba(255,255,255,0.7);">Posture Score</div>
                    <div id="posture-rating" style="
                        font-size: 11px;
                        padding: 2px 8px;
                        border-radius: 10px;
                        display: inline-block;
                        margin-top: 8px;
                    ">--</div>
                </div>
                
                <!-- Filler Words -->
                <div class="metric-card" style="
                    background: rgba(255,255,255,0.05);
                    border-radius: 12px;
                    padding: 16px;
                    border-left: 4px solid #FF9800;
                ">
                    <div style="font-size: 24px; margin-bottom: 8px;">🗣️</div>
                    <div style="font-size: 24px; font-weight: bold;" id="filler-score">--%</div>
                    <div style="font-size: 12px; color: rgba(255,255,255,0.7);">Filler Words</div>
                    <div id="filler-rating" style="
                        font-size: 11px;
                        padding: 2px 8px;
                        border-radius: 10px;
                        display: inline-block;
                        margin-top: 8px;
                    ">--</div>
                </div>
            </div>
            
            <!-- Detailed Breakdown -->
            <div id="detailed-breakdown" style="
                background: rgba(255,255,255,0.05);
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 20px;
            ">
                <h3 style="margin: 0 0 16px 0;">📊 Detailed Breakdown</h3>
                
                <!-- Eye Contact Details -->
                <div style="margin-bottom: 16px;">
                    <h4 style="margin: 0 0 8px 0; color: #2196F3;">👁️ Eye Contact Analysis</h4>
                    <div id="eye-contact-details" style="font-size: 14px; color: rgba(255,255,255,0.8);"></div>
                </div>
                
                <!-- Posture Details -->
                <div style="margin-bottom: 16px;">
                    <h4 style="margin: 0 0 8px 0; color: #9C27B0;">🪑 Posture Analysis</h4>
                    <div id="posture-details" style="font-size: 14px; color: rgba(255,255,255,0.8);"></div>
                </div>
                
                <!-- Filler Word Details -->
                <div>
                    <h4 style="margin: 0 0 8px 0; color: #FF9800;">🗣️ Filler Word Analysis</h4>
                    <div id="filler-details" style="font-size: 14px; color: rgba(255,255,255,0.8);"></div>
                    <div id="filler-chart" style="margin-top: 12px;"></div>
                </div>
            </div>
            
            <!-- Tips Section -->
            <div id="tips-section" style="
                background: linear-gradient(135deg, rgba(76,175,80,0.2) 0%, rgba(139,195,74,0.2) 100%);
                border-radius: 12px;
                padding: 20px;
                border: 1px solid rgba(76,175,80,0.3);
            ">
                <h3 style="margin: 0 0 16px 0;">💡 Personalized Tips</h3>
                <div id="tips-content"></div>
            </div>
        </div>
    </div>
    
    <!-- Load MediaPipe -->
    <script src="https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/face_mesh.js" crossorigin="anonymous"></script>
    <script src="https://cdn.jsdelivr.net/npm/@mediapipe/pose/pose.js" crossorigin="anonymous"></script>
    <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js" crossorigin="anonymous"></script>
    
    <script>
    (function() {{
        // Analysis state
        const state = {{
            eyeContactFrames: 0,
            totalFrames: 0,
            lookAwayCount: 0,
            currentlyLookingAtCamera: true,
            longestStreak: 0,
            currentStreak: 0,
            gazeHistory: [],
            
            goodPostureFrames: 0,
            slouchingFrames: 0,
            leaningFrames: 0,
            
            transcript: '',
            fillerCounts: {{}},
            totalWords: 0,
            
            videoDuration: 0,
            analysisComplete: false
        }};
        
        const video = document.getElementById('analysis-video');
        const progressBar = document.getElementById('progress-bar');
        const progressPercent = document.getElementById('progress-percent');
        const analysisStatus = document.getElementById('analysis-status');
        
        // Filler words to detect
        const fillerWords = ['um', 'uh', 'ah', 'er', 'like', 'you know', 'i mean', 
                           'basically', 'actually', 'literally', 'so', 'well', 
                           'right', 'okay', 'kind of', 'sort of'];
        
        // Initialize MediaPipe Face Mesh
        let faceMesh = null;
        let pose = null;
        
        async function initializeAnalysis() {{
            updateStatus('Loading AI models...');
            updateProgress(5);
            
            try {{
                // Initialize Face Mesh for eye tracking
                faceMesh = new FaceMesh({{
                    locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${{file}}`
                }});
                
                faceMesh.setOptions({{
                    maxNumFaces: 1,
                    refineLandmarks: true,
                    minDetectionConfidence: 0.5,
                    minTrackingConfidence: 0.5
                }});
                
                faceMesh.onResults(onFaceResults);
                
                // Initialize Pose for posture detection
                pose = new Pose({{
                    locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${{file}}`
                }});
                
                pose.setOptions({{
                    modelComplexity: 1,
                    smoothLandmarks: true,
                    minDetectionConfidence: 0.5,
                    minTrackingConfidence: 0.5
                }});
                
                pose.onResults(onPoseResults);
                
                updateProgress(15);
                updateStatus('Models loaded. Starting video analysis...');
                
                // Start video analysis
                await analyzeVideo();
                
            }} catch (error) {{
                console.error('Analysis initialization error:', error);
                updateStatus('Error: ' + error.message);
            }}
        }}
        
        function onFaceResults(results) {{
            state.totalFrames++;
            
            if (results.multiFaceLandmarks && results.multiFaceLandmarks.length > 0) {{
                const landmarks = results.multiFaceLandmarks[0];
                
                // Analyze eye gaze using iris landmarks (468-477)
                const leftIris = landmarks[468];
                const rightIris = landmarks[473];
                const nose = landmarks[1];
                
                // Calculate gaze direction
                const gazeX = ((leftIris.x + rightIris.x) / 2) - nose.x;
                const gazeY = ((leftIris.y + rightIris.y) / 2) - nose.y;
                
                // Determine if looking at camera (centered gaze)
                const isLookingAtCamera = Math.abs(gazeX) < 0.05 && Math.abs(gazeY) < 0.08;
                
                if (isLookingAtCamera) {{
                    state.eyeContactFrames++;
                    state.currentStreak++;
                    if (state.currentStreak > state.longestStreak) {{
                        state.longestStreak = state.currentStreak;
                    }}
                    if (!state.currentlyLookingAtCamera) {{
                        state.currentlyLookingAtCamera = true;
                    }}
                }} else {{
                    if (state.currentlyLookingAtCamera) {{
                        state.lookAwayCount++;
                        state.currentlyLookingAtCamera = false;
                    }}
                    state.currentStreak = 0;
                }}
                
                state.gazeHistory.push({{ x: gazeX, y: gazeY, looking: isLookingAtCamera }});
            }}
        }}
        
        function onPoseResults(results) {{
            if (results.poseLandmarks) {{
                const landmarks = results.poseLandmarks;
                
                // Get key points for posture analysis
                const leftShoulder = landmarks[11];
                const rightShoulder = landmarks[12];
                const leftEar = landmarks[7];
                const rightEar = landmarks[8];
                const nose = landmarks[0];
                
                // Calculate shoulder alignment (should be relatively horizontal)
                const shoulderTilt = Math.abs(leftShoulder.y - rightShoulder.y);
                
                // Calculate head position relative to shoulders
                const headCenterX = (leftEar.x + rightEar.x) / 2;
                const shoulderCenterX = (leftShoulder.x + rightShoulder.x) / 2;
                const headOffset = Math.abs(headCenterX - shoulderCenterX);
                
                // Calculate forward lean (ear should be above shoulder)
                const earY = (leftEar.y + rightEar.y) / 2;
                const shoulderY = (leftShoulder.y + rightShoulder.y) / 2;
                const forwardLean = earY - shoulderY;
                
                // Determine posture quality
                const isGoodPosture = shoulderTilt < 0.05 && headOffset < 0.1 && forwardLean < 0.15;
                const isSlouching = forwardLean > 0.2;
                const isLeaning = headOffset > 0.15;
                
                if (isGoodPosture) {{
                    state.goodPostureFrames++;
                }} else if (isSlouching) {{
                    state.slouchingFrames++;
                }} else if (isLeaning) {{
                    state.leaningFrames++;
                }}
            }}
        }}
        
        async function analyzeVideo() {{
            return new Promise((resolve) => {{
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                
                video.addEventListener('loadedmetadata', () => {{
                    state.videoDuration = video.duration;
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    
                    updateStatus(`Video loaded: ${{Math.round(video.duration)}} seconds`);
                }});
                
                video.addEventListener('ended', async () => {{
                    updateProgress(70);
                    updateStatus('Video analysis complete. Analyzing speech...');
                    
                    // Analyze speech for filler words
                    await analyzeTranscript();
                    
                    updateProgress(90);
                    updateStatus('Generating results...');
                    
                    // Calculate and display results
                    displayResults();
                    
                    updateProgress(100);
                    state.analysisComplete = true;
                    resolve();
                }});
                
                // Process video frames
                let frameCount = 0;
                const processFrame = async () => {{
                    if (video.paused || video.ended) return;
                    
                    ctx.drawImage(video, 0, 0);
                    const imageData = canvas.toDataURL('image/jpeg', 0.8);
                    
                    // Send to MediaPipe
                    const img = new Image();
                    img.onload = async () => {{
                        await faceMesh.send({{ image: img }});
                        await pose.send({{ image: img }});
                    }};
                    img.src = imageData;
                    
                    frameCount++;
                    const progress = 15 + (video.currentTime / video.duration) * 55;
                    updateProgress(progress);
                    updateStatus(`Analyzing frame ${{frameCount}}... (${{Math.round(video.currentTime)}}s / ${{Math.round(video.duration)}}s)`);
                    
                    requestAnimationFrame(processFrame);
                }};
                
                video.play();
                processFrame();
            }});
        }}
        
        async function analyzeTranscript() {{
            // Use Web Speech API to get transcript if available
            // For now, we'll analyze any existing transcript from the interview
            const savedTranscript = sessionStorage.getItem('hiresense_interview_transcript') || '';
            state.transcript = savedTranscript;
            
            if (state.transcript) {{
                const words = state.transcript.toLowerCase().split(/\\s+/);
                state.totalWords = words.length;
                
                // Count filler words
                fillerWords.forEach(filler => {{
                    const regex = new RegExp('\\\\b' + filler.replace(' ', '\\\\s+') + '\\\\b', 'gi');
                    const matches = state.transcript.toLowerCase().match(regex);
                    if (matches) {{
                        state.fillerCounts[filler] = matches.length;
                    }}
                }});
            }}
        }}
        
        function displayResults() {{
            // Hide progress, show results
            document.getElementById('analysis-progress').style.display = 'none';
            document.getElementById('results-container').style.display = 'block';
            
            // Calculate metrics
            const eyeContactPercent = state.totalFrames > 0 
                ? Math.round((state.eyeContactFrames / state.totalFrames) * 100) 
                : 0;
            
            const postureScore = state.totalFrames > 0
                ? Math.round((state.goodPostureFrames / state.totalFrames) * 100)
                : 0;
            
            const totalFillers = Object.values(state.fillerCounts).reduce((a, b) => a + b, 0);
            const fillerPercent = state.totalWords > 0
                ? ((totalFillers / state.totalWords) * 100).toFixed(1)
                : 0;
            
            // Calculate overall score
            const fillerScore = Math.max(0, 100 - (parseFloat(fillerPercent) * 5));
            const overallScore = Math.round(
                eyeContactPercent * 0.35 +
                postureScore * 0.30 +
                fillerScore * 0.35
            );
            
            // Update UI
            document.getElementById('overall-score').textContent = overallScore;
            document.getElementById('overall-rating').textContent = getRating(overallScore);
            document.getElementById('overall-rating').style.background = getRatingColor(overallScore);
            
            document.getElementById('eye-contact-score').textContent = eyeContactPercent + '%';
            document.getElementById('eye-contact-rating').textContent = getRating(eyeContactPercent);
            document.getElementById('eye-contact-rating').style.background = getRatingColor(eyeContactPercent);
            
            document.getElementById('posture-score').textContent = postureScore + '/100';
            document.getElementById('posture-rating').textContent = getRating(postureScore);
            document.getElementById('posture-rating').style.background = getRatingColor(postureScore);
            
            document.getElementById('filler-score').textContent = fillerPercent + '%';
            const fillerRating = fillerPercent < 2 ? 'Excellent' : fillerPercent < 5 ? 'Good' : fillerPercent < 10 ? 'Needs Work' : 'Poor';
            document.getElementById('filler-rating').textContent = fillerRating;
            document.getElementById('filler-rating').style.background = fillerPercent < 5 ? 'rgba(76,175,80,0.3)' : 'rgba(255,152,0,0.3)';
            
            // Detailed breakdowns
            document.getElementById('eye-contact-details').innerHTML = `
                <p>• Maintained eye contact for <strong>${{eyeContactPercent}}%</strong> of the interview</p>
                <p>• Longest continuous eye contact: <strong>${{(state.longestStreak / 30).toFixed(1)}}s</strong></p>
                <p>• Looked away <strong>${{state.lookAwayCount}}</strong> times</p>
            `;
            
            document.getElementById('posture-details').innerHTML = `
                <p>• Good posture maintained for <strong>${{postureScore}}%</strong> of frames</p>
                <p>• Slouching detected in <strong>${{Math.round((state.slouchingFrames / Math.max(state.totalFrames, 1)) * 100)}}%</strong> of frames</p>
                <p>• Excessive leaning in <strong>${{Math.round((state.leaningFrames / Math.max(state.totalFrames, 1)) * 100)}}%</strong> of frames</p>
            `;
            
            // Filler word breakdown
            const sortedFillers = Object.entries(state.fillerCounts)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 5);
            
            let fillerHTML = `<p>• Total filler words: <strong>${{totalFillers}}</strong> out of ${{state.totalWords}} words</p>`;
            if (sortedFillers.length > 0) {{
                fillerHTML += '<p>• Most common fillers:</p><ul style="margin: 8px 0; padding-left: 20px;">';
                sortedFillers.forEach(([word, count]) => {{
                    fillerHTML += `<li>"${{word}}": ${{count}} times</li>`;
                }});
                fillerHTML += '</ul>';
            }}
            document.getElementById('filler-details').innerHTML = fillerHTML;
            
            // Tips
            const tips = generateTips(eyeContactPercent, postureScore, parseFloat(fillerPercent));
            document.getElementById('tips-content').innerHTML = tips.map(tip => 
                `<p style="margin-bottom: 12px;">${{tip}}</p>`
            ).join('');
            
            // Send results to Streamlit
            sendResultsToStreamlit({{
                eyeContact: {{
                    percentage: eyeContactPercent,
                    lookAwayCount: state.lookAwayCount,
                    longestStreak: state.longestStreak / 30
                }},
                posture: {{
                    score: postureScore,
                    slouching: Math.round((state.slouchingFrames / Math.max(state.totalFrames, 1)) * 100),
                    leaning: Math.round((state.leaningFrames / Math.max(state.totalFrames, 1)) * 100)
                }},
                fillerWords: {{
                    percentage: parseFloat(fillerPercent),
                    total: totalFillers,
                    breakdown: state.fillerCounts
                }},
                overall: {{
                    score: overallScore,
                    rating: getRating(overallScore)
                }}
            }});
        }}
        
        function getRating(score) {{
            if (score >= 85) return 'Excellent';
            if (score >= 70) return 'Good';
            if (score >= 55) return 'Needs Work';
            return 'Poor';
        }}
        
        function getRatingColor(score) {{
            if (score >= 85) return 'rgba(76, 175, 80, 0.3)';
            if (score >= 70) return 'rgba(139, 195, 74, 0.3)';
            if (score >= 55) return 'rgba(255, 193, 7, 0.3)';
            return 'rgba(244, 67, 54, 0.3)';
        }}
        
        function generateTips(eyeContact, posture, fillers) {{
            const tips = [];
            
            if (eyeContact < 70) {{
                tips.push('👁️ <strong>Eye Contact:</strong> Position your webcam at eye level and place a small sticker near the lens as a reminder to look there.');
            }}
            
            if (posture < 70) {{
                tips.push('🪑 <strong>Posture:</strong> Sit with your back straight and shoulders relaxed. Consider using a chair with good lumbar support.');
            }}
            
            if (fillers > 5) {{
                tips.push('🗣️ <strong>Filler Words:</strong> Practice pausing silently instead of using fillers. Slow down your speech to give yourself time to think.');
            }}
            
            if (tips.length === 0) {{
                tips.push('✨ <strong>Great Job!</strong> Your non-verbal communication is strong. Keep practicing to maintain these skills under pressure.');
            }}
            
            return tips;
        }}
        
        function updateProgress(percent) {{
            progressBar.style.width = percent + '%';
            progressPercent.textContent = Math.round(percent) + '%';
        }}
        
        function updateStatus(status) {{
            analysisStatus.textContent = status;
        }}
        
        function sendResultsToStreamlit(results) {{
            // Store results for Streamlit to access
            sessionStorage.setItem('hiresense_nonverbal_results', JSON.stringify(results));
            
            // Dispatch custom event
            window.dispatchEvent(new CustomEvent('nonverbal-analysis-complete', {{ detail: results }}));
        }}
        
        // Start analysis when component loads
        if ('{video_blob_url}') {{
            initializeAnalysis();
        }} else {{
            updateStatus('No video recording found. Please record an interview first.');
        }}
    }})();
    </script>
    '''


def render_nonverbal_analysis_section(height: int = 600) -> str:
    """
    Render the non-verbal analysis section for the results page.
    
    This is called from app.py to display the analysis UI.
    
    Args:
        height: Component height in pixels
    
    Returns:
        HTML string for the analysis component
    """
    return f'''
    <div id="nonverbal-trigger-container" style="
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 16px;
        padding: 24px;
        color: white;
        text-align: center;
    ">
        <h3 style="margin: 0 0 16px 0;">🔍 Advanced Non-Verbal Analysis</h3>
        <p style="color: rgba(255,255,255,0.7); margin-bottom: 20px;">
            Analyze your eye contact, posture, and filler word usage from your recorded interview.
        </p>
        <button id="start-analysis-btn" onclick="startNonVerbalAnalysis()" style="
            background: linear-gradient(135deg, #4CAF50 0%, #8BC34A 100%);
            border: none;
            color: white;
            padding: 12px 32px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        " onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
            🚀 Start Analysis
        </button>
        <p style="font-size: 12px; color: rgba(255,255,255,0.5); margin-top: 12px;">
            Requires a recorded interview session
        </p>
    </div>
    
    <script>
    function startNonVerbalAnalysis() {{
        // Check if video recording exists
        const videoUrl = sessionStorage.getItem('hiresense_video_url');
        if (!videoUrl) {{
            alert('No video recording found. Please enable video recording and complete an interview first.');
            return;
        }}
        
        // Trigger analysis
        window.dispatchEvent(new CustomEvent('start-nonverbal-analysis', {{ detail: {{ videoUrl }} }}));
    }}
    </script>
    '''


# ============================================================================
# Streamlit Integration Functions
# ============================================================================

def get_analysis_results_from_session() -> Optional[Dict[str, Any]]:
    """
    Retrieve analysis results from session storage.
    
    Returns:
        Dictionary with analysis results or None if not available
    """
    # This would be called from Streamlit to get results
    # The actual implementation would use st.session_state
    return None


def format_analysis_for_report(results: Dict[str, Any]) -> str:
    """
    Format analysis results for inclusion in the AI report.
    
    Args:
        results: Dictionary with analysis results
    
    Returns:
        Formatted markdown string
    """
    if not results:
        return ""
    
    return f"""
## 🔍 Non-Verbal Communication Analysis

### Overall Score: {results.get('overall', {}).get('score', 'N/A')}/100 ({results.get('overall', {}).get('rating', 'N/A')})

### 👁️ Eye Contact
- **Engagement:** {results.get('eyeContact', {}).get('percentage', 'N/A')}%
- **Look-away count:** {results.get('eyeContact', {}).get('lookAwayCount', 'N/A')} times
- **Longest streak:** {results.get('eyeContact', {}).get('longestStreak', 'N/A'):.1f} seconds

### 🪑 Posture
- **Score:** {results.get('posture', {}).get('score', 'N/A')}/100
- **Slouching detected:** {results.get('posture', {}).get('slouching', 'N/A')}% of time
- **Excessive leaning:** {results.get('posture', {}).get('leaning', 'N/A')}% of time

### 🗣️ Filler Words
- **Filler word percentage:** {results.get('fillerWords', {}).get('percentage', 'N/A')}%
- **Total filler words:** {results.get('fillerWords', {}).get('total', 'N/A')}
"""
