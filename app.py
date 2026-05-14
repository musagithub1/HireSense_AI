"""
app.py
======

HireSense AI - Intelligent Interview Platform
=============================================

An intelligent, adaptive mock interview platform that helps job seekers 
prepare for their dream roles by combining cutting-edge AI with real-time 
emotion detection.

Features:
- Resume + Job Description (RAG) personalization
- Real-time emotion detection (webcam)
- Adaptive interviewer (tone + difficulty)
- Voice input + TTS output
- Interview analytics + AI report card
- Interview Type Selection (Technical/Behavioral/HR/Case Study)
- Question Bank & History
- Multi-Language Support (NEW)
- Company-Specific Prep - FAANG, etc. (NEW)
- Video Recording (NEW)
- AI Follow-up Questions (NEW)
- Skill Gap Analysis (NEW)
- Live Interview Copilot (NEW)
- Integrated Coding & Whiteboard (NEW)
- Advanced Non-Verbal Analysis (NEW) - Eye contact, posture, filler words
"""

from __future__ import annotations

# ============================================================================
# IMPORTANT: Load .env file FIRST before any other imports
# ============================================================================
import config  # This loads the .env file automatically

import streamlit as st
import streamlit.components.v1 as components
import time
import json
from datetime import datetime

# Validate configuration before proceeding
is_valid, config_message = config.validate_config()
if not is_valid:
    st.set_page_config(page_title="Configuration Required", page_icon="⚠️")
    st.error(f"⚠️ {config_message}")
    st.info("""
    **How to fix this:**
    1. Create a `.env` file in the same directory as this app
    2. Add your OpenRouter API key:
       ```
       OPENROUTER_API_KEY=your_actual_api_key_here
       ```
    3. Get your API key from: https://openrouter.ai/
    4. Restart the application
    """)
    st.stop()

import interview_arena as arena
import analytics_dashboard as analytics
import webcam_component as webcam
import voice_input_component as voice_input

# New feature imports
import language_support
import company_prep
import video_recording
import followup_questions
import skill_gap_analysis
import live_copilot
import coding_whiteboard
import nonverbal_analysis


# ============================================================================
# Interview Types
# ============================================================================

INTERVIEW_TYPES = {
    "Technical": {
        "icon": "💻",
        "description": "Coding, system design, and technical problem-solving",
        "focus": ["Data structures", "Algorithms", "System design", "Technical projects"]
    },
    "Behavioral": {
        "icon": "🤝",
        "description": "Soft skills, teamwork, and past experiences (STAR method)",
        "focus": ["Leadership", "Teamwork", "Conflict resolution", "Problem-solving"]
    },
    "HR": {
        "icon": "👔",
        "description": "Culture fit, career goals, and company alignment",
        "focus": ["Career goals", "Motivation", "Company fit", "Expectations"]
    },
    "Case Study": {
        "icon": "📊",
        "description": "Business scenarios and analytical thinking",
        "focus": ["Analysis", "Problem-solving", "Business acumen", "Communication"]
    },
    "Mixed": {
        "icon": "🎯",
        "description": "Comprehensive interview covering all aspects",
        "focus": ["Technical skills", "Soft skills", "Culture fit", "Overall assessment"]
    }
}


# ============================================================================
# Helper Functions
# ============================================================================

def display_streaming_response(stream_generator):
    """Display streaming response with per-agent pipeline traces."""
    response_text = ""
    
    # Track per-agent trace content
    agent_traces = {}   # agent_name -> list of trace strings
    agent_status = {}   # agent_name -> "running" | "done"
    agent_order = []    # maintain insertion order
    
    pipeline_container = None
    pipeline_placeholder = None
    response_placeholder = st.empty()
    
    def _render_pipeline():
        """Re-render the full pipeline view."""
        if pipeline_placeholder is None:
            return
        md = ""
        for agent_name in agent_order:
            status = agent_status.get(agent_name, "running")
            traces = agent_traces.get(agent_name, [])
            
            if status == "done":
                status_icon = "✅"
            else:
                status_icon = "🔄"
            
            md += f"### {status_icon} {agent_name}\n"
            for t in traces:
                md += f"{t}\n"
            md += "\n"
        
        pipeline_placeholder.markdown(md)
    
    for chunk in stream_generator:
        if isinstance(chunk, dict):
            chunk_type = chunk.get("type", "")
            agent_name = chunk.get("agent", "")
            icon = chunk.get("icon", "🔧")
            
            # Create the pipeline expander on first trace
            if pipeline_container is None and chunk_type in ("trace", "tool_use", "agent_done", "pipeline_start"):
                pipeline_container = st.expander("🧠 Antigravity 5-Agent Pipeline", expanded=True)
                pipeline_placeholder = pipeline_container.empty()
            
            if chunk_type == "pipeline_start":
                agent_traces["🧠 Orchestrator"] = [f"🚀 {chunk.get('content', '')}"]
                agent_status["🧠 Orchestrator"] = "done"
                if "🧠 Orchestrator" not in agent_order:
                    agent_order.append("🧠 Orchestrator")
                _render_pipeline()
                
            elif chunk_type == "trace":
                display_name = f"{icon} {agent_name}"
                if display_name not in agent_order:
                    agent_order.append(display_name)
                    agent_traces[display_name] = []
                    agent_status[display_name] = "running"
                agent_traces[display_name].append(f"- 🔹 {chunk.get('content', '')}")
                _render_pipeline()
                
            elif chunk_type == "tool_use":
                display_name = f"{icon} {agent_name}"
                if display_name not in agent_order:
                    agent_order.append(display_name)
                    agent_traces[display_name] = []
                agent_traces[display_name].append(
                    f"- 🛠️ **`{chunk.get('tool', '')}`** → {chunk.get('result', '')}"
                )
                _render_pipeline()
                
            elif chunk_type == "agent_done":
                display_name = f"{icon} {agent_name}"
                agent_status[display_name] = "done"
                if display_name in agent_traces:
                    agent_traces[display_name].append(
                        f"- ✅ **Done:** {chunk.get('summary', '')}"
                    )
                _render_pipeline()
                
            elif chunk_type == "question_chunk":
                response_text += chunk["content"]
                response_placeholder.markdown(response_text + "▌")
                
        elif isinstance(chunk, str):
            response_text += chunk
            response_placeholder.markdown(response_text + "▌")
    
    response_placeholder.markdown(response_text)
    return response_text


def speak_text(text: str, speed: float = 1.1, lang_code: str = "en"):
    """
    Speak text using browser's TTS API with language support.
    """
    return language_support.get_language_specific_tts_html(text, lang_code, speed)


def get_persistence_loader_html():
    """HTML component to load persisted data from localStorage."""
    return '''
    <script>
    (function() {
        const data = {
            resume_text: localStorage.getItem('hiresense_resume_text') || '',
            jd_text: localStorage.getItem('hiresense_jd_text') || '',
            voice_answer: localStorage.getItem('hiresense_voice_answer') || '',
            interview_history: JSON.parse(localStorage.getItem('hiresense_interview_history') || '[]'),
            language: localStorage.getItem('hiresense_language') || 'en',
            loaded_at: Date.now()
        };
        
        sessionStorage.setItem('hiresense_persisted_data', JSON.stringify(data));
        
        if (window.parent && window.parent.postMessage) {
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: data
            }, '*');
        }
    })();
    </script>
    '''


def get_save_to_storage_html(key: str, value: str):
    """HTML component to save data to localStorage."""
    escaped_value = json.dumps(value)
    return f'''
    <script>
    (function() {{
        localStorage.setItem('hiresense_{key}', {escaped_value});
    }})();
    </script>
    '''


def init_session_state():
    """Initialize session state for the interview."""
    defaults = {
        "interview_started": False,
        "interview_resume_text": None,
        "interview_jd_text": None,
        "interview_rag_context": None,
        "interview_history": [],
        "interview_stress_timeline": [],
        "current_question_num": 0,
        "total_questions": 5,
        "current_emotional_state": "neutral",
        "interview_complete": False,
        "tts_enabled": True,
        "webcam_enabled": True,
        "voice_input_enabled": True,
        "current_stress_level": 0.5,
        "interview_start_time": None,
        "interview_report": None,
        "awaiting_question": True,
        "current_question_text": None,
        "tts_played": False,
        "interview_type": "Mixed",
        "question_bank": [],
        "current_voice_answer": "",
        "page": "interview",
        # New feature states
        "selected_language": "en",
        "selected_company": "general",
        "video_recording_enabled": False,
        "followup_enabled": True,
        "awaiting_followup": False,
        "followup_count": 0,
        "max_followups": 2,
        "skill_analysis_done": False,
        "skill_analysis_result": None,
        # New feature states for Copilot and Coding
        "copilot_enabled": False,
        "coding_mode_enabled": False,
        "current_problem": None,
        "coding_language": "python",
        # Non-verbal analysis states
        "nonverbal_analysis_done": False,
        "show_nonverbal_analysis": False,
        "nonverbal_results": None,
        "nonverbal_detailed_report": None,
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_ui_text(key: str) -> str:
    """Get translated UI text based on selected language."""
    return language_support.get_ui_text(key, st.session_state.get("selected_language", "en"))


def save_to_question_bank():
    """Save the current interview to the question bank."""
    if not st.session_state.get("interview_history"):
        return
    
    qa_pairs = []
    history = st.session_state["interview_history"]
    for i in range(0, len(history) - 1, 2):
        if i + 1 < len(history):
            qa_pairs.append({
                "question": history[i].get("content", ""),
                "answer": history[i + 1].get("content", "")
            })
    
    stress_timeline = st.session_state.get("interview_stress_timeline", [])
    avg_stress = sum(s.get("stress_level", 0.5) for s in stress_timeline) / max(len(stress_timeline), 1)
    composure_score = int((1 - avg_stress) * 100)
    
    duration = "N/A"
    if st.session_state.get("interview_start_time"):
        elapsed = time.time() - st.session_state["interview_start_time"]
        duration = f"{int(elapsed // 60)}m {int(elapsed % 60)}s"
    
    interview_record = {
        "id": f"interview_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "timestamp": datetime.now().isoformat(),
        "interview_type": st.session_state.get("interview_type", "Mixed"),
        "company": st.session_state.get("selected_company", "general"),
        "language": st.session_state.get("selected_language", "en"),
        "questions": qa_pairs,
        "metrics": {
            "composure_score": composure_score,
            "duration": duration,
            "total_questions": st.session_state.get("total_questions", 5),
            "questions_answered": len(qa_pairs)
        },
        "report": st.session_state.get("interview_report", "")
    }
    
    if "question_bank" not in st.session_state:
        st.session_state["question_bank"] = []
    
    st.session_state["question_bank"].append(interview_record)
    
    components.html(
        get_save_to_storage_html("interview_history", json.dumps(st.session_state["question_bank"])),
        height=0
    )


# ============================================================================
# Page Renderers
# ============================================================================

def render_interview_setup():
    """Render the HireSense AI interview setup interface."""
    st.markdown(f"### 📋 {get_ui_text('setup_session')}")
    
    # Language Selection (NEW)
    st.markdown("#### 🌐 " + get_ui_text('select_language'))
    lang_col1, lang_col2 = st.columns([3, 1])
    
    with lang_col1:
        languages = language_support.get_language_list()
        lang_options = {lang["display"]: lang["code"] for lang in languages}
        current_lang = st.session_state.get("selected_language", "en")
        current_display = next((lang["display"] for lang in languages if lang["code"] == current_lang), languages[0]["display"])
        
        selected_lang_display = st.selectbox(
            get_ui_text('language'),
            options=list(lang_options.keys()),
            index=list(lang_options.values()).index(current_lang) if current_lang in lang_options.values() else 0,
            key="language_selector"
        )
        st.session_state["selected_language"] = lang_options[selected_lang_display]
    
    st.markdown("---")
    
    # Company-Specific Prep (NEW)
    st.markdown("#### 🏢 Company-Specific Preparation")
    
    companies = company_prep.get_company_list()
    company_cols = st.columns(6)
    
    for i, company in enumerate(companies[:6]):
        with company_cols[i]:
            is_selected = st.session_state.get("selected_company") == company["key"]
            if st.button(
                f"{company['logo']}",
                key=f"company_{company['key']}",
                type="primary" if is_selected else "secondary",
                help=company["name"],
                width="stretch"
            ):
                st.session_state["selected_company"] = company["key"]
                st.rerun()
    
    # Show more companies in expander
    with st.expander("More Companies"):
        more_cols = st.columns(6)
        for i, company in enumerate(companies[6:]):
            with more_cols[i % 6]:
                is_selected = st.session_state.get("selected_company") == company["key"]
                if st.button(
                    f"{company['logo']} {company['name']}",
                    key=f"company_{company['key']}",
                    type="primary" if is_selected else "secondary",
                    width="stretch"
                ):
                    st.session_state["selected_company"] = company["key"]
                    st.rerun()
    
    # Show selected company info
    selected_company = st.session_state.get("selected_company", "general")
    company_info = company_prep.get_company_info(selected_company)
    
    with st.expander(f"📋 {company_info['name']} Interview Guide", expanded=False):
        st.markdown(f"**Interview Style:** {company_info['interview_style']}")
        st.markdown("**Focus Areas:**")
        for area in company_info['focus_areas']:
            st.markdown(f"- {area}")
        st.markdown("**Tips:**")
        for tip in company_info['tips'][:3]:
            st.markdown(f"💡 {tip}")
    
    st.markdown("---")
    
    # Interview Type Selection
    st.markdown(f"#### 🎯 {get_ui_text('select_interview_type')}")
    
    type_cols = st.columns(5)
    for i, (type_name, type_info) in enumerate(INTERVIEW_TYPES.items()):
        with type_cols[i]:
            is_selected = st.session_state.get("interview_type") == type_name
            button_type = "primary" if is_selected else "secondary"
            
            if st.button(
                f"{type_info['icon']} {type_name}",
                key=f"type_{type_name}",
                type=button_type,
                width="stretch"
            ):
                st.session_state["interview_type"] = type_name
                st.rerun()
    
    selected_type = st.session_state.get("interview_type", "Mixed")
    type_info = INTERVIEW_TYPES[selected_type]
    st.info(f"**{type_info['icon']} {selected_type}:** {type_info['description']}")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"#### 📄 {get_ui_text('upload_resume')}")
        resume_file = st.file_uploader(
            "Upload your resume (PDF)",
            type=["pdf"],
            key="interview_resume_upload",
            help="Your resume will be used to personalize interview questions"
        )
        
        if resume_file:
            with st.spinner("Processing resume..."):
                resume_bytes = resume_file.getvalue()
                resume_text = arena.extract_pdf_text(resume_bytes)
                st.session_state["interview_resume_text"] = resume_text
                st.success(f"✅ Resume loaded: {resume_file.name}")
                
                components.html(get_save_to_storage_html("resume_text", resume_text), height=0)
                
                with st.expander("Preview Resume Content"):
                    st.text(resume_text[:1000] + "..." if len(resume_text) > 1000 else resume_text)
    
    with col2:
        st.markdown(f"#### 📋 {get_ui_text('job_description')}")
        jd_input_method = st.radio(
            "How would you like to provide the JD?",
            ["Upload PDF", "Paste Text"],
            horizontal=True,
            key="jd_input_method"
        )
        
        if jd_input_method == "Upload PDF":
            jd_file = st.file_uploader(
                "Upload job description (PDF)",
                type=["pdf"],
                key="interview_jd_upload"
            )
            if jd_file:
                with st.spinner("Processing JD..."):
                    jd_bytes = jd_file.getvalue()
                    jd_text = arena.extract_pdf_text(jd_bytes)
                    st.session_state["interview_jd_text"] = jd_text
                    st.success(f"✅ JD loaded: {jd_file.name}")
                    
                    components.html(get_save_to_storage_html("jd_text", jd_text), height=0)
        else:
            jd_text = st.text_area(
                "Paste job description here",
                height=200,
                key="interview_jd_text_input",
                placeholder="Paste the job description for the position you're applying for..."
            )
            if jd_text:
                st.session_state["interview_jd_text"] = jd_text
                components.html(get_save_to_storage_html("jd_text", jd_text), height=0)
    
    st.markdown("---")
    
    # Skill Gap Analysis (NEW)
    if st.session_state.get("interview_resume_text") and st.session_state.get("interview_jd_text"):
        st.markdown("#### 📊 Skill Gap Analysis")
        
        if not st.session_state.get("skill_analysis_done"):
            if st.button("🔍 Analyze Skill Gaps", type="secondary"):
                with st.spinner("Analyzing skills and gaps..."):
                    result = skill_gap_analysis.run_full_skill_analysis(
                        st.session_state["interview_resume_text"],
                        st.session_state["interview_jd_text"]
                    )
                    st.session_state["skill_analysis_result"] = result
                    st.session_state["skill_analysis_done"] = True
                    st.rerun()
        else:
            result = st.session_state.get("skill_analysis_result", {})
            stats = result.get("summary_stats", {})
            
            # Display summary metrics
            metric_cols = st.columns(4)
            with metric_cols[0]:
                st.metric("Match Score", f"{stats.get('overall_score', 0)}%")
            with metric_cols[1]:
                st.metric("Matching Skills", stats.get('matching_count', 0))
            with metric_cols[2]:
                st.metric("Skill Gaps", stats.get('gap_count', 0))
            with metric_cols[3]:
                st.metric("Exceeding", stats.get('exceeding_count', 0))
            
            with st.expander("📋 View Full Analysis"):
                st.markdown(result.get("formatted_report", "No analysis available"))
                
                # Radar chart
                radar_data = result.get("radar_data", {})
                if radar_data.get("categories"):
                    components.html(
                        skill_gap_analysis.get_skill_gap_chart_html(radar_data),
                        height=350
                    )
            
            if st.button("🔄 Re-analyze"):
                st.session_state["skill_analysis_done"] = False
                st.rerun()
    
    st.markdown("---")
    st.markdown(f"### ⚙️ {get_ui_text('session_settings')}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        num_questions = st.slider(
            get_ui_text('num_questions'),
            min_value=3,
            max_value=10,
            value=5,
            key="num_questions_slider"
        )
        st.session_state["total_questions"] = num_questions
    
    with col2:
        st.session_state["tts_enabled"] = st.checkbox(
            f"🔊 {get_ui_text('enable_voice')}",
            value=True,
            help="AI will speak questions aloud"
        )
    
    with col3:
        st.session_state["webcam_enabled"] = st.checkbox(
            f"📹 {get_ui_text('enable_webcam')}",
            value=True,
            help="Real-time emotion detection"
        )
    
    with col4:
        st.session_state["voice_input_enabled"] = st.checkbox(
            f"🎤 {get_ui_text('enable_voice_input')}",
            value=True,
            help="Speak your answers instead of typing"
        )
    
    # New feature settings
    col5, col6 = st.columns(2)
    
    with col5:
        st.session_state["video_recording_enabled"] = st.checkbox(
            "🎬 Enable Video Recording",
            value=False,
            help="Record your interview session for later review"
        )
    
    with col6:
        st.session_state["followup_enabled"] = st.checkbox(
            "🔄 Enable AI Follow-up Questions",
            value=True,
            help="AI will ask follow-up questions based on your answers"
        )
    
    st.markdown("---")
    
    # Start Session Button
    can_start = (
        st.session_state.get("interview_resume_text") and 
        st.session_state.get("interview_jd_text")
    )
    
    if not can_start:
        st.warning("⚠️ Please upload both your resume and job description to start your HireSense session.")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            f"🚀 {get_ui_text('start_session')}",
            type="primary",
            disabled=not can_start,
            width="stretch"
        ):
            # Build RAG context with company-specific info
            resume_data = arena.parse_resume(st.session_state["interview_resume_text"])
            jd_data = arena.parse_job_description(st.session_state["interview_jd_text"])
            base_context = arena.build_rag_context(resume_data, jd_data)
            
            # Add company-specific context
            company_prompt = company_prep.get_company_interview_prompt(
                st.session_state.get("selected_company", "general")
            )
            
            # Add language instruction
            lang_prompt = language_support.get_interview_language_prompt(
                st.session_state.get("selected_language", "en")
            )
            
            st.session_state["interview_rag_context"] = f"{base_context}\n\n{company_prompt}\n\n{lang_prompt}"
            
            # Reset interview state
            st.session_state["interview_started"] = True
            st.session_state["interview_history"] = []
            
            # Reset the Antigravity orchestrator for a fresh pipeline
            try:
                from antigravity_agent import reset_orchestrator
                reset_orchestrator()
            except ImportError:
                pass
            st.session_state["interview_stress_timeline"] = []
            st.session_state["current_question_num"] = 1
            st.session_state["interview_complete"] = False
            st.session_state["interview_start_time"] = time.time()
            st.session_state["awaiting_question"] = True
            st.session_state["interview_report"] = None
            st.session_state["current_question_text"] = None
            st.session_state["tts_played"] = False
            st.session_state["current_voice_answer"] = ""
            st.session_state["followup_count"] = 0
            st.session_state["awaiting_followup"] = False
            
            # Initialize video recording if enabled
            if st.session_state.get("video_recording_enabled"):
                video_recording.start_recording_session()
            
            st.rerun()


def render_active_interview():
    """Render the active HireSense AI interview interface."""
    interview_type = st.session_state.get("interview_type", "Mixed")
    type_info = INTERVIEW_TYPES.get(interview_type, INTERVIEW_TYPES["Mixed"])
    company_info = company_prep.get_company_info(st.session_state.get("selected_company", "general"))
    
    st.markdown(f"### {type_info['icon']} HireSense {interview_type} Interview")
    st.caption(f"🏢 {company_info['name']} | 🌐 {language_support.get_language_info(st.session_state.get('selected_language', 'en'))['name']}")
    
    # Progress indicator
    progress = st.session_state["current_question_num"] / st.session_state["total_questions"]
    st.progress(progress, text=f"Question {st.session_state['current_question_num']} of {st.session_state['total_questions']}")
    
    # Main interview layout
    col1, col2 = st.columns([3, 1])
    
    with col2:
        # Emotion status panel
        st.markdown(f"#### 📊 {get_ui_text('live_status')}")
        
        # Video Recording (NEW)
        if st.session_state.get("video_recording_enabled"):
            with st.expander("🎬 Video Recording", expanded=True):
                video_recording.render_video_recorder(
                    height=400,
                    session_id=st.session_state.get("recording_session_id", "default")
                )
        
        # Webcam and emotion display
        if st.session_state["webcam_enabled"] and not st.session_state.get("video_recording_enabled"):
            st.components.v1.html(webcam.get_simple_webcam_html(), height=400)
        
        # Manual stress level adjustment (collapsed by default)
        with st.expander("🎛️ Manual Stress Control", expanded=False):
            manual_stress = st.slider(
                "Simulate stress level:",
                0.0, 1.0, 
                st.session_state.get("current_stress_level", 0.5),
                key="manual_stress_slider",
                help="Use this to test adaptive AI behavior"
            )
            st.session_state["current_stress_level"] = manual_stress
        
        # Current emotional state display
        stress_level = st.session_state.get("current_stress_level", 0.5)
        emotional_state = get_ui_text('confident') + " 😊" if stress_level <= 0.5 else get_ui_text('stressed') + " 😰"
        state_color = "🟢" if stress_level < 0.4 else "🟡" if stress_level <= 0.7 else "🔴"
        
        st.markdown(f"**{get_ui_text('emotional_state')}**")
        st.markdown(f"### {emotional_state}")
        st.markdown(f"{state_color} {stress_level:.0%} stress")
        
        # AI Mode indicator
        ai_mode = st.session_state.get("current_emotional_state", "neutral")
        mode_display = {
            "stressed": f"🤗 {get_ui_text('supportive_mode')}",
            "confident": f"💪 {get_ui_text('challenge_mode')}",
            "neutral": f"⚖️ {get_ui_text('balanced_mode')}"
        }
        st.info(f"**{get_ui_text('ai_mode')}:** {mode_display.get(ai_mode, get_ui_text('balanced_mode'))}")
        
        st.markdown("")  # Add spacing
        
        # Quick stats
        st.markdown("---")
        st.markdown(f"**{get_ui_text('session_stats')}**")
        if st.session_state["interview_start_time"]:
            elapsed = time.time() - st.session_state["interview_start_time"]
            st.write(f"⏱️ {get_ui_text('duration')}: {int(elapsed // 60)}m {int(elapsed % 60)}s")
        st.write(f"💬 {get_ui_text('exchanges')}: {len(st.session_state['interview_history']) // 2}")
        
        if st.session_state.get("followup_enabled"):
            st.write(f"🔄 Follow-ups: {st.session_state.get('followup_count', 0)}")
    
    with col1:
        # Conversation display
        st.markdown(f"#### 💬 HireSense Interview")
        
        # Display conversation history
        conversation_container = st.container()
        with conversation_container:
            for entry in st.session_state["interview_history"]:
                if entry["role"] == "assistant":
                    st.markdown(f"**🤖 HireSense AI:** {entry['content']}")
                else:
                    st.markdown(f"**👤 You:** {entry['content']}")
                st.markdown("---")
        
        # Generate question if needed
        should_generate = (
            st.session_state["awaiting_question"] and
            st.session_state["current_question_num"] <= st.session_state["total_questions"] and
            not st.session_state.get("awaiting_followup", False)
        )
        
        if should_generate:
            with st.spinner("🤔 HireSense AI is preparing the next question..."):
                # Update emotional state based on stress level
                stress = st.session_state.get("current_stress_level", 0.5)
                if stress > 0.6:
                    st.session_state["current_emotional_state"] = "stressed"
                elif stress < 0.4:
                    st.session_state["current_emotional_state"] = "confident"
                else:
                    st.session_state["current_emotional_state"] = "neutral"
                
                # Generate question with interview type
                question_gen = arena.generate_interview_question(
                    st.session_state["interview_rag_context"],
                    st.session_state["interview_history"],
                    st.session_state["current_emotional_state"],
                    st.session_state["current_question_num"],
                    st.session_state["total_questions"],
                    st.session_state.get("interview_type", "Mixed")
                )
                
                st.markdown("**🤖 HireSense AI:**")
                question_text = display_streaming_response(question_gen)
                
                # Add to history
                st.session_state["interview_history"].append({
                    "role": "assistant",
                    "content": question_text,
                    "timestamp": time.time(),
                    "is_followup": False
                })
                
                # Add video marker for question
                if st.session_state.get("video_recording_enabled"):
                    components.html(
                        video_recording.add_question_marker_js(st.session_state["current_question_num"]),
                        height=0
                    )
                
                st.session_state["current_question_text"] = question_text
                st.session_state["tts_played"] = False
                st.session_state["awaiting_question"] = False
                st.session_state["followup_count"] = 0
                
                st.rerun()
        
        # Generate follow-up question if needed (NEW)
        if st.session_state.get("awaiting_followup", False):
            with st.spinner("🤔 HireSense AI is preparing a follow-up question..."):
                # Get the last Q&A pair
                history = st.session_state["interview_history"]
                if len(history) >= 2:
                    last_question = history[-2]["content"]
                    last_answer = history[-1]["content"]
                    
                    followup_gen = followup_questions.generate_smart_followup(
                        original_question=last_question,
                        candidate_answer=last_answer,
                        rag_context=st.session_state.get("interview_rag_context", ""),
                        interview_type=st.session_state.get("interview_type", "Mixed"),
                        emotional_state=st.session_state.get("current_emotional_state", "neutral"),
                        language=st.session_state.get("selected_language", "en")
                    )
                    
                    st.markdown("**🤖 HireSense AI (Follow-up):**")
                    followup_text = display_streaming_response(followup_gen)
                    
                    st.session_state["interview_history"].append({
                        "role": "assistant",
                        "content": followup_text,
                        "timestamp": time.time(),
                        "is_followup": True
                    })
                    
                    st.session_state["current_question_text"] = followup_text
                    st.session_state["tts_played"] = False
                    st.session_state["awaiting_followup"] = False
                    st.session_state["followup_count"] += 1
                    
                    st.rerun()
        
        # Play TTS for current question
        if (st.session_state["tts_enabled"] and 
            st.session_state.get("current_question_text") and 
            not st.session_state.get("tts_played", True) and
            not st.session_state["awaiting_question"]):
            
            tts_html = speak_text(
                st.session_state["current_question_text"], 
                speed=1.1,
                lang_code=st.session_state.get("selected_language", "en")
            )
            st.components.v1.html(tts_html, height=0)
            st.session_state["tts_played"] = True
        
        # Answer input
        if not st.session_state["awaiting_question"] and not st.session_state.get("awaiting_followup", False):
            st.markdown(f"#### ✍️ {get_ui_text('your_response')}")
            
            # Voice input section
            if st.session_state.get("voice_input_enabled", True):
                with st.expander(f"🎤 {get_ui_text('speak_your_answer')}", expanded=True):
                    # Get speech recognition language code
                    speech_lang = language_support.get_speech_recognition_code(
                        st.session_state.get("selected_language", "en")
                    )
                    voice_input.render_voice_input(
                        height=420, 
                        key=f"q{st.session_state['current_question_num']}_f{st.session_state.get('followup_count', 0)}",
                        language_code=speech_lang
                    )
                    st.caption(f"💡 Click '{get_ui_text('use_this_answer')}' to fill the text box below")
            
            # Text input
            answer_key = f"answer_{st.session_state['current_question_num']}_{st.session_state.get('followup_count', 0)}"
            
            user_answer = st.text_area(
                "Your answer:",
                value=st.session_state.get("current_voice_answer", ""),
                height=150,
                key=answer_key,
                placeholder="Type your answer here, or use voice input above..."
            )
            
            col_submit, col_followup, col_skip, col_end = st.columns(4)
            
            with col_submit:
                if st.button(f"📤 {get_ui_text('submit_answer')}", type="primary", disabled=not user_answer):
                    # Record stress
                    st.session_state["interview_stress_timeline"].append({
                        "timestamp": time.time() - st.session_state["interview_start_time"],
                        "stress_level": st.session_state.get("current_stress_level", 0.5),
                        "question_num": st.session_state["current_question_num"]
                    })
                    
                    # Add answer to history
                    st.session_state["interview_history"].append({
                        "role": "user",
                        "content": user_answer,
                        "timestamp": time.time()
                    })
                    
                    # Check if we should ask a follow-up
                    should_followup = (
                        st.session_state.get("followup_enabled", True) and
                        st.session_state.get("followup_count", 0) < st.session_state.get("max_followups", 2) and
                        len(user_answer.split()) >= 15  # Only follow up on substantial answers
                    )
                    
                    if should_followup:
                        # 50% chance of follow-up to keep it natural
                        import random
                        if random.random() < 0.5:
                            st.session_state["awaiting_followup"] = True
                        else:
                            # Move to next question
                            st.session_state["current_question_num"] += 1
                            st.session_state["awaiting_question"] = True
                    else:
                        # Move to next question
                        st.session_state["current_question_num"] += 1
                        st.session_state["awaiting_question"] = True
                    
                    st.session_state["current_question_text"] = None
                    st.session_state["tts_played"] = False
                    st.session_state["current_voice_answer"] = ""
                    
                    if st.session_state["current_question_num"] > st.session_state["total_questions"]:
                        st.session_state["interview_complete"] = True
                        save_to_question_bank()
                    
                    st.rerun()
            
            with col_followup:
                # Manual follow-up request (NEW)
                if st.session_state.get("followup_enabled") and st.session_state.get("followup_count", 0) < 2:
                    if st.button("🔄 Ask Follow-up", disabled=not user_answer):
                        st.session_state["interview_stress_timeline"].append({
                            "timestamp": time.time() - st.session_state["interview_start_time"],
                            "stress_level": st.session_state.get("current_stress_level", 0.5),
                            "question_num": st.session_state["current_question_num"]
                        })
                        
                        st.session_state["interview_history"].append({
                            "role": "user",
                            "content": user_answer,
                            "timestamp": time.time()
                        })
                        
                        st.session_state["awaiting_followup"] = True
                        st.session_state["current_question_text"] = None
                        st.session_state["current_voice_answer"] = ""
                        st.rerun()
            
            with col_skip:
                if st.button(f"⏭️ {get_ui_text('skip_question')}"):
                    st.session_state["interview_stress_timeline"].append({
                        "timestamp": time.time() - st.session_state["interview_start_time"],
                        "stress_level": st.session_state.get("current_stress_level", 0.5),
                        "question_num": st.session_state["current_question_num"]
                    })
                    
                    st.session_state["interview_history"].append({
                        "role": "user",
                        "content": "[Skipped]",
                        "timestamp": time.time()
                    })
                    st.session_state["current_question_num"] += 1
                    st.session_state["awaiting_question"] = True
                    st.session_state["awaiting_followup"] = False
                    st.session_state["current_question_text"] = None
                    st.session_state["tts_played"] = False
                    st.session_state["current_voice_answer"] = ""
                    
                    if st.session_state["current_question_num"] > st.session_state["total_questions"]:
                        st.session_state["interview_complete"] = True
                        save_to_question_bank()
                    
                    st.rerun()
            
            with col_end:
                if st.button(f"🛑 {get_ui_text('end_session')}"):
                    st.session_state["interview_complete"] = True
                    save_to_question_bank()
                    st.rerun()


def render_interview_results():
    """Render the HireSense Report and analytics dashboard."""
    st.markdown(f"### 🏆 {get_ui_text('session_complete')}")
    st.balloons()
    
    # Stop video recording if enabled
    if st.session_state.get("video_recording_enabled"):
        video_recording.stop_recording_session()
        st.info("📹 Your interview recording has been saved. You can download it from the recording panel.")
    
    # Analytics dashboard
    st.markdown("---")
    st.markdown(f"## 📊 {get_ui_text('performance_analytics')}")
    
    metrics = analytics.render_full_dashboard(
        st.session_state["interview_stress_timeline"],
        st.session_state["interview_history"],
        st.session_state["total_questions"],
        st.session_state.get("interview_report")
    )
    
    st.markdown("---")
    
    # Generate AI Report Card
    st.markdown(f"### 📋 {get_ui_text('ai_report')}")
    
    if not st.session_state.get("interview_report"):
        if st.button(f"📝 {get_ui_text('generate_report')}", type="primary"):
            with st.spinner("🤖 HireSense AI is analyzing your performance..."):
                # Include company-specific evaluation
                company_report_prompt = company_prep.get_company_report_prompt(
                    st.session_state.get("selected_company", "general")
                )
                
                enhanced_context = f"{st.session_state['interview_rag_context']}\n\n{company_report_prompt}"
                
                report_gen = arena.generate_final_report(
                    enhanced_context,
                    st.session_state["interview_history"],
                    st.session_state["interview_stress_timeline"]
                )
                
                report_text = display_streaming_response(report_gen)
                st.session_state["interview_report"] = report_text
                
                if st.session_state.get("question_bank"):
                    st.session_state["question_bank"][-1]["report"] = report_text
                    components.html(
                        get_save_to_storage_html("interview_history", json.dumps(st.session_state["question_bank"])),
                        height=0
                    )
                
                st.rerun()
    else:
        with st.expander(f"📄 {get_ui_text('view_report')}", expanded=True):
            st.markdown(st.session_state["interview_report"])
    
    # Skill Gap Analysis in Results (NEW)
    if st.session_state.get("skill_analysis_result"):
        st.markdown("---")
        st.markdown("### 📊 Skill Gap Analysis")
        
        result = st.session_state["skill_analysis_result"]
        gap_analysis = result.get("gap_analysis", {})
        
        # Show development priorities
        priorities = gap_analysis.get("development_priorities", [])
        if priorities:
            st.markdown("#### 🎯 Development Priorities")
            for priority in priorities[:3]:
                with st.expander(f"📚 {priority.get('area', 'Unknown')}"):
                    st.markdown(f"**Current Gap:** {priority.get('current_gap', 'Unknown')}")
                    st.markdown(f"**Timeline:** {priority.get('timeline', 'Unknown')}")
                    st.markdown("**Recommended Actions:**")
                    for action in priority.get("recommended_actions", []):
                        st.markdown(f"- {action}")
        
        # Generate learning path
        if st.button("📚 Generate Learning Path"):
            skill_gaps = gap_analysis.get("skill_gaps", [])
            if skill_gaps:
                with st.spinner("Generating personalized learning path..."):
                    learning_gen = skill_gap_analysis.generate_learning_path(skill_gaps)
                    learning_path = display_streaming_response(learning_gen)
    
    st.markdown("---")
    
    # Interview Transcript
    with st.expander(f"💬 {get_ui_text('full_transcript')}"):
        for entry in st.session_state["interview_history"]:
            role = "🤖 HireSense AI" if entry["role"] == "assistant" else "👤 You"
            followup_tag = " (Follow-up)" if entry.get("is_followup") else ""
            st.markdown(f"**{role}{followup_tag}:** {entry['content']}")
            st.markdown("---")
    
    # Video Recording Playback (NEW)
    if st.session_state.get("video_recording_enabled"):
        with st.expander("📹 Interview Recording"):
            video_recording.render_recordings_list(height=200)
    
    # Non-Verbal Communication Analysis (NEW)
    if st.session_state.get("video_recording_enabled"):
        st.markdown("---")
        st.markdown("### 🔍 Advanced Non-Verbal Analysis")
        st.markdown("Analyze your eye contact, posture, and filler word usage from your recorded interview.")
        
        # Check if analysis has been done
        if not st.session_state.get("nonverbal_analysis_done"):
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("🚀 Analyze Non-Verbal Communication", type="primary", use_container_width=True):
                    st.session_state["show_nonverbal_analysis"] = True
                    st.rerun()
        
        # Show analysis component
        if st.session_state.get("show_nonverbal_analysis"):
            st.info("🔄 Analysis in progress... This may take a few moments.")
            
            # Render the analysis component
            components.html(
                nonverbal_analysis.get_nonverbal_analysis_component_html(
                    video_blob_url="",  # Will be populated from sessionStorage
                    height=700
                ),
                height=720
            )
            
            # Display results if available
            if st.session_state.get("nonverbal_results"):
                results = st.session_state["nonverbal_results"]
                
                st.markdown("#### 🎯 Analysis Results")
                
                # Metrics row
                metric_cols = st.columns(4)
                with metric_cols[0]:
                    st.metric(
                        "🎯 Overall Score",
                        f"{results.get('overall', {}).get('score', 'N/A')}/100",
                        delta=results.get('overall', {}).get('rating', '')
                    )
                with metric_cols[1]:
                    st.metric(
                        "👁️ Eye Contact",
                        f"{results.get('eyeContact', {}).get('percentage', 'N/A')}%"
                    )
                with metric_cols[2]:
                    st.metric(
                        "🪑 Posture",
                        f"{results.get('posture', {}).get('score', 'N/A')}/100"
                    )
                with metric_cols[3]:
                    st.metric(
                        "🗣️ Filler Words",
                        f"{results.get('fillerWords', {}).get('percentage', 'N/A')}%"
                    )
                
                # Detailed AI analysis
                if st.button("🤖 Generate Detailed AI Analysis"):
                    with st.spinner("Generating detailed analysis..."):
                        # Create analysis result object
                        analysis_result = nonverbal_analysis.NonVerbalAnalysisResult(
                            session_id="current",
                            analysis_timestamp=datetime.now().isoformat(),
                            video_duration_seconds=st.session_state.get("interview_duration", 300),
                            eye_contact=nonverbal_analysis.EyeContactMetrics(
                                total_duration_seconds=st.session_state.get("interview_duration", 300),
                                looking_at_camera_seconds=0,
                                looking_away_seconds=0,
                                eye_contact_percentage=results.get('eyeContact', {}).get('percentage', 0),
                                longest_eye_contact_streak=results.get('eyeContact', {}).get('longestStreak', 0),
                                average_gaze_duration=0,
                                look_away_count=results.get('eyeContact', {}).get('lookAwayCount', 0),
                                rating=nonverbal_analysis.calculate_eye_contact_rating(
                                    results.get('eyeContact', {}).get('percentage', 0)
                                ),
                                feedback=""
                            ),
                            posture=nonverbal_analysis.PostureMetrics(
                                total_frames_analyzed=100,
                                good_posture_frames=results.get('posture', {}).get('score', 0),
                                slouching_frames=results.get('posture', {}).get('slouching', 0),
                                leaning_frames=results.get('posture', {}).get('leaning', 0),
                                posture_score=results.get('posture', {}).get('score', 0),
                                confidence_indicators=[],
                                improvement_areas=[],
                                rating=nonverbal_analysis.calculate_posture_rating(
                                    results.get('posture', {}).get('score', 0)
                                ),
                                feedback=""
                            ),
                            filler_words=nonverbal_analysis.FillerWordMetrics(
                                total_words_spoken=results.get('fillerWords', {}).get('total', 0) * 20,
                                total_filler_words=results.get('fillerWords', {}).get('total', 0),
                                filler_word_percentage=results.get('fillerWords', {}).get('percentage', 0),
                                filler_breakdown=results.get('fillerWords', {}).get('breakdown', {}),
                                words_per_minute=120,
                                filler_words_per_minute=0,
                                rating="good",
                                feedback="",
                                worst_offenders=list(results.get('fillerWords', {}).get('breakdown', {}).items())[:5]
                            ),
                            overall_score=results.get('overall', {}).get('score', 0),
                            overall_rating=results.get('overall', {}).get('rating', 'N/A'),
                            key_strengths=[],
                            areas_for_improvement=[],
                            personalized_tips=[]
                        )
                        
                        # Generate detailed report
                        report_gen = nonverbal_analysis.generate_detailed_analysis_report(
                            analysis_result,
                            interview_context=st.session_state.get("interview_type", "General")
                        )
                        
                        detailed_report = display_streaming_response(report_gen)
                        st.session_state["nonverbal_detailed_report"] = detailed_report
                
                # Show detailed report if generated
                if st.session_state.get("nonverbal_detailed_report"):
                    with st.expander("📝 Detailed Non-Verbal Analysis Report", expanded=True):
                        st.markdown(st.session_state["nonverbal_detailed_report"])
    
    # Restart option
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(f"🔄 {get_ui_text('start_new_session')}", type="primary", width="stretch"):
            keys_to_reset = [
                "interview_started", "interview_complete", "interview_history",
                "interview_stress_timeline", "current_question_num", "interview_report",
                "awaiting_question", "interview_start_time",
                "current_question_text", "tts_played", "current_voice_answer",
                "followup_count", "awaiting_followup", "skill_analysis_done"
            ]
            for key in keys_to_reset:
                if key in st.session_state:
                    if key == "interview_history" or key == "interview_stress_timeline":
                        st.session_state[key] = []
                    elif key == "current_question_num":
                        st.session_state[key] = 0
                    elif key == "followup_count":
                        st.session_state[key] = 0
                    elif key in ["interview_started", "interview_complete", "tts_played", 
                                "awaiting_followup", "skill_analysis_done"]:
                        st.session_state[key] = False
                    else:
                        st.session_state[key] = None
            st.rerun()


def render_question_bank():
    """Render the Question Bank page showing past interviews."""
    st.markdown(f"### 📚 {get_ui_text('question_bank')}")
    st.markdown("Review your past interviews and practice questions.")
    
    history = st.session_state.get("question_bank", [])
    
    if not history:
        st.info("🎯 No past interviews yet. Complete an interview to build your question bank!")
        
        if st.button("🚀 Start Your First Interview", type="primary"):
            st.session_state["page"] = "interview"
            st.rerun()
        return
    
    st.write(f"**{len(history)} past interview(s)**")
    
    # Filter by type
    all_types = list(set(i.get("interview_type", "Mixed") for i in history))
    selected_filter = st.selectbox("Filter by type:", ["All"] + all_types)
    
    # Filter by company (NEW)
    all_companies = list(set(i.get("company", "general") for i in history))
    company_names = {c: company_prep.get_company_info(c)["name"] for c in all_companies}
    selected_company_filter = st.selectbox(
        "Filter by company:", 
        ["All"] + [company_names.get(c, c) for c in all_companies]
    )
    
    filtered_history = history
    if selected_filter != "All":
        filtered_history = [i for i in filtered_history if i.get("interview_type") == selected_filter]
    if selected_company_filter != "All":
        company_key = next((k for k, v in company_names.items() if v == selected_company_filter), None)
        if company_key:
            filtered_history = [i for i in filtered_history if i.get("company") == company_key]
    
    for interview in reversed(filtered_history):
        timestamp = interview.get("timestamp", "Unknown date")
        interview_type = interview.get("interview_type", "General")
        company = interview.get("company", "general")
        company_info = company_prep.get_company_info(company)
        questions = interview.get("questions", [])
        metrics = interview.get("metrics", {})
        type_info = INTERVIEW_TYPES.get(interview_type, INTERVIEW_TYPES["Mixed"])
        
        with st.expander(
            f"{type_info['icon']} {interview_type} @ {company_info['logo']} {company_info['name']} - {timestamp[:10]} ({len(questions)} Q&A)",
            expanded=False
        ):
            # Metrics row
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Questions", metrics.get("questions_answered", len(questions)))
            with col2:
                st.metric("Composure", f"{metrics.get('composure_score', 'N/A')}%")
            with col3:
                st.metric("Duration", metrics.get("duration", "N/A"))
            with col4:
                st.metric("Type", interview_type)
            
            st.markdown("---")
            
            # Questions and answers
            for j, qa in enumerate(questions):
                question = qa.get("question", "N/A")
                answer = qa.get("answer", "N/A")
                
                st.markdown(f"**Q{j+1}:** {question}")
                
                if answer == "[Skipped]":
                    st.warning("*Skipped*")
                else:
                    st.markdown(f"**Your answer:** {answer}")
                
                st.markdown("---")
            
            # Report
            report = interview.get("report")
            if report:
                with st.expander("📋 View AI Report"):
                    st.markdown(report)
    
    # Clear history button
    st.markdown("---")
    if st.button("🗑️ Clear All History", type="secondary"):
        st.session_state["question_bank"] = []
        components.html(
            '''<script>localStorage.removeItem('hiresense_interview_history');</script>''',
            height=0
        )
        st.rerun()


def render_skill_analysis_page():
    """Render dedicated Skill Gap Analysis page (NEW)."""
    st.markdown("### 📊 Skill Gap Analysis")
    st.markdown("Analyze the gap between your skills and job requirements.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📄 Your Resume")
        resume_text = st.text_area(
            "Paste your resume text",
            height=300,
            key="skill_resume_input",
            value=st.session_state.get("interview_resume_text", ""),
            placeholder="Paste your resume content here..."
        )
    
    with col2:
        st.markdown("#### 📋 Job Description")
        jd_text = st.text_area(
            "Paste the job description",
            height=300,
            key="skill_jd_input",
            value=st.session_state.get("interview_jd_text", ""),
            placeholder="Paste the job description here..."
        )
    
    if st.button("🔍 Analyze Skills", type="primary", disabled=not (resume_text and jd_text)):
        with st.spinner("Analyzing skills and identifying gaps..."):
            result = skill_gap_analysis.run_full_skill_analysis(resume_text, jd_text)
            st.session_state["skill_page_result"] = result
    
    if st.session_state.get("skill_page_result"):
        result = st.session_state["skill_page_result"]
        stats = result.get("summary_stats", {})
        gap_analysis = result.get("gap_analysis", {})
        
        st.markdown("---")
        
        # Summary metrics
        metric_cols = st.columns(5)
        with metric_cols[0]:
            score = stats.get('overall_score', 0)
            st.metric("Match Score", f"{score}%")
        with metric_cols[1]:
            st.metric("Category", stats.get('match_category', 'Unknown'))
        with metric_cols[2]:
            st.metric("Matching", stats.get('matching_count', 0))
        with metric_cols[3]:
            st.metric("Gaps", stats.get('gap_count', 0))
        with metric_cols[4]:
            st.metric("Exceeding", stats.get('exceeding_count', 0))
        
        # Radar chart
        st.markdown("---")
        st.markdown("#### 📈 Skill Category Analysis")
        radar_data = result.get("radar_data", {})
        if radar_data.get("categories"):
            components.html(
                skill_gap_analysis.get_skill_gap_chart_html(radar_data),
                height=400
            )
        
        # Detailed report
        st.markdown("---")
        st.markdown("#### 📋 Detailed Analysis")
        st.markdown(result.get("formatted_report", "No analysis available"))
        
        # Learning path generation
        st.markdown("---")
        st.markdown("#### 📚 Learning Path")
        
        skill_gaps = gap_analysis.get("skill_gaps", [])
        if skill_gaps:
            timeline = st.slider("Target timeline (months)", 1, 12, 3)
            
            if st.button("Generate Personalized Learning Path"):
                with st.spinner("Creating your learning path..."):
                    learning_gen = skill_gap_analysis.generate_learning_path(
                        skill_gaps, 
                        target_timeline_months=timeline
                    )
                    learning_path = display_streaming_response(learning_gen)


def render_copilot_page():
    """Render the Live Interview Copilot page (NEW)."""
    st.markdown("### 🤖 Live Interview Copilot")
    st.markdown("Get real-time assistance during your actual interviews on Zoom, Teams, or Meet.")
    
    st.info("""
    **How it works:**
    1. Upload your resume and job description below
    2. Start the copilot before your interview
    3. The copilot will listen and provide smart suggestions in real-time
    4. Get STAR-formatted answers, key points to mention, and confidence boosts
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📄 Your Resume")
        resume_text = st.text_area(
            "Paste your resume text",
            height=200,
            key="copilot_resume_input",
            value=st.session_state.get("interview_resume_text", ""),
            placeholder="Paste your resume content here..."
        )
        if resume_text:
            st.session_state["interview_resume_text"] = resume_text
    
    with col2:
        st.markdown("#### 📋 Job Description")
        jd_text = st.text_area(
            "Paste the job description",
            height=200,
            key="copilot_jd_input",
            value=st.session_state.get("interview_jd_text", ""),
            placeholder="Paste the job description here..."
        )
        if jd_text:
            st.session_state["interview_jd_text"] = jd_text
    
    st.markdown("---")
    
    # Copilot activation
    if resume_text and jd_text:
        st.success("✅ Resume and Job Description loaded. You're ready to start the copilot!")
        
        st.markdown("### 🎯 Interview Copilot")
        st.markdown("The copilot will listen to your interview and provide real-time suggestions.")
        
        # Render the copilot component
        live_copilot.render_copilot_component(
            resume_text=resume_text,
            jd_text=jd_text,
            height=700
        )
    else:
        st.warning("⚠️ Please provide both your resume and the job description to activate the copilot.")


def render_coding_page():
    """Render the Integrated Coding & Whiteboard page (NEW)."""
    st.markdown("### 💻 Coding Practice & Whiteboard")
    st.markdown("Practice coding problems and system design with an integrated environment.")
    
    # Problem selection
    st.markdown("#### 🎯 Select a Problem Category")
    
    problem_templates = coding_whiteboard.get_problem_selector()
    
    # Category selection
    category_cols = st.columns(len(problem_templates))
    selected_category = st.session_state.get("selected_problem_category", "arrays")
    
    for i, (cat_key, cat_data) in enumerate(problem_templates.items()):
        with category_cols[i]:
            is_selected = selected_category == cat_key
            if st.button(
                f"{cat_data['icon']} {cat_data['name']}",
                key=f"cat_{cat_key}",
                type="primary" if is_selected else "secondary",
                use_container_width=True
            ):
                st.session_state["selected_problem_category"] = cat_key
                st.session_state["current_problem"] = None
                st.rerun()
    
    # Problem selection within category
    if selected_category:
        category_data = problem_templates.get(selected_category, {})
        problems = category_data.get("problems", [])
        
        if problems:
            st.markdown(f"#### 📝 {category_data['name']} Problems")
            
            problem_options = [f"{p['title']} ({p['difficulty']})" for p in problems]
            selected_problem_idx = st.selectbox(
                "Choose a problem:",
                range(len(problem_options)),
                format_func=lambda x: problem_options[x],
                key="problem_selector"
            )
            
            if selected_problem_idx is not None:
                st.session_state["current_problem"] = problems[selected_problem_idx]
    
    # Language selection
    st.markdown("---")
    languages = coding_whiteboard.get_supported_languages()
    lang_options = {v['name']: k for k, v in languages.items()}
    
    selected_lang_name = st.selectbox(
        "Programming Language:",
        list(lang_options.keys()),
        index=0,
        key="coding_language_selector"
    )
    selected_language = lang_options[selected_lang_name]
    st.session_state["coding_language"] = selected_language
    
    st.markdown("---")
    
    # Render the coding component
    current_problem = st.session_state.get("current_problem")
    
    coding_whiteboard.render_coding_component(
        initial_language=selected_language,
        initial_code=languages[selected_language].get("default_code", ""),
        problem=current_problem,
        height=750
    )


# ============================================================================
# Main Application
# ============================================================================

def main() -> None:
    """Main entry point for HireSense AI."""
    st.set_page_config(
        page_title="HireSense AI - Intelligent Interview Platform",
        layout="wide",
        page_icon="🎯",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .big-font { font-size:20px !important; font-weight: bold; }
    .stButton>button { width: 100%; }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    init_session_state()
    
    # Load persisted data from localStorage
    components.html(get_persistence_loader_html(), height=0)
    
    # Sidebar navigation
    with st.sidebar:
        st.title("🎯 HireSense AI")
        st.markdown("---")
        
        # Language selector in sidebar
        st.markdown("### 🌐 Language")
        languages = language_support.get_language_list()
        lang_options = {lang["display"]: lang["code"] for lang in languages}
        current_lang = st.session_state.get("selected_language", "en")
        
        selected_lang_display = st.selectbox(
            "Interface Language",
            options=list(lang_options.keys()),
            index=list(lang_options.values()).index(current_lang) if current_lang in lang_options.values() else 0,
            key="sidebar_language_selector",
            label_visibility="collapsed"
        )
        st.session_state["selected_language"] = lang_options[selected_lang_display]
        
        st.markdown("---")
        
        # Navigation
        st.markdown("### Navigation")
        
        if st.button(f"🎤 {get_ui_text('interview')}", width="stretch", 
                     type="primary" if st.session_state.get("page") == "interview" else "secondary"):
            st.session_state["page"] = "interview"
            st.rerun()
        
        if st.button(f"📚 {get_ui_text('question_bank')}", width="stretch",
                     type="primary" if st.session_state.get("page") == "history" else "secondary"):
            st.session_state["page"] = "history"
            st.rerun()
        
        if st.button("📊 Skill Analysis", width="stretch",
                     type="primary" if st.session_state.get("page") == "skills" else "secondary"):
            st.session_state["page"] = "skills"
            st.rerun()
        
        if st.button("🤖 Live Copilot", width="stretch",
                     type="primary" if st.session_state.get("page") == "copilot" else "secondary"):
            st.session_state["page"] = "copilot"
            st.rerun()
        
        if st.button("💻 Coding Practice", width="stretch",
                     type="primary" if st.session_state.get("page") == "coding" else "secondary"):
            st.session_state["page"] = "coding"
            st.rerun()
        
        st.markdown("---")
        
        # System status
        st.markdown("### ⚙️ System Status")
        config_status = config.get_config_status()
        
        if config_status["openrouter"]["configured"]:
            st.success("✅ OpenRouter: Connected")
        else:
            st.error("❌ OpenRouter: Not configured")
        
        if config_status["langsmith"]["enabled"]:
            st.success(f"✅ LangSmith: {config_status['langsmith']['project']}")
        else:
            st.info("ℹ️ LangSmith: Not enabled")
        
        # Question bank count
        bank_count = len(st.session_state.get("question_bank", []))
        st.metric("📚 Saved Interviews", bank_count)
        
        # Feature status
        st.markdown("---")
        st.markdown("### ✨ Features")
        st.markdown(f"🌐 Multi-Language: {'✅' if True else '❌'}")
        st.markdown(f"🏢 Company Prep: {'✅' if True else '❌'}")
        st.markdown(f"🎬 Video Recording: {'✅' if st.session_state.get('video_recording_enabled') else '⚪'}")
        st.markdown(f"🔄 Follow-ups: {'✅' if st.session_state.get('followup_enabled') else '⚪'}")
        st.markdown(f"📊 Skill Analysis: {'✅' if True else '❌'}")
        st.markdown(f"🤖 Live Copilot: {'✅' if True else '❌'}")
        st.markdown(f"💻 Coding Practice: {'✅' if True else '❌'}")
    
    # Header
    st.title("🎯 HireSense AI")
    st.markdown(f"### {get_ui_text('app_subtitle')}")
    st.markdown("*Ace your next interview with adaptive AI that reads your emotions and personalizes your practice.*")
    st.markdown("---")
    
    # Main content based on page
    current_page = st.session_state.get("page", "interview")
    
    if current_page == "history":
        render_question_bank()
    elif current_page == "skills":
        render_skill_analysis_page()
    elif current_page == "copilot":
        render_copilot_page()
    elif current_page == "coding":
        render_coding_page()
    elif st.session_state["interview_started"] and not st.session_state["interview_complete"]:
        render_active_interview()
    elif st.session_state["interview_complete"]:
        render_interview_results()
    else:
        render_interview_setup()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>🎯 <strong>HireSense AI</strong> - Intelligent Interview Platform</p>
        <p>RAG Personalization | Emotion Detection | Adaptive AI | Voice I/O | Analytics | Question Bank</p>
        <p>Multi-Language | Company-Specific Prep | Video Recording | AI Follow-ups | Skill Gap Analysis</p>
        <p>Live Interview Copilot | Integrated Coding & Whiteboard</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
