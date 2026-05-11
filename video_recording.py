"""
video_recording.py
==================

HireSense AI - Video Recording Module

Provides video recording capabilities for interview sessions:
- Record webcam video during interviews
- Save recordings for later review
- Playback with timestamp markers
- Export recordings
"""

import streamlit.components.v1 as components
import streamlit as st
from datetime import datetime
import json
import base64
from typing import Optional, Dict, List


# ============================================================================
# Video Recording Component HTML
# ============================================================================

def get_video_recorder_html(session_id: str = "default") -> str:
    """
    Generate HTML/JS code for video recording component.
    
    Features:
    - Start/stop recording
    - Preview during recording
    - Download recorded video
    - Timestamp markers for questions
    """
    
    return f'''
<!DOCTYPE html>
<html>
<head>
    <style>
        .video-recorder {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-radius: 16px;
            padding: 20px;
            color: white;
        }}
        
        .recorder-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        
        .recorder-title {{
            font-size: 16px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .recording-indicator {{
            display: none;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            background: rgba(255, 59, 48, 0.2);
            border-radius: 20px;
            font-size: 12px;
            color: #ff3b30;
        }}
        
        .recording-indicator.active {{
            display: flex;
            animation: pulse 1.5s infinite;
        }}
        
        .rec-dot {{
            width: 8px;
            height: 8px;
            background: #ff3b30;
            border-radius: 50%;
            animation: blink 1s infinite;
        }}
        
        @keyframes blink {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.3; }}
        }}
        
        @keyframes pulse {{
            0%, 100% {{ transform: scale(1); }}
            50% {{ transform: scale(1.02); }}
        }}
        
        .video-container {{
            position: relative;
            width: 100%;
            aspect-ratio: 16/9;
            background: #000;
            border-radius: 12px;
            overflow: hidden;
            margin-bottom: 15px;
        }}
        
        #preview-video, #playback-video {{
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}
        
        #preview-video {{
            transform: scaleX(-1);
        }}
        
        .controls {{
            display: flex;
            gap: 10px;
            justify-content: center;
            flex-wrap: wrap;
        }}
        
        .control-btn {{
            padding: 12px 24px;
            border: none;
            border-radius: 25px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .btn-record {{
            background: linear-gradient(135deg, #ff3b30 0%, #ff6b6b 100%);
            color: white;
        }}
        
        .btn-record:hover {{
            transform: scale(1.05);
            box-shadow: 0 4px 15px rgba(255, 59, 48, 0.4);
        }}
        
        .btn-record.recording {{
            background: linear-gradient(135deg, #ff6b6b 0%, #ff3b30 100%);
            animation: recording-pulse 1.5s infinite;
        }}
        
        @keyframes recording-pulse {{
            0%, 100% {{ box-shadow: 0 0 0 0 rgba(255, 59, 48, 0.4); }}
            50% {{ box-shadow: 0 0 0 10px rgba(255, 59, 48, 0); }}
        }}
        
        .btn-stop {{
            background: linear-gradient(135deg, #555 0%, #333 100%);
            color: white;
        }}
        
        .btn-stop:hover {{
            background: linear-gradient(135deg, #666 0%, #444 100%);
        }}
        
        .btn-download {{
            background: linear-gradient(135deg, #34c759 0%, #30d158 100%);
            color: white;
        }}
        
        .btn-download:hover {{
            transform: scale(1.05);
            box-shadow: 0 4px 15px rgba(52, 199, 89, 0.4);
        }}
        
        .btn-play {{
            background: linear-gradient(135deg, #007aff 0%, #5ac8fa 100%);
            color: white;
        }}
        
        .btn-play:hover {{
            transform: scale(1.05);
        }}
        
        .btn-disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}
        
        .timer {{
            font-size: 24px;
            font-weight: bold;
            text-align: center;
            margin: 15px 0;
            font-family: 'SF Mono', Monaco, monospace;
        }}
        
        .status-bar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 15px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            margin-top: 15px;
            font-size: 12px;
        }}
        
        .markers-panel {{
            margin-top: 15px;
            padding: 15px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            max-height: 150px;
            overflow-y: auto;
        }}
        
        .markers-title {{
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 10px;
            color: #aaa;
        }}
        
        .marker-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            margin-bottom: 6px;
            cursor: pointer;
            transition: background 0.2s;
        }}
        
        .marker-item:hover {{
            background: rgba(255, 255, 255, 0.2);
        }}
        
        .marker-time {{
            font-family: 'SF Mono', Monaco, monospace;
            color: #5ac8fa;
        }}
        
        .marker-label {{
            color: #fff;
            font-size: 13px;
        }}
        
        .hidden {{
            display: none !important;
        }}
        
        .playback-controls {{
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-top: 10px;
        }}
        
        .playback-btn {{
            padding: 8px 16px;
            border: none;
            border-radius: 20px;
            background: rgba(255, 255, 255, 0.2);
            color: white;
            cursor: pointer;
            font-size: 12px;
            transition: background 0.2s;
        }}
        
        .playback-btn:hover {{
            background: rgba(255, 255, 255, 0.3);
        }}
    </style>
</head>
<body>
    <div class="video-recorder">
        <div class="recorder-header">
            <div class="recorder-title">
                📹 Interview Recording
            </div>
            <div class="recording-indicator" id="rec-indicator">
                <div class="rec-dot"></div>
                <span>REC</span>
            </div>
        </div>
        
        <div class="video-container">
            <video id="preview-video" autoplay muted playsinline></video>
            <video id="playback-video" class="hidden" controls playsinline></video>
        </div>
        
        <div class="timer" id="timer">00:00:00</div>
        
        <div class="controls">
            <button class="control-btn btn-record" id="btn-record" onclick="toggleRecording()">
                <span id="record-icon">⏺</span>
                <span id="record-text">Start Recording</span>
            </button>
            <button class="control-btn btn-download hidden" id="btn-download" onclick="downloadRecording()">
                💾 Download
            </button>
            <button class="control-btn btn-play hidden" id="btn-play" onclick="togglePlayback()">
                ▶️ Review
            </button>
        </div>
        
        <div class="status-bar">
            <span id="status-text">Ready to record</span>
            <span id="file-size">--</span>
        </div>
        
        <div class="markers-panel" id="markers-panel">
            <div class="markers-title">📍 Question Markers</div>
            <div id="markers-list"></div>
        </div>
    </div>
    
    <script>
    (function() {{
        const sessionId = '{session_id}';
        let mediaRecorder = null;
        let recordedChunks = [];
        let stream = null;
        let isRecording = false;
        let startTime = null;
        let timerInterval = null;
        let markers = [];
        let recordedBlob = null;
        
        const previewVideo = document.getElementById('preview-video');
        const playbackVideo = document.getElementById('playback-video');
        const btnRecord = document.getElementById('btn-record');
        const btnDownload = document.getElementById('btn-download');
        const btnPlay = document.getElementById('btn-play');
        const recIndicator = document.getElementById('rec-indicator');
        const timerDisplay = document.getElementById('timer');
        const statusText = document.getElementById('status-text');
        const fileSize = document.getElementById('file-size');
        const markersList = document.getElementById('markers-list');
        const recordIcon = document.getElementById('record-icon');
        const recordText = document.getElementById('record-text');
        
        // Initialize webcam
        async function initCamera() {{
            try {{
                stream = await navigator.mediaDevices.getUserMedia({{
                    video: {{ 
                        width: {{ ideal: 1280 }},
                        height: {{ ideal: 720 }},
                        facingMode: 'user'
                    }},
                    audio: true
                }});
                previewVideo.srcObject = stream;
                statusText.textContent = 'Camera ready';
            }} catch (err) {{
                console.error('Camera error:', err);
                statusText.textContent = 'Camera access denied';
            }}
        }}
        
        // Toggle recording
        window.toggleRecording = function() {{
            if (isRecording) {{
                stopRecording();
            }} else {{
                startRecording();
            }}
        }};
        
        // Start recording
        function startRecording() {{
            if (!stream) {{
                statusText.textContent = 'No camera access';
                return;
            }}
            
            recordedChunks = [];
            markers = [];
            markersList.innerHTML = '';
            
            const options = {{ mimeType: 'video/webm;codecs=vp9,opus' }};
            try {{
                mediaRecorder = new MediaRecorder(stream, options);
            }} catch (e) {{
                // Fallback
                mediaRecorder = new MediaRecorder(stream);
            }}
            
            mediaRecorder.ondataavailable = (event) => {{
                if (event.data.size > 0) {{
                    recordedChunks.push(event.data);
                    updateFileSize();
                }}
            }};
            
            mediaRecorder.onstop = () => {{
                recordedBlob = new Blob(recordedChunks, {{ type: 'video/webm' }});
                const url = URL.createObjectURL(recordedBlob);
                playbackVideo.src = url;
                
                btnDownload.classList.remove('hidden');
                btnPlay.classList.remove('hidden');
                
                // Save to localStorage (metadata only, not the blob)
                saveRecordingMetadata();
            }};
            
            mediaRecorder.start(1000); // Collect data every second
            isRecording = true;
            startTime = Date.now();
            
            // Update UI
            recIndicator.classList.add('active');
            btnRecord.classList.add('recording');
            recordIcon.textContent = '⏹';
            recordText.textContent = 'Stop Recording';
            statusText.textContent = 'Recording...';
            
            // Start timer
            timerInterval = setInterval(updateTimer, 1000);
            
            // Add initial marker
            addMarker('Recording Started');
            
            // Notify Streamlit
            notifyStreamlit('recording_started');
        }}
        
        // Stop recording
        function stopRecording() {{
            if (mediaRecorder && isRecording) {{
                mediaRecorder.stop();
                isRecording = false;
                
                // Update UI
                recIndicator.classList.remove('active');
                btnRecord.classList.remove('recording');
                recordIcon.textContent = '⏺';
                recordText.textContent = 'New Recording';
                statusText.textContent = 'Recording saved';
                
                clearInterval(timerInterval);
                
                // Add end marker
                addMarker('Recording Ended');
                
                // Notify Streamlit
                notifyStreamlit('recording_stopped');
            }}
        }}
        
        // Update timer display
        function updateTimer() {{
            if (!startTime) return;
            const elapsed = Date.now() - startTime;
            const hours = Math.floor(elapsed / 3600000);
            const minutes = Math.floor((elapsed % 3600000) / 60000);
            const seconds = Math.floor((elapsed % 60000) / 1000);
            timerDisplay.textContent = 
                String(hours).padStart(2, '0') + ':' +
                String(minutes).padStart(2, '0') + ':' +
                String(seconds).padStart(2, '0');
        }}
        
        // Update file size display
        function updateFileSize() {{
            const totalSize = recordedChunks.reduce((acc, chunk) => acc + chunk.size, 0);
            const sizeMB = (totalSize / (1024 * 1024)).toFixed(2);
            fileSize.textContent = sizeMB + ' MB';
        }}
        
        // Add timestamp marker
        window.addMarker = function(label) {{
            if (!startTime && !recordedBlob) return;
            
            const timestamp = startTime ? Date.now() - startTime : 0;
            const marker = {{
                time: timestamp,
                label: label,
                formatted: formatTime(timestamp)
            }};
            markers.push(marker);
            
            const markerEl = document.createElement('div');
            markerEl.className = 'marker-item';
            markerEl.innerHTML = `
                <span class="marker-time">${{marker.formatted}}</span>
                <span class="marker-label">${{label}}</span>
            `;
            markerEl.onclick = () => seekToMarker(timestamp);
            markersList.appendChild(markerEl);
        }};
        
        // Format time for display
        function formatTime(ms) {{
            const minutes = Math.floor(ms / 60000);
            const seconds = Math.floor((ms % 60000) / 1000);
            return String(minutes).padStart(2, '0') + ':' + String(seconds).padStart(2, '0');
        }}
        
        // Seek to marker in playback
        function seekToMarker(timestamp) {{
            if (playbackVideo.src) {{
                previewVideo.classList.add('hidden');
                playbackVideo.classList.remove('hidden');
                playbackVideo.currentTime = timestamp / 1000;
                playbackVideo.play();
            }}
        }}
        
        // Toggle playback view
        window.togglePlayback = function() {{
            if (playbackVideo.classList.contains('hidden')) {{
                previewVideo.classList.add('hidden');
                playbackVideo.classList.remove('hidden');
                playbackVideo.play();
                btnPlay.innerHTML = '📹 Live View';
            }} else {{
                playbackVideo.classList.add('hidden');
                previewVideo.classList.remove('hidden');
                playbackVideo.pause();
                btnPlay.innerHTML = '▶️ Review';
            }}
        }};
        
        // Download recording
        window.downloadRecording = function() {{
            if (!recordedBlob) return;
            
            const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '');
            const filename = `HireSense_Interview_${{timestamp}}.webm`;
            
            const url = URL.createObjectURL(recordedBlob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            statusText.textContent = 'Downloaded: ' + filename;
        }};
        
        // Save recording metadata
        function saveRecordingMetadata() {{
            const metadata = {{
                sessionId: sessionId,
                timestamp: new Date().toISOString(),
                duration: timerDisplay.textContent,
                markers: markers,
                fileSize: fileSize.textContent
            }};
            
            // Save to localStorage
            const recordings = JSON.parse(localStorage.getItem('hiresense_recordings') || '[]');
            recordings.push(metadata);
            localStorage.setItem('hiresense_recordings', JSON.stringify(recordings));
        }}
        
        // Notify Streamlit of events
        function notifyStreamlit(event, data = {{}}) {{
            window.parent.postMessage({{
                type: 'streamlit:setComponentValue',
                value: {{
                    event: event,
                    sessionId: sessionId,
                    timestamp: Date.now(),
                    ...data
                }}
            }}, '*');
        }}
        
        // Listen for question markers from Streamlit
        window.addEventListener('message', (event) => {{
            if (event.data && event.data.type === 'add_marker') {{
                addMarker(event.data.label || 'Question');
            }}
        }});
        
        // Expose addMarker globally for external calls
        window.addInterviewMarker = addMarker;
        
        // Initialize
        initCamera();
    }})();
    </script>
</body>
</html>
'''


def render_video_recorder(height: int = 550, session_id: str = "default"):
    """Render the video recording component in Streamlit."""
    html_code = get_video_recorder_html(session_id)
    components.html(html_code, height=height)


def add_question_marker_js(question_num: int) -> str:
    """Generate JavaScript to add a question marker."""
    return f'''
    <script>
    (function() {{
        if (window.addInterviewMarker) {{
            window.addInterviewMarker('Question {question_num}');
        }}
    }})();
    </script>
    '''


# ============================================================================
# Recording Playback Component
# ============================================================================

def get_recordings_list_html() -> str:
    """Generate HTML for displaying past recordings."""
    return '''
<!DOCTYPE html>
<html>
<head>
    <style>
        .recordings-list {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            padding: 15px;
        }
        
        .recording-card {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 12px;
            border: 1px solid #dee2e6;
        }
        
        .recording-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .recording-title {
            font-weight: 600;
            color: #333;
        }
        
        .recording-date {
            font-size: 12px;
            color: #666;
        }
        
        .recording-stats {
            display: flex;
            gap: 15px;
            font-size: 13px;
            color: #555;
        }
        
        .stat-item {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .no-recordings {
            text-align: center;
            padding: 40px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="recordings-list" id="recordings-list">
        <div class="no-recordings" id="no-recordings">
            No recordings yet. Start an interview to record!
        </div>
    </div>
    
    <script>
    (function() {
        const recordings = JSON.parse(localStorage.getItem('hiresense_recordings') || '[]');
        const container = document.getElementById('recordings-list');
        const noRecordings = document.getElementById('no-recordings');
        
        if (recordings.length > 0) {
            noRecordings.style.display = 'none';
            
            recordings.reverse().forEach((rec, index) => {
                const card = document.createElement('div');
                card.className = 'recording-card';
                card.innerHTML = `
                    <div class="recording-header">
                        <span class="recording-title">📹 Interview Recording ${recordings.length - index}</span>
                        <span class="recording-date">${new Date(rec.timestamp).toLocaleDateString()}</span>
                    </div>
                    <div class="recording-stats">
                        <span class="stat-item">⏱️ ${rec.duration}</span>
                        <span class="stat-item">📍 ${rec.markers?.length || 0} markers</span>
                        <span class="stat-item">💾 ${rec.fileSize}</span>
                    </div>
                `;
                container.appendChild(card);
            });
        }
    })();
    </script>
</body>
</html>
'''


def render_recordings_list(height: int = 300):
    """Render the list of past recordings."""
    html_code = get_recordings_list_html()
    components.html(html_code, height=height)


# ============================================================================
# Session State Helpers
# ============================================================================

def init_recording_state():
    """Initialize recording-related session state."""
    if "recording_enabled" not in st.session_state:
        st.session_state["recording_enabled"] = False
    if "recording_session_id" not in st.session_state:
        st.session_state["recording_session_id"] = None


def start_recording_session() -> str:
    """Start a new recording session and return session ID."""
    session_id = f"interview_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    st.session_state["recording_session_id"] = session_id
    st.session_state["recording_enabled"] = True
    return session_id


def stop_recording_session():
    """Stop the current recording session."""
    st.session_state["recording_enabled"] = False
