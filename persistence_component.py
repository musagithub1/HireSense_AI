"""
persistence_component.py
========================

HireSense AI - Browser Persistence Component

Provides localStorage-based persistence for:
1. Resume text (survives page refresh)
2. Job description text (survives page refresh)
3. Voice transcripts (survives page refresh)
4. Interview history (for Question Bank feature)
"""

import streamlit.components.v1 as components
import streamlit as st
import json
import base64
from datetime import datetime


def get_persistence_html() -> str:
    """
    Generate HTML/JS component that handles localStorage persistence
    and communicates with Streamlit via postMessage.
    """
    return '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { margin: 0; padding: 0; }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div id="status" class="hidden"></div>
    
    <script>
    (function() {
        const STORAGE_KEYS = {
            RESUME: 'hiresense_resume_text',
            JD: 'hiresense_jd_text',
            VOICE: 'hiresense_voice_answer',
            HISTORY: 'hiresense_interview_history',
            SETTINGS: 'hiresense_settings'
        };
        
        // Load all persisted data and send to Streamlit
        function loadPersistedData() {
            const data = {
                resume_text: localStorage.getItem(STORAGE_KEYS.RESUME) || '',
                jd_text: localStorage.getItem(STORAGE_KEYS.JD) || '',
                voice_answer: localStorage.getItem(STORAGE_KEYS.VOICE) || '',
                interview_history: JSON.parse(localStorage.getItem(STORAGE_KEYS.HISTORY) || '[]'),
                settings: JSON.parse(localStorage.getItem(STORAGE_KEYS.SETTINGS) || '{}'),
                loaded_at: Date.now()
            };
            
            // Send to Streamlit
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: data
            }, '*');
            
            return data;
        }
        
        // Save data to localStorage
        function saveData(key, value) {
            if (typeof value === 'object') {
                localStorage.setItem(key, JSON.stringify(value));
            } else {
                localStorage.setItem(key, value);
            }
        }
        
        // Listen for save requests from Streamlit
        window.addEventListener('message', function(event) {
            if (event.data && event.data.type === 'hiresense_save') {
                const { key, value } = event.data;
                if (STORAGE_KEYS[key]) {
                    saveData(STORAGE_KEYS[key], value);
                }
            }
            
            if (event.data && event.data.type === 'hiresense_clear') {
                const { key } = event.data;
                if (key === 'ALL') {
                    Object.values(STORAGE_KEYS).forEach(k => localStorage.removeItem(k));
                } else if (STORAGE_KEYS[key]) {
                    localStorage.removeItem(STORAGE_KEYS[key]);
                }
            }
            
            if (event.data && event.data.type === 'hiresense_load') {
                loadPersistedData();
            }
        });
        
        // Auto-load on component mount
        loadPersistedData();
    })();
    </script>
</body>
</html>
'''


def render_persistence_loader():
    """
    Render the persistence loader component.
    This should be called once at the top of the app to load persisted data.
    
    Returns:
        dict: The loaded data from localStorage, or None if not yet loaded
    """
    return components.html(get_persistence_html(), height=0)


def get_save_script(key: str, value: str) -> str:
    """
    Generate JavaScript to save data to localStorage.
    
    Args:
        key: Storage key (RESUME, JD, VOICE, HISTORY, SETTINGS)
        value: Value to save
    
    Returns:
        HTML string with script to execute
    """
    # Escape the value for JavaScript
    escaped_value = json.dumps(value)
    
    return f'''
    <script>
    (function() {{
        const STORAGE_KEYS = {{
            RESUME: 'hiresense_resume_text',
            JD: 'hiresense_jd_text',
            VOICE: 'hiresense_voice_answer',
            HISTORY: 'hiresense_interview_history',
            SETTINGS: 'hiresense_settings'
        }};
        
        const key = STORAGE_KEYS['{key}'];
        const value = {escaped_value};
        
        if (key) {{
            if (typeof value === 'object') {{
                localStorage.setItem(key, JSON.stringify(value));
            }} else {{
                localStorage.setItem(key, value);
            }}
        }}
    }})();
    </script>
    '''


def save_to_browser(key: str, value):
    """
    Save data to browser localStorage.
    
    Args:
        key: Storage key (RESUME, JD, VOICE, HISTORY, SETTINGS)
        value: Value to save (string or dict)
    """
    if isinstance(value, (dict, list)):
        value_str = json.dumps(value)
    else:
        value_str = str(value) if value else ""
    
    script = get_save_script(key, value_str)
    components.html(script, height=0)


def get_clear_script(key: str = "ALL") -> str:
    """
    Generate JavaScript to clear data from localStorage.
    
    Args:
        key: Storage key to clear, or "ALL" to clear everything
    
    Returns:
        HTML string with script to execute
    """
    return f'''
    <script>
    (function() {{
        const STORAGE_KEYS = {{
            RESUME: 'hiresense_resume_text',
            JD: 'hiresense_jd_text',
            VOICE: 'hiresense_voice_answer',
            HISTORY: 'hiresense_interview_history',
            SETTINGS: 'hiresense_settings'
        }};
        
        const key = '{key}';
        if (key === 'ALL') {{
            Object.values(STORAGE_KEYS).forEach(k => localStorage.removeItem(k));
        }} else if (STORAGE_KEYS[key]) {{
            localStorage.removeItem(STORAGE_KEYS[key]);
        }}
    }})();
    </script>
    '''


def clear_browser_storage(key: str = "ALL"):
    """
    Clear data from browser localStorage.
    
    Args:
        key: Storage key to clear, or "ALL" to clear everything
    """
    script = get_clear_script(key)
    components.html(script, height=0)


# ============================================================================
# Question Bank / Interview History
# ============================================================================

def save_interview_to_history(interview_data: dict):
    """
    Save a completed interview to the history.
    
    Args:
        interview_data: Dict containing:
            - timestamp: ISO timestamp
            - interview_type: Technical/Behavioral/HR
            - questions: List of Q&A pairs
            - metrics: Performance metrics
            - report: AI-generated report
    """
    # Add to session state history
    if "interview_history_bank" not in st.session_state:
        st.session_state["interview_history_bank"] = []
    
    # Add timestamp if not present
    if "timestamp" not in interview_data:
        interview_data["timestamp"] = datetime.now().isoformat()
    
    # Add unique ID
    interview_data["id"] = f"interview_{len(st.session_state['interview_history_bank'])}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    st.session_state["interview_history_bank"].append(interview_data)
    
    # Save to localStorage
    save_to_browser("HISTORY", st.session_state["interview_history_bank"])


def get_interview_history() -> list:
    """
    Get the interview history from session state.
    
    Returns:
        list: List of past interview records
    """
    return st.session_state.get("interview_history_bank", [])


def render_question_bank():
    """
    Render the Question Bank UI showing past interviews and questions.
    """
    st.markdown("### 📚 Question Bank")
    
    history = get_interview_history()
    
    if not history:
        st.info("No past interviews yet. Complete an interview to build your question bank!")
        return
    
    st.write(f"**{len(history)} past interview(s)**")
    
    for i, interview in enumerate(reversed(history)):
        timestamp = interview.get("timestamp", "Unknown date")
        interview_type = interview.get("interview_type", "General")
        questions = interview.get("questions", [])
        
        with st.expander(f"📋 {interview_type} Interview - {timestamp[:10]}", expanded=False):
            # Show metrics if available
            metrics = interview.get("metrics", {})
            if metrics:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Questions", len(questions))
                with col2:
                    st.metric("Composure", f"{metrics.get('composure_score', 'N/A')}%")
                with col3:
                    st.metric("Duration", metrics.get("duration", "N/A"))
            
            # Show questions and answers
            st.markdown("#### Questions & Answers")
            for j, qa in enumerate(questions):
                st.markdown(f"**Q{j+1}: {qa.get('question', 'N/A')}**")
                st.markdown(f"*Your answer:* {qa.get('answer', 'N/A')}")
                st.markdown("---")
            
            # Show report if available
            report = interview.get("report")
            if report:
                with st.expander("View AI Report"):
                    st.markdown(report)
