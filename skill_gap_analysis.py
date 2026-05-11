"""
skill_gap_analysis.py
=====================

HireSense AI - Skill Gap Analysis Module

Analyzes the gap between candidate's skills (from resume) and job requirements:
- Extract skills from resume
- Extract requirements from job description
- Identify matching skills
- Identify skill gaps
- Provide recommendations for improvement
- Generate learning paths
"""

from __future__ import annotations

import os
import re
import json
from typing import Dict, Any, Optional, List, Iterator, Tuple
from dataclasses import dataclass
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
# Skill Categories
# ============================================================================

SKILL_CATEGORIES = {
    "programming_languages": {
        "name": "Programming Languages",
        "icon": "💻",
        "keywords": ["python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", 
                    "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "sql"]
    },
    "frameworks": {
        "name": "Frameworks & Libraries",
        "icon": "🏗️",
        "keywords": ["react", "angular", "vue", "django", "flask", "spring", "node", "express",
                    "tensorflow", "pytorch", "keras", "pandas", "numpy", "scikit-learn"]
    },
    "databases": {
        "name": "Databases",
        "icon": "🗄️",
        "keywords": ["mysql", "postgresql", "mongodb", "redis", "elasticsearch", "cassandra",
                    "dynamodb", "oracle", "sql server", "sqlite", "neo4j"]
    },
    "cloud_devops": {
        "name": "Cloud & DevOps",
        "icon": "☁️",
        "keywords": ["aws", "azure", "gcp", "docker", "kubernetes", "jenkins", "terraform",
                    "ansible", "ci/cd", "github actions", "gitlab", "circleci"]
    },
    "data_ml": {
        "name": "Data & ML",
        "icon": "🤖",
        "keywords": ["machine learning", "deep learning", "nlp", "computer vision", "data science",
                    "data analysis", "statistics", "big data", "spark", "hadoop", "etl"]
    },
    "soft_skills": {
        "name": "Soft Skills",
        "icon": "🤝",
        "keywords": ["leadership", "communication", "teamwork", "problem-solving", "agile",
                    "scrum", "project management", "mentoring", "presentation"]
    },
    "domain": {
        "name": "Domain Knowledge",
        "icon": "📚",
        "keywords": ["fintech", "healthcare", "e-commerce", "saas", "b2b", "b2c", "startup",
                    "enterprise", "security", "compliance", "gdpr"]
    }
}


# ============================================================================
# Skill Data Classes
# ============================================================================

@dataclass
class Skill:
    """Represents a single skill."""
    name: str
    category: str
    proficiency: str  # beginner, intermediate, advanced, expert
    years_experience: Optional[float] = None
    context: Optional[str] = None  # Where/how the skill was used


@dataclass
class SkillGap:
    """Represents a gap between required and possessed skills."""
    skill_name: str
    category: str
    required_level: str
    current_level: str  # "none" if not possessed
    priority: str  # high, medium, low
    recommendation: str


@dataclass
class SkillMatch:
    """Represents a matching skill between resume and JD."""
    skill_name: str
    category: str
    required_level: str
    candidate_level: str
    match_quality: str  # exceeds, meets, partial, none


# ============================================================================
# Skill Extraction
# ============================================================================

def extract_skills_from_text(
    text: str,
    text_type: str = "resume",  # "resume" or "job_description"
    *,
    model_name: str = "google/gemini-2.0-flash-001",
    temperature: float = 0.2,
) -> Dict[str, Any]:
    """
    Extract skills from resume or job description text using AI.
    
    Returns:
        Dict with categorized skills and proficiency levels
    """
    llm = ChatOpenRouter(
        model_name=model_name,
        temperature=temperature,
        streaming=False
    )
    
    if text_type == "resume":
        system_prompt = """You are an expert resume analyzer. Extract all skills from the resume.
For each skill, determine:
1. The skill name (standardized)
2. Category (programming_languages, frameworks, databases, cloud_devops, data_ml, soft_skills, domain)
3. Proficiency level (beginner, intermediate, advanced, expert) based on context
4. Years of experience if mentioned
5. Context where the skill was used

Return JSON:
{
    "skills": [
        {
            "name": "Python",
            "category": "programming_languages",
            "proficiency": "advanced",
            "years": 5,
            "context": "Used for data analysis and ML projects"
        }
    ],
    "summary": {
        "total_skills": 15,
        "strongest_categories": ["programming_languages", "data_ml"],
        "experience_level": "senior"
    }
}"""
    else:
        system_prompt = """You are an expert job description analyzer. Extract all required skills.
For each skill, determine:
1. The skill name (standardized)
2. Category (programming_languages, frameworks, databases, cloud_devops, data_ml, soft_skills, domain)
3. Required level (beginner, intermediate, advanced, expert)
4. Whether it's required or preferred
5. Context from the JD

Return JSON:
{
    "skills": [
        {
            "name": "Python",
            "category": "programming_languages",
            "required_level": "advanced",
            "is_required": true,
            "context": "Required for backend development"
        }
    ],
    "summary": {
        "total_requirements": 12,
        "must_have_count": 8,
        "nice_to_have_count": 4,
        "role_level": "senior"
    }
}"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Analyze this {text_type}:\n\n{text[:4000]}"}
    ]
    
    try:
        response = llm.invoke(messages)
        content = response.content
        
        # Extract JSON
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"Skill extraction error: {e}")
    
    return {"skills": [], "summary": {}}


# ============================================================================
# Gap Analysis
# ============================================================================

def analyze_skill_gaps(
    resume_skills: Dict[str, Any],
    jd_skills: Dict[str, Any],
    *,
    model_name: str = "google/gemini-2.0-flash-001",
    temperature: float = 0.3,
) -> Dict[str, Any]:
    """
    Analyze gaps between candidate skills and job requirements.
    
    Returns comprehensive gap analysis with recommendations.
    """
    llm = ChatOpenRouter(
        model_name=model_name,
        temperature=temperature,
        streaming=False
    )
    
    system_prompt = """You are an expert career coach and technical recruiter.
Analyze the skill gap between a candidate's skills and job requirements.

Provide a comprehensive analysis in JSON format:
{
    "overall_match_score": <0-100>,
    "match_category": "Strong Match" | "Good Match" | "Partial Match" | "Needs Development",
    
    "matching_skills": [
        {
            "skill": "Python",
            "candidate_level": "advanced",
            "required_level": "advanced",
            "match_quality": "meets",
            "notes": "Strong match for this requirement"
        }
    ],
    
    "skill_gaps": [
        {
            "skill": "Kubernetes",
            "required_level": "intermediate",
            "current_level": "none",
            "priority": "high",
            "gap_severity": "significant",
            "recommendation": "Take a Kubernetes fundamentals course",
            "estimated_learning_time": "2-3 months"
        }
    ],
    
    "exceeding_skills": [
        {
            "skill": "Machine Learning",
            "candidate_level": "expert",
            "required_level": "intermediate",
            "value_add": "Could contribute to advanced ML initiatives"
        }
    ],
    
    "category_analysis": {
        "programming_languages": {"score": 85, "status": "strong"},
        "frameworks": {"score": 70, "status": "good"},
        "cloud_devops": {"score": 40, "status": "needs_work"}
    },
    
    "interview_focus_areas": [
        "Cloud infrastructure experience",
        "System design at scale"
    ],
    
    "development_priorities": [
        {
            "area": "Cloud & DevOps",
            "current_gap": "significant",
            "recommended_actions": ["AWS certification", "Docker practice"],
            "timeline": "3-6 months"
        }
    ],
    
    "strengths_to_highlight": [
        "Strong Python and data analysis background",
        "Excellent problem-solving demonstrated through projects"
    ],
    
    "risk_assessment": {
        "overall_risk": "low" | "medium" | "high",
        "main_concerns": ["Limited cloud experience"],
        "mitigating_factors": ["Quick learner", "Strong fundamentals"]
    }
}"""

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"""Analyze the skill gap:

CANDIDATE'S SKILLS:
{json.dumps(resume_skills, indent=2)}

JOB REQUIREMENTS:
{json.dumps(jd_skills, indent=2)}

Provide comprehensive gap analysis:"""
        }
    ]
    
    try:
        response = llm.invoke(messages)
        content = response.content
        
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"Gap analysis error: {e}")
    
    return {
        "overall_match_score": 50,
        "match_category": "Partial Match",
        "matching_skills": [],
        "skill_gaps": [],
        "exceeding_skills": [],
        "category_analysis": {},
        "interview_focus_areas": [],
        "development_priorities": [],
        "strengths_to_highlight": [],
        "risk_assessment": {"overall_risk": "medium"}
    }


# ============================================================================
# Learning Path Generation
# ============================================================================

def generate_learning_path(
    skill_gaps: List[Dict],
    target_timeline_months: int = 3,
    *,
    model_name: str = "google/gemini-2.0-flash-001",
    temperature: float = 0.5,
) -> Iterator[str]:
    """
    Generate a personalized learning path to address skill gaps.
    
    Yields tokens for streaming display.
    """
    llm = ChatOpenRouter(
        model_name=model_name,
        temperature=temperature,
        streaming=True
    )
    
    system_prompt = f"""You are an expert career coach and learning specialist.
Create a personalized learning path to address the candidate's skill gaps.

Timeline: {target_timeline_months} months

Include:
1. Prioritized learning objectives
2. Specific resources (courses, books, projects)
3. Weekly/monthly milestones
4. Practice projects to build portfolio
5. Metrics to track progress

Format the response in clear markdown with sections and actionable items."""

    gaps_text = "\n".join([
        f"- {gap.get('skill', 'Unknown')}: {gap.get('required_level', 'unknown')} required, "
        f"currently {gap.get('current_level', 'none')} (Priority: {gap.get('priority', 'medium')})"
        for gap in skill_gaps
    ])

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"""Create a learning path for these skill gaps:

{gaps_text}

Generate a detailed, actionable learning plan:"""
        }
    ]
    
    for chunk in llm.stream(messages):
        if hasattr(chunk, 'content'):
            yield chunk.content


# ============================================================================
# Visualization Helpers
# ============================================================================

def get_skill_radar_data(gap_analysis: Dict) -> Dict[str, Any]:
    """Prepare data for skill radar chart visualization."""
    category_analysis = gap_analysis.get("category_analysis", {})
    
    categories = []
    scores = []
    
    for cat_key, cat_info in SKILL_CATEGORIES.items():
        cat_data = category_analysis.get(cat_key, {"score": 0})
        categories.append(cat_info["name"])
        scores.append(cat_data.get("score", 0))
    
    return {
        "categories": categories,
        "scores": scores,
        "icons": [cat["icon"] for cat in SKILL_CATEGORIES.values()]
    }


def get_gap_summary_stats(gap_analysis: Dict) -> Dict[str, Any]:
    """Get summary statistics from gap analysis."""
    matching = len(gap_analysis.get("matching_skills", []))
    gaps = len(gap_analysis.get("skill_gaps", []))
    exceeding = len(gap_analysis.get("exceeding_skills", []))
    
    high_priority_gaps = sum(
        1 for gap in gap_analysis.get("skill_gaps", [])
        if gap.get("priority") == "high"
    )
    
    return {
        "matching_count": matching,
        "gap_count": gaps,
        "exceeding_count": exceeding,
        "high_priority_gaps": high_priority_gaps,
        "overall_score": gap_analysis.get("overall_match_score", 0),
        "match_category": gap_analysis.get("match_category", "Unknown"),
        "total_skills_analyzed": matching + gaps + exceeding
    }


def format_gap_analysis_markdown(gap_analysis: Dict) -> str:
    """Format gap analysis as markdown for display."""
    stats = get_gap_summary_stats(gap_analysis)
    
    output = f"""
## 📊 Skill Gap Analysis Report

### Overall Assessment
- **Match Score:** {stats['overall_score']}%
- **Category:** {stats['match_category']}
- **Skills Analyzed:** {stats['total_skills_analyzed']}

---

### ✅ Matching Skills ({stats['matching_count']})
"""
    
    for skill in gap_analysis.get("matching_skills", [])[:5]:
        quality_emoji = {"exceeds": "🌟", "meets": "✅", "partial": "⚠️"}.get(
            skill.get("match_quality", ""), "•"
        )
        output += f"\n{quality_emoji} **{skill.get('skill', 'Unknown')}** - {skill.get('match_quality', 'unknown').title()}"
    
    output += f"""

---

### ⚠️ Skill Gaps ({stats['gap_count']})
"""
    
    for gap in gap_analysis.get("skill_gaps", [])[:5]:
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
            gap.get("priority", ""), "•"
        )
        output += f"\n{priority_emoji} **{gap.get('skill', 'Unknown')}** ({gap.get('priority', 'unknown').title()} Priority)"
        output += f"\n   - Required: {gap.get('required_level', 'unknown')}, Current: {gap.get('current_level', 'none')}"
        if gap.get("recommendation"):
            output += f"\n   - 💡 {gap.get('recommendation')}"
    
    output += f"""

---

### 🌟 Exceeding Expectations ({stats['exceeding_count']})
"""
    
    for skill in gap_analysis.get("exceeding_skills", [])[:3]:
        output += f"\n⭐ **{skill.get('skill', 'Unknown')}** - {skill.get('value_add', '')}"
    
    # Interview focus areas
    focus_areas = gap_analysis.get("interview_focus_areas", [])
    if focus_areas:
        output += "\n\n---\n\n### 🎯 Interview Focus Areas\n"
        for area in focus_areas:
            output += f"\n- {area}"
    
    # Strengths to highlight
    strengths = gap_analysis.get("strengths_to_highlight", [])
    if strengths:
        output += "\n\n---\n\n### 💪 Strengths to Highlight\n"
        for strength in strengths:
            output += f"\n- {strength}"
    
    return output


# ============================================================================
# Full Analysis Pipeline
# ============================================================================

def run_full_skill_analysis(
    resume_text: str,
    jd_text: str,
    *,
    model_name: str = "google/gemini-2.0-flash-001",
) -> Dict[str, Any]:
    """
    Run complete skill gap analysis pipeline.
    
    Returns:
        Dict with all analysis results
    """
    # Extract skills from resume
    resume_skills = extract_skills_from_text(
        resume_text, 
        text_type="resume",
        model_name=model_name
    )
    
    # Extract requirements from JD
    jd_skills = extract_skills_from_text(
        jd_text,
        text_type="job_description", 
        model_name=model_name
    )
    
    # Analyze gaps
    gap_analysis = analyze_skill_gaps(
        resume_skills,
        jd_skills,
        model_name=model_name
    )
    
    return {
        "resume_skills": resume_skills,
        "jd_requirements": jd_skills,
        "gap_analysis": gap_analysis,
        "summary_stats": get_gap_summary_stats(gap_analysis),
        "radar_data": get_skill_radar_data(gap_analysis),
        "formatted_report": format_gap_analysis_markdown(gap_analysis)
    }


# ============================================================================
# Streamlit Component Helpers
# ============================================================================

def get_skill_gap_chart_html(radar_data: Dict) -> str:
    """Generate HTML/JS for skill radar chart using Chart.js."""
    categories = json.dumps(radar_data.get("categories", []))
    scores = json.dumps(radar_data.get("scores", []))
    
    return f'''
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .chart-container {{
            width: 100%;
            max-width: 400px;
            margin: 0 auto;
        }}
    </style>
</head>
<body>
    <div class="chart-container">
        <canvas id="skillRadar"></canvas>
    </div>
    <script>
        const ctx = document.getElementById('skillRadar').getContext('2d');
        new Chart(ctx, {{
            type: 'radar',
            data: {{
                labels: {categories},
                datasets: [{{
                    label: 'Skill Match %',
                    data: {scores},
                    fill: true,
                    backgroundColor: 'rgba(99, 102, 241, 0.2)',
                    borderColor: 'rgb(99, 102, 241)',
                    pointBackgroundColor: 'rgb(99, 102, 241)',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: 'rgb(99, 102, 241)'
                }}]
            }},
            options: {{
                elements: {{
                    line: {{
                        borderWidth: 3
                    }}
                }},
                scales: {{
                    r: {{
                        angleLines: {{
                            display: true
                        }},
                        suggestedMin: 0,
                        suggestedMax: 100
                    }}
                }},
                plugins: {{
                    legend: {{
                        display: false
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
'''


def get_match_score_gauge_html(score: int, category: str) -> str:
    """Generate HTML for match score gauge visualization."""
    # Determine color based on score
    if score >= 80:
        color = "#22c55e"  # green
        status = "Excellent"
    elif score >= 60:
        color = "#84cc16"  # lime
        status = "Good"
    elif score >= 40:
        color = "#eab308"  # yellow
        status = "Fair"
    else:
        color = "#ef4444"  # red
        status = "Needs Work"
    
    return f'''
<div style="text-align: center; padding: 20px;">
    <div style="position: relative; width: 150px; height: 150px; margin: 0 auto;">
        <svg viewBox="0 0 36 36" style="transform: rotate(-90deg);">
            <path
                d="M18 2.0845
                   a 15.9155 15.9155 0 0 1 0 31.831
                   a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="#e5e7eb"
                stroke-width="3"
            />
            <path
                d="M18 2.0845
                   a 15.9155 15.9155 0 0 1 0 31.831
                   a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="{color}"
                stroke-width="3"
                stroke-dasharray="{score}, 100"
            />
        </svg>
        <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center;">
            <div style="font-size: 28px; font-weight: bold; color: {color};">{score}%</div>
            <div style="font-size: 12px; color: #666;">{status}</div>
        </div>
    </div>
    <div style="margin-top: 10px; font-size: 14px; color: #333; font-weight: 500;">{category}</div>
</div>
'''
