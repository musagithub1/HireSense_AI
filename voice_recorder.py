"""
voice_recorder.py
=================

Voice recording and speech-to-text component for Streamlit.
Provides a complete solution for users to speak their answers.
"""

import streamlit as st
import streamlit.components.v1 as components


def get_voice_recorder_html() -> str:
    """
    Generate HTML/JS for a complete voice recording interface.
    Uses Web Speech API for real-time speech-to-text.
    
    Features:
    - Large, easy-to-click microphone button
    - Real-time transcription display
    - Auto-stop after silence
    - Visual feedback during recording
    - Sends transcript to Streamlit via postMessage
    """
    
    return '''
<!DOCTYPE html>
<html>
<head>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: transparent;
        }
        
        .voice-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 15px;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 15px;
            border: 2px solid #dee2e6;
        }
        
        .mic-section {
            display: flex;
            align-items: center;
            gap: 20px;
            margin-bottom: 15px;
        }
        
        .mic-button {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            border: none;
            cursor: pointer;
            font-size: 32px;
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(40, 167, 69, 0.4);
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .mic-button:hover {
            transform: scale(1.05);
            box-shadow: 0 6px 20px rgba(40, 167, 69, 0.5);
        }
        
        .mic-button.recording {
            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
            box-shadow: 0 4px 15px rgba(220, 53, 69, 0.4);
            animation: pulse 1s infinite;
        }
        
        .mic-button:disabled {
            background: #6c757d;
            cursor: not-allowed;
            animation: none;
        }
        
        @keyframes pulse {
            0%, 100% { transform: scale(1); box-shadow: 0 4px 15px rgba(220, 53, 69, 0.4); }
            50% { transform: scale(1.08); box-shadow: 0 6px 25px rgba(220, 53, 69, 0.6); }
        }
        
        .status-info {
            text-align: center;
        }
        
        .status-text {
            font-size: 16px;
            font-weight: 600;
            color: #495057;
            margin-bottom: 5px;
        }
        
        .status-text.recording {
            color: #dc3545;
        }
        
        .hint-text {
            font-size: 12px;
            color: #6c757d;
        }
        
        .transcript-box {
            width: 100%;
            min-height: 100px;
            max-height: 200px;
            padding: 12px;
            border: 2px solid #ced4da;
            border-radius: 10px;
            background: white;
            font-size: 14px;
            line-height: 1.6;
            overflow-y: auto;
            margin-bottom: 15px;
        }
        
        .transcript-box.recording {
            border-color: #dc3545;
            background: #fff5f5;
        }
        
        .transcript-box.has-text {
            border-color: #28a745;
        }
        
        .placeholder {
            color: #adb5bd;
            font-style: italic;
        }
        
        .interim {
            color: #6c757d;
            font-style: italic;
        }
        
        .final {
            color: #212529;
        }
        
        .action-buttons {
            display: flex;
            gap: 10px;
            width: 100%;
        }
        
        .action-btn {
            flex: 1;
            padding: 12px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.2s;
        }
        
        .clear-btn {
            background: #6c757d;
            color: white;
        }
        
        .clear-btn:hover {
            background: #5a6268;
        }
        
        .use-btn {
            background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
            color: white;
        }
        
        .use-btn:hover {
            background: linear-gradient(135deg, #0056b3 0%, #004085 100%);
        }
        
        .use-btn:disabled {
            background: #adb5bd;
            cursor: not-allowed;
        }
        
        .error-box {
            width: 100%;
            padding: 10px;
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            border-radius: 8px;
            color: #721c24;
            font-size: 13px;
            margin-bottom: 10px;
            display: none;
        }
        
        .browser-warning {
            width: 100%;
            padding: 10px;
            background: #fff3cd;
            border: 1px solid #ffeeba;
            border-radius: 8px;
            color: #856404;
            font-size: 13px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="voice-container">
        <div id="error-box" class="error-box"></div>
        
        <div class="mic-section">
            <button id="mic-btn" class="mic-button" title="Click to start/stop recording">
                🎤
            </button>
            <div class="status-info">
                <div id="status" class="status-text">Click microphone to speak</div>
                <div class="hint-text">Your speech will be converted to text</div>
            </div>
        </div>
        
        <div id="transcript-box" class="transcript-box">
            <span class="placeholder">Your spoken words will appear here...</span>
        </div>
        
        <div class="action-buttons">
            <button id="clear-btn" class="action-btn clear-btn">🗑️ Clear</button>
            <button id="use-btn" class="action-btn use-btn" disabled>✅ Use This Answer</button>
        </div>
    </div>
    
    <div id="browser-warning" class="browser-warning" style="display: none;">
        ⚠️ Speech recognition not supported. Please use Chrome or Edge browser.
    </div>
    
    <script>
    (function() {
        const micBtn = document.getElementById('mic-btn');
        const status = document.getElementById('status');
        const transcriptBox = document.getElementById('transcript-box');
        const clearBtn = document.getElementById('clear-btn');
        const useBtn = document.getElementById('use-btn');
        const errorBox = document.getElementById('error-box');
        const browserWarning = document.getElementById('browser-warning');
        const container = document.querySelector('.voice-container');
        
        // Check for speech recognition support
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        
        if (!SpeechRecognition) {
            container.style.display = 'none';
            browserWarning.style.display = 'block';
            return;
        }
        
        // Initialize speech recognition
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';
        recognition.maxAlternatives = 1;
        
        let isRecording = false;
        let finalTranscript = '';
        let interimTranscript = '';
        
        function updateTranscriptDisplay() {
            if (!finalTranscript && !interimTranscript) {
                transcriptBox.innerHTML = '<span class="placeholder">Your spoken words will appear here...</span>';
                transcriptBox.classList.remove('has-text');
            } else {
                transcriptBox.innerHTML = 
                    '<span class="final">' + finalTranscript + '</span>' +
                    '<span class="interim">' + interimTranscript + '</span>';
                transcriptBox.classList.add('has-text');
            }
            
            // Enable/disable use button
            useBtn.disabled = !finalTranscript.trim();
            
            // Auto-scroll to bottom
            transcriptBox.scrollTop = transcriptBox.scrollHeight;
        }
        
        function showError(message) {
            errorBox.textContent = message;
            errorBox.style.display = 'block';
            setTimeout(() => { errorBox.style.display = 'none'; }, 5000);
        }
        
        function startRecording() {
            try {
                recognition.start();
            } catch (e) {
                if (e.name === 'InvalidStateError') {
                    // Already started, ignore
                } else {
                    showError('Could not start recording: ' + e.message);
                }
            }
        }
        
        function stopRecording() {
            recognition.stop();
        }
        
        // Recognition event handlers
        recognition.onstart = function() {
            isRecording = true;
            micBtn.classList.add('recording');
            micBtn.innerHTML = '⏹️';
            status.textContent = '🔴 Recording... Speak now!';
            status.classList.add('recording');
            transcriptBox.classList.add('recording');
            errorBox.style.display = 'none';
        };
        
        recognition.onend = function() {
            isRecording = false;
            micBtn.classList.remove('recording');
            micBtn.innerHTML = '🎤';
            status.textContent = finalTranscript ? '✅ Recording complete' : 'Click microphone to speak';
            status.classList.remove('recording');
            transcriptBox.classList.remove('recording');
            interimTranscript = '';
            updateTranscriptDisplay();
        };
        
        recognition.onresult = function(event) {
            interimTranscript = '';
            
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const result = event.results[i];
                if (result.isFinal) {
                    finalTranscript += result[0].transcript + ' ';
                } else {
                    interimTranscript += result[0].transcript;
                }
            }
            
            updateTranscriptDisplay();
        };
        
        recognition.onerror = function(event) {
            console.error('Speech recognition error:', event.error);
            
            let errorMessage = '';
            switch(event.error) {
                case 'no-speech':
                    errorMessage = 'No speech detected. Please try again and speak clearly.';
                    break;
                case 'audio-capture':
                    errorMessage = 'No microphone found. Please connect a microphone and try again.';
                    break;
                case 'not-allowed':
                    errorMessage = 'Microphone access denied. Please allow microphone access in your browser settings.';
                    break;
                case 'network':
                    errorMessage = 'Network error. Please check your internet connection.';
                    break;
                case 'aborted':
                    // User stopped, not an error
                    return;
                default:
                    errorMessage = 'Speech recognition error: ' + event.error;
            }
            
            showError(errorMessage);
        };
        
        // Button event handlers
        micBtn.addEventListener('click', function() {
            if (isRecording) {
                stopRecording();
            } else {
                startRecording();
            }
        });
        
        clearBtn.addEventListener('click', function() {
            finalTranscript = '';
            interimTranscript = '';
            updateTranscriptDisplay();
            if (isRecording) {
                stopRecording();
            }
        });
        
        useBtn.addEventListener('click', function() {
            const text = finalTranscript.trim();
            if (text) {
                // Send to Streamlit
                window.parent.postMessage({
                    type: 'streamlit:setComponentValue',
                    value: {
                        transcript: text,
                        action: 'use_answer',
                        timestamp: Date.now()
                    }
                }, '*');
                
                // Visual feedback
                useBtn.textContent = '✅ Sent!';
                useBtn.disabled = true;
                setTimeout(() => {
                    useBtn.textContent = '✅ Use This Answer';
                    useBtn.disabled = !finalTranscript.trim();
                }, 2000);
            }
        });
        
        // Initialize display
        updateTranscriptDisplay();
    })();
    </script>
</body>
</html>
'''


def render_voice_recorder(height: int = 320):
    """Render the voice recorder component in Streamlit."""
    html = get_voice_recorder_html()
    return components.html(html, height=height)


# Alternative: Audio recorder that saves to file for server-side processing
def get_audio_recorder_html() -> str:
    """
    Alternative audio recorder that records audio and can be processed server-side.
    Uses MediaRecorder API.
    """
    return '''
<!DOCTYPE html>
<html>
<head>
    <style>
        .recorder-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 12px;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        .record-btn {
            width: 70px;
            height: 70px;
            border-radius: 50%;
            border: none;
            cursor: pointer;
            font-size: 28px;
            background: #28a745;
            color: white;
            margin-bottom: 15px;
            transition: all 0.3s;
        }
        
        .record-btn.recording {
            background: #dc3545;
            animation: pulse 1s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        
        .status {
            font-size: 14px;
            color: #495057;
            margin-bottom: 10px;
        }
        
        .timer {
            font-size: 24px;
            font-weight: bold;
            color: #212529;
            font-family: monospace;
        }
        
        audio {
            width: 100%;
            margin-top: 15px;
        }
    </style>
</head>
<body>
    <div class="recorder-container">
        <button id="record-btn" class="record-btn">🎤</button>
        <div id="status" class="status">Click to start recording</div>
        <div id="timer" class="timer">00:00</div>
        <audio id="audio-player" controls style="display: none;"></audio>
    </div>
    
    <script>
    (function() {
        const recordBtn = document.getElementById('record-btn');
        const status = document.getElementById('status');
        const timer = document.getElementById('timer');
        const audioPlayer = document.getElementById('audio-player');
        
        let mediaRecorder = null;
        let audioChunks = [];
        let isRecording = false;
        let timerInterval = null;
        let seconds = 0;
        
        function formatTime(s) {
            const mins = Math.floor(s / 60).toString().padStart(2, '0');
            const secs = (s % 60).toString().padStart(2, '0');
            return mins + ':' + secs;
        }
        
        async function startRecording() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];
                
                mediaRecorder.ondataavailable = (e) => {
                    audioChunks.push(e.data);
                };
                
                mediaRecorder.onstop = () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                    const audioUrl = URL.createObjectURL(audioBlob);
                    audioPlayer.src = audioUrl;
                    audioPlayer.style.display = 'block';
                    
                    // Convert to base64 and send to Streamlit
                    const reader = new FileReader();
                    reader.onloadend = () => {
                        window.parent.postMessage({
                            type: 'streamlit:setComponentValue',
                            value: {
                                audio_data: reader.result,
                                duration: seconds,
                                timestamp: Date.now()
                            }
                        }, '*');
                    };
                    reader.readAsDataURL(audioBlob);
                };
                
                mediaRecorder.start();
                isRecording = true;
                recordBtn.classList.add('recording');
                recordBtn.innerHTML = '⏹️';
                status.textContent = 'Recording...';
                
                seconds = 0;
                timerInterval = setInterval(() => {
                    seconds++;
                    timer.textContent = formatTime(seconds);
                }, 1000);
                
            } catch (e) {
                status.textContent = 'Error: ' + e.message;
            }
        }
        
        function stopRecording() {
            if (mediaRecorder && isRecording) {
                mediaRecorder.stop();
                mediaRecorder.stream.getTracks().forEach(track => track.stop());
                isRecording = false;
                recordBtn.classList.remove('recording');
                recordBtn.innerHTML = '🎤';
                status.textContent = 'Recording saved';
                clearInterval(timerInterval);
            }
        }
        
        recordBtn.addEventListener('click', () => {
            if (isRecording) {
                stopRecording();
            } else {
                startRecording();
            }
        });
    })();
    </script>
</body>
</html>
'''
