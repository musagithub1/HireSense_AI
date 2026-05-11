"""
voice_input_component.py
========================

HireSense AI - Voice Input Component

Complete voice input solution that:
1. Records user's voice using Web Speech API
2. Converts speech to text in real-time
3. Syncs transcript to Streamlit via session storage and callbacks
4. Provides visual feedback during recording
"""

import streamlit.components.v1 as components
import streamlit as st


def get_realtime_voice_input_html(session_key: str = "voice_answer", language_code: str = "en-US") -> str:
    """
    Generate a voice input interface that syncs transcript to Streamlit
    via localStorage and postMessage for reliable state management.
    """
    
    return f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
            background: transparent;
            padding: 10px;
        }}
        
        .voice-container {{
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border: 2px solid #dee2e6;
            border-radius: 16px;
            padding: 20px;
            text-align: center;
        }}
        
        .voice-container.recording {{
            border-color: #ff6b6b;
            background: linear-gradient(135deg, #fff5f5 0%, #ffe3e3 100%);
            animation: recordingPulse 2s infinite;
        }}
        
        @keyframes recordingPulse {{
            0%, 100% {{ box-shadow: 0 0 0 0 rgba(255, 107, 107, 0.4); }}
            50% {{ box-shadow: 0 0 0 10px rgba(255, 107, 107, 0); }}
        }}
        
        .voice-container.has-transcript {{
            border-color: #51cf66;
            background: linear-gradient(135deg, #f8fff8 0%, #e6ffe6 100%);
        }}
        
        .title {{
            font-size: 16px;
            font-weight: 600;
            color: #495057;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }}
        
        .mic-button {{
            width: 100px;
            height: 100px;
            border-radius: 50%;
            border: none;
            cursor: pointer;
            font-size: 42px;
            background: linear-gradient(135deg, #51cf66 0%, #37b24d 100%);
            color: white;
            box-shadow: 0 8px 25px rgba(55, 178, 77, 0.4);
            transition: all 0.3s ease;
            margin: 15px auto;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .mic-button:hover {{
            transform: scale(1.05);
            box-shadow: 0 10px 30px rgba(55, 178, 77, 0.5);
        }}
        
        .mic-button.recording {{
            background: linear-gradient(135deg, #ff6b6b 0%, #fa5252 100%);
            box-shadow: 0 8px 25px rgba(255, 107, 107, 0.5);
            animation: pulse 1.5s infinite;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ transform: scale(1); }}
            50% {{ transform: scale(1.08); }}
        }}
        
        .status {{
            font-size: 14px;
            color: #868e96;
            margin: 10px 0;
            min-height: 20px;
        }}
        
        .status.recording {{
            color: #fa5252;
            font-weight: 600;
        }}
        
        .status.ready {{
            color: #37b24d;
            font-weight: 600;
        }}
        
        .live-indicator {{
            display: none;
            align-items: center;
            justify-content: center;
            gap: 8px;
            margin: 10px 0;
            padding: 8px 16px;
            background: #fff5f5;
            border-radius: 20px;
            font-size: 13px;
            color: #fa5252;
        }}
        
        .live-indicator.show {{
            display: flex;
        }}
        
        .live-dot {{
            width: 10px;
            height: 10px;
            background: #fa5252;
            border-radius: 50%;
            animation: blink 1s infinite;
        }}
        
        @keyframes blink {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.3; }}
        }}
        
        .transcript-preview {{
            background: white;
            border: 2px solid #e9ecef;
            border-radius: 12px;
            padding: 15px;
            margin: 15px 0;
            min-height: 60px;
            max-height: 120px;
            overflow-y: auto;
            text-align: left;
            font-size: 14px;
            line-height: 1.6;
            color: #212529;
        }}
        
        .transcript-preview.recording {{
            border-color: #ff6b6b;
        }}
        
        .transcript-preview .interim {{
            color: #868e96;
            font-style: italic;
        }}
        
        .transcript-preview .placeholder {{
            color: #adb5bd;
            font-style: italic;
        }}
        
        .button-row {{
            display: flex;
            gap: 10px;
            justify-content: center;
            margin-top: 15px;
        }}
        
        .action-btn {{
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        
        .clear-btn {{
            background: #f8f9fa;
            color: #495057;
            border: 2px solid #dee2e6;
        }}
        
        .clear-btn:hover {{
            background: #e9ecef;
        }}
        
        .use-btn {{
            background: linear-gradient(135deg, #228be6 0%, #1971c2 100%);
            color: white;
        }}
        
        .use-btn:hover:not(:disabled) {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(34, 139, 230, 0.4);
        }}
        
        .use-btn:disabled {{
            background: #dee2e6;
            color: #868e96;
            cursor: not-allowed;
        }}
        
        .use-btn.success {{
            background: linear-gradient(135deg, #51cf66 0%, #37b24d 100%);
        }}
        
        .error-msg {{
            background: #fff5f5;
            color: #c92a2a;
            padding: 10px 15px;
            border-radius: 8px;
            font-size: 13px;
            margin-top: 10px;
            display: none;
        }}
        
        .error-msg.show {{
            display: block;
        }}
        
        .hint {{
            font-size: 12px;
            color: #868e96;
            margin-top: 10px;
            padding: 8px;
            background: #f1f3f5;
            border-radius: 8px;
        }}
        
        .char-count {{
            font-size: 11px;
            color: #adb5bd;
            text-align: right;
            margin-top: 5px;
        }}
    </style>
</head>
<body>
    <div class="voice-container" id="voiceContainer">
        <div class="title">
            🎤 Speak Your Answer
            <span style="font-size: 11px; padding: 3px 8px; background: #e7f5ff; color: #1971c2; border-radius: 12px;">
                Chrome/Edge
            </span>
        </div>
        
        <button class="mic-button" id="micBtn">🎤</button>
        
        <div class="status" id="status">Click the microphone to start speaking</div>
        
        <div class="live-indicator" id="liveIndicator">
            <span class="live-dot"></span>
            <span>LIVE - Recording your answer</span>
        </div>
        
        <div class="transcript-preview" id="transcriptPreview">
            <span class="placeholder">Your words will appear here...</span>
        </div>
        <div class="char-count" id="charCount">0 characters</div>
        
        <div class="button-row">
            <button class="action-btn clear-btn" id="clearBtn">🗑️ Clear</button>
            <button class="action-btn use-btn" id="useBtn" disabled>✅ Use This Answer</button>
        </div>
        
        <div class="error-msg" id="errorMsg"></div>
        
        <div class="hint">
            💡 Click "Use This Answer" to fill the answer field below
        </div>
    </div>
    
    <script>
    (function() {{
        const SESSION_KEY = '{session_key}';
        
        // Check browser support
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        
        if (!SpeechRecognition) {{
            document.getElementById('voiceContainer').innerHTML = `
                <div style="padding: 30px; text-align: center;">
                    <div style="font-size: 48px; margin-bottom: 15px;">⚠️</div>
                    <div style="font-size: 16px; font-weight: 600; color: #495057; margin-bottom: 10px;">
                        Voice Input Not Supported
                    </div>
                    <div style="font-size: 13px; color: #868e96;">
                        Please use Google Chrome or Microsoft Edge for voice input.
                    </div>
                </div>
            `;
            return;
        }}
        
        // Initialize recognition
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = '{language_code}';
        recognition.maxAlternatives = 1;
        
        // DOM elements
        const container = document.getElementById('voiceContainer');
        const micBtn = document.getElementById('micBtn');
        const status = document.getElementById('status');
        const transcriptPreview = document.getElementById('transcriptPreview');
        const charCount = document.getElementById('charCount');
        const clearBtn = document.getElementById('clearBtn');
        const useBtn = document.getElementById('useBtn');
        const errorMsg = document.getElementById('errorMsg');
        const liveIndicator = document.getElementById('liveIndicator');
        
        // State
        let isRecording = false;
        let finalTranscript = '';
        let hasPlaceholder = true;
        
        // Load any existing transcript from localStorage
        const savedTranscript = localStorage.getItem(SESSION_KEY);
        if (savedTranscript) {{
            finalTranscript = savedTranscript;
            setTranscriptText(savedTranscript);
        }}
        
        // Save transcript to localStorage and notify Streamlit
        function saveTranscript(text) {{
            localStorage.setItem(SESSION_KEY, text);
            localStorage.setItem(SESSION_KEY + '_timestamp', Date.now().toString());
        }}
        
        // Send transcript to Streamlit parent
        function sendToStreamlit(text) {{
            // Save to localStorage
            saveTranscript(text);
            
            // Post message to parent
            window.parent.postMessage({{
                type: 'streamlit:setComponentValue',
                value: {{ transcript: text, key: SESSION_KEY, timestamp: Date.now() }}
            }}, '*');
            
            // Also set in sessionStorage for backup
            sessionStorage.setItem(SESSION_KEY, text);
        }}
        
        // Helper functions
        function getTranscriptText() {{
            if (hasPlaceholder) return '';
            return transcriptPreview.innerText.trim();
        }}
        
        function setTranscriptText(text, interim = '') {{
            hasPlaceholder = false;
            if (!text && !interim) {{
                transcriptPreview.innerHTML = '<span class="placeholder">Your words will appear here...</span>';
                hasPlaceholder = true;
                container.classList.remove('has-transcript');
            }} else {{
                let html = text;
                if (interim) {{
                    html += '<span class="interim"> ' + interim + '</span>';
                }}
                transcriptPreview.innerHTML = html;
                if (text) {{
                    container.classList.add('has-transcript');
                }}
            }}
            updateCharCount();
            updateUseButton();
        }}
        
        function updateCharCount() {{
            const text = getTranscriptText();
            charCount.textContent = text.length + ' characters';
        }}
        
        function updateUseButton() {{
            const text = getTranscriptText();
            useBtn.disabled = text.length === 0;
        }}
        
        function showError(message) {{
            errorMsg.textContent = message;
            errorMsg.classList.add('show');
            setTimeout(() => errorMsg.classList.remove('show'), 5000);
        }}
        
        // Recognition event handlers
        recognition.onstart = function() {{
            isRecording = true;
            micBtn.classList.add('recording');
            micBtn.innerHTML = '⏹️';
            status.textContent = '🔴 Listening... Speak now!';
            status.classList.add('recording');
            status.classList.remove('ready');
            transcriptPreview.classList.add('recording');
            container.classList.add('recording');
            container.classList.remove('has-transcript');
            liveIndicator.classList.add('show');
            errorMsg.classList.remove('show');
            
            if (hasPlaceholder) {{
                transcriptPreview.innerHTML = '';
                hasPlaceholder = false;
            }}
        }};
        
        recognition.onend = function() {{
            isRecording = false;
            micBtn.classList.remove('recording');
            micBtn.innerHTML = '🎤';
            transcriptPreview.classList.remove('recording');
            container.classList.remove('recording');
            liveIndicator.classList.remove('show');
            
            const text = getTranscriptText().replace(/\\s+/g, ' ').trim();
            if (text) {{
                setTranscriptText(text);
                finalTranscript = text;
                status.textContent = '✅ Done! Click "Use This Answer" to continue';
                status.classList.add('ready');
                status.classList.remove('recording');
                
                // Auto-save to localStorage
                saveTranscript(text);
            }} else {{
                status.textContent = 'Click the microphone to start speaking';
                status.classList.remove('recording', 'ready');
            }}
        }};
        
        recognition.onresult = function(event) {{
            let interim = '';
            let final = finalTranscript;
            
            for (let i = event.resultIndex; i < event.results.length; i++) {{
                const result = event.results[i];
                if (result.isFinal) {{
                    final += result[0].transcript + ' ';
                }} else {{
                    interim += result[0].transcript;
                }}
            }}
            
            finalTranscript = final.trim();
            setTranscriptText(finalTranscript, interim);
            
            // Save as we go
            if (finalTranscript) {{
                saveTranscript(finalTranscript);
            }}
        }};
        
        recognition.onerror = function(event) {{
            isRecording = false;
            micBtn.classList.remove('recording');
            micBtn.innerHTML = '🎤';
            status.textContent = 'Click the microphone to try again';
            status.classList.remove('recording', 'ready');
            transcriptPreview.classList.remove('recording');
            container.classList.remove('recording');
            liveIndicator.classList.remove('show');
            
            const errorMessages = {{
                'no-speech': 'No speech detected. Please try again.',
                'audio-capture': 'Microphone not found. Please check your settings.',
                'not-allowed': 'Microphone access denied. Please allow microphone access.',
                'network': 'Network error. Please check your connection.',
                'aborted': 'Recording was stopped.',
                'service-not-allowed': 'Speech service not allowed.'
            }};
            
            if (event.error !== 'aborted') {{
                showError(errorMessages[event.error] || 'Error: ' + event.error);
            }}
        }};
        
        // Button handlers
        micBtn.addEventListener('click', function() {{
            if (isRecording) {{
                recognition.stop();
            }} else {{
                try {{
                    recognition.start();
                }} catch (e) {{
                    if (e.name !== 'InvalidStateError') {{
                        showError('Could not start recording: ' + e.message);
                    }}
                }}
            }}
        }});
        
        clearBtn.addEventListener('click', function() {{
            if (isRecording) {{
                recognition.stop();
            }}
            finalTranscript = '';
            setTranscriptText('');
            status.textContent = 'Click the microphone to start speaking';
            status.classList.remove('recording', 'ready');
            
            // Clear localStorage
            localStorage.removeItem(SESSION_KEY);
            localStorage.removeItem(SESSION_KEY + '_timestamp');
            sessionStorage.removeItem(SESSION_KEY);
        }});
        
        useBtn.addEventListener('click', function() {{
            const text = getTranscriptText();
            if (text) {{
                // Send to Streamlit
                sendToStreamlit(text);
                
                // Visual feedback
                useBtn.innerHTML = '✅ Sent!';
                useBtn.classList.add('success');
                
                setTimeout(() => {{
                    useBtn.innerHTML = '✅ Use This Answer';
                    useBtn.classList.remove('success');
                }}, 1500);
            }}
        }});
        
        // Initialize
        updateCharCount();
        updateUseButton();
    }})();
    </script>
</body>
</html>
'''


def render_voice_input(height: int = 380, key: str = "voice_input", language_code: str = "en-US"):
    """
    Render the voice input component.
    
    Args:
        height: Height of the component in pixels
        key: Unique key for the component
    
    Returns the component.
    """
    # Create a unique session key based on the provided key
    session_key = f"hiresense_voice_{key}"
    html = get_realtime_voice_input_html(session_key, language_code)
    return components.html(html, height=height)


def get_voice_transcript(key: str = "voice_input") -> str:
    """
    Get the voice transcript from session state.
    Call this after render_voice_input to get the transcript.
    
    Args:
        key: The same key used in render_voice_input
    
    Returns:
        str: The transcript text, or empty string if none
    """
    session_key = f"hiresense_voice_{key}"
    return st.session_state.get(session_key, "")
