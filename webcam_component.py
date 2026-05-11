"""
webcam_component.py
===================

Webcam-based emotion detection component for Streamlit.
Uses TensorFlow.js for client-side inference with the Viva Defense model.
"""

import streamlit.components.v1 as components
import os
import json

def get_webcam_emotion_detector_html(model_path: str = "./tfjs_model/model.json") -> str:
    """
    Generate HTML/JS code for webcam-based emotion detection.
    
    The component:
    1. Accesses the webcam
    2. Detects faces using face-api.js
    3. Preprocesses face images (grayscale, resize to 48x48)
    4. Runs inference using TensorFlow.js
    5. Reports stress/confidence levels
    """
    
    html_code = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@4.17.0/dist/tf.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.12/dist/face-api.min.js"></script>
        <style>
            .container {{
                display: flex;
                flex-direction: column;
                align-items: center;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            #video-container {{
                position: relative;
                width: 280px;
                height: 210px;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }}
            #webcam {{
                width: 100%;
                height: 100%;
                object-fit: cover;
                transform: scaleX(-1);
            }}
            #overlay {{
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                pointer-events: none;
            }}
            #status-panel {{
                margin-top: 15px;
                padding: 15px;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                border-radius: 10px;
                width: 260px;
                text-align: center;
            }}
            .emotion-display {{
                font-size: 24px;
                font-weight: bold;
                margin: 10px 0;
            }}
            .stress-bar {{
                width: 100%;
                height: 20px;
                background: #e0e0e0;
                border-radius: 10px;
                overflow: hidden;
                margin: 10px 0;
            }}
            .stress-fill {{
                height: 100%;
                transition: width 0.3s ease, background-color 0.3s ease;
                border-radius: 10px;
            }}
            .stats {{
                display: flex;
                justify-content: space-between;
                font-size: 12px;
                color: #666;
            }}
            .loading {{
                color: #666;
                font-style: italic;
            }}
            .error {{
                color: #e74c3c;
            }}
            .face-box {{
                position: absolute;
                border: 2px solid #4CAF50;
                border-radius: 4px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div id="video-container">
                <video id="webcam" autoplay playsinline muted></video>
                <canvas id="overlay"></canvas>
            </div>
            <div id="status-panel">
                <div id="status" class="loading">Initializing...</div>
                <div id="emotion-display" class="emotion-display">--</div>
                <div class="stress-bar">
                    <div id="stress-fill" class="stress-fill" style="width: 50%; background: #ffc107;"></div>
                </div>
                <div class="stats">
                    <span>Confident</span>
                    <span id="stress-percent">50%</span>
                    <span>Stressed</span>
                </div>
            </div>
        </div>
        
        <script>
        (async function() {{
            const video = document.getElementById('webcam');
            const overlay = document.getElementById('overlay');
            const ctx = overlay.getContext('2d');
            const statusDiv = document.getElementById('status');
            const emotionDiv = document.getElementById('emotion-display');
            const stressFill = document.getElementById('stress-fill');
            const stressPercent = document.getElementById('stress-percent');
            
            let model = null;
            let faceDetector = null;
            let isProcessing = false;
            let stressHistory = [];
            
            // Update stress display
            function updateStressDisplay(stressLevel) {{
                const percent = Math.round(stressLevel * 100);
                stressPercent.textContent = percent + '% stress';
                stressFill.style.width = percent + '%';
                
                // Color gradient from green (confident) to red (stressed)
                if (stressLevel < 0.3) {{
                    stressFill.style.background = '#4CAF50';
                    emotionDiv.textContent = '😊 Confident';
                    emotionDiv.style.color = '#4CAF50';
                }} else if (stressLevel < 0.5) {{
                    stressFill.style.background = '#8BC34A';
                    emotionDiv.textContent = '🙂 Calm';
                    emotionDiv.style.color = '#8BC34A';
                }} else if (stressLevel < 0.7) {{
                    stressFill.style.background = '#ffc107';
                    emotionDiv.textContent = '😐 Neutral';
                    emotionDiv.style.color = '#ffc107';
                }} else {{
                    stressFill.style.background = '#f44336';
                    emotionDiv.textContent = '😰 Stressed';
                    emotionDiv.style.color = '#f44336';
                }}
                
                // Send to Streamlit
                stressHistory.push(stressLevel);
                if (stressHistory.length > 100) stressHistory.shift();
                
                // Post message to parent (Streamlit)
                window.parent.postMessage({{
                    type: 'streamlit:setComponentValue',
                    value: {{
                        stress_level: stressLevel,
                        state: stressLevel > 0.5 ? 'stressed' : 'confident',
                        timestamp: Date.now()
                    }}
                }}, '*');
            }}
            
            // Preprocess image for model
            function preprocessImage(imageData) {{
                return tf.tidy(() => {{
                    // Convert to tensor
                    let tensor = tf.browser.fromPixels(imageData, 1); // Grayscale
                    
                    // Resize to 48x48
                    tensor = tf.image.resizeBilinear(tensor, [48, 48]);
                    
                    // Normalize to [0, 1]
                    tensor = tensor.div(255.0);
                    
                    // Add batch dimension
                    tensor = tensor.expandDims(0);
                    
                    return tensor;
                }});
            }}
            
            // Detect emotion from face
            async function detectEmotion(faceCanvas) {{
                if (!model || isProcessing) return;
                
                isProcessing = true;
                try {{
                    const tensor = preprocessImage(faceCanvas);
                    const prediction = await model.predict(tensor);
                    const stressLevel = (await prediction.data())[0];
                    
                    tensor.dispose();
                    prediction.dispose();
                    
                    updateStressDisplay(stressLevel);
                }} catch (e) {{
                    console.error('Prediction error:', e);
                }}
                isProcessing = false;
            }}
            
            // Process video frame
            async function processFrame() {{
                if (video.readyState !== 4) {{
                    requestAnimationFrame(processFrame);
                    return;
                }}
                
                // Set canvas size
                overlay.width = video.videoWidth;
                overlay.height = video.videoHeight;
                
                // Clear overlay
                ctx.clearRect(0, 0, overlay.width, overlay.height);
                
                try {{
                    // Detect faces
                    const detections = await faceapi.detectAllFaces(
                        video, 
                        new faceapi.TinyFaceDetectorOptions()
                    );
                    
                    if (detections.length > 0) {{
                        const face = detections[0];
                        const box = face.box;
                        
                        // Draw face box (mirrored)
                        ctx.strokeStyle = '#4CAF50';
                        ctx.lineWidth = 2;
                        ctx.strokeRect(
                            overlay.width - box.x - box.width,
                            box.y,
                            box.width,
                            box.height
                        );
                        
                        // Extract face region
                        const faceCanvas = document.createElement('canvas');
                        faceCanvas.width = 48;
                        faceCanvas.height = 48;
                        const faceCtx = faceCanvas.getContext('2d');
                        
                        // Draw face to canvas (grayscale)
                        faceCtx.filter = 'grayscale(100%)';
                        faceCtx.drawImage(
                            video,
                            box.x, box.y, box.width, box.height,
                            0, 0, 48, 48
                        );
                        
                        // Run emotion detection
                        await detectEmotion(faceCanvas);
                        
                        statusDiv.textContent = '📹 Analyzing...';
                        statusDiv.className = '';
                    }} else {{
                        statusDiv.textContent = '👤 No face detected';
                        statusDiv.className = 'loading';
                    }}
                }} catch (e) {{
                    console.error('Frame processing error:', e);
                }}
                
                // Continue processing
                setTimeout(() => requestAnimationFrame(processFrame), 200); // 5 FPS
            }}
            
            // Initialize
            async function init() {{
                try {{
                    statusDiv.textContent = 'Loading face detection...';
                    
                    // Load face-api models
                    await faceapi.nets.tinyFaceDetector.loadFromUri(
                        'https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.12/model'
                    );
                    
                    statusDiv.textContent = 'Loading emotion model...';
                    
                    // Load TensorFlow.js model
                    // For demo, we'll use a simulated model since the actual model
                    // needs to be served from the same origin
                    try {{
                        // Try to load the actual model
                        model = await tf.loadLayersModel('{model_path}');
                        console.log('Loaded actual model');
                    }} catch (e) {{
                        console.log('Using simulated emotion detection');
                        // Create a simple model for demo
                        model = tf.sequential({{
                            layers: [
                                tf.layers.conv2d({{
                                    inputShape: [48, 48, 1],
                                    filters: 32,
                                    kernelSize: 3,
                                    activation: 'relu'
                                }}),
                                tf.layers.maxPooling2d({{poolSize: 2}}),
                                tf.layers.flatten(),
                                tf.layers.dense({{units: 64, activation: 'relu'}}),
                                tf.layers.dense({{units: 1, activation: 'sigmoid'}})
                            ]
                        }});
                    }}
                    
                    statusDiv.textContent = 'Accessing webcam...';
                    
                    // Get webcam stream
                    const stream = await navigator.mediaDevices.getUserMedia({{
                        video: {{ facingMode: 'user', width: 320, height: 240 }}
                    }});
                    
                    video.srcObject = stream;
                    await video.play();
                    
                    statusDiv.textContent = '✅ Ready';
                    
                    // Start processing
                    processFrame();
                    
                }} catch (e) {{
                    console.error('Init error:', e);
                    statusDiv.textContent = '⚠️ ' + e.message;
                    statusDiv.className = 'error';
                }}
            }}
            
            init();
        }})();
        </script>
    </body>
    </html>
    '''
    
    return html_code


def render_webcam_emotion_detector(height: int = 400):
    """Render the webcam emotion detector component in Streamlit."""
    html = get_webcam_emotion_detector_html()
    components.html(html, height=height)


def get_simple_webcam_html() -> str:
    """Get a simpler webcam component that works without external model loading."""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            .container {
                display: flex;
                flex-direction: column;
                align-items: center;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            #video-container {
                position: relative;
                width: 280px;
                height: 210px;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                background: #000;
            }
            #webcam {
                width: 100%;
                height: 100%;
                object-fit: cover;
                transform: scaleX(-1);
            }
            #status-panel {
                margin-top: 15px;
                padding: 15px 15px 20px 15px;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                border-radius: 10px;
                width: 260px;
                text-align: center;
                min-height: 120px;
            }
            .emotion-display {
                font-size: 24px;
                font-weight: bold;
                margin: 10px 0;
            }
            .stress-bar {
                width: 100%;
                height: 20px;
                background: #e0e0e0;
                border-radius: 10px;
                overflow: hidden;
                margin: 10px 0;
            }
            .stress-fill {
                height: 100%;
                transition: width 0.5s ease, background-color 0.5s ease;
                border-radius: 10px;
            }
            .stats {
                display: flex;
                justify-content: space-between;
                font-size: 12px;
                color: #666;
                padding-bottom: 5px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div id="video-container">
                <video id="webcam" autoplay playsinline muted></video>
            </div>
            <div id="status-panel">
                <div id="status">Initializing webcam...</div>
                <div id="emotion-display" class="emotion-display">--</div>
                <div class="stress-bar">
                    <div id="stress-fill" class="stress-fill" style="width: 50%; background: #ffc107;"></div>
                </div>
                <div class="stats">
                    <span>😊 Confident</span>
                    <span id="stress-percent">50%</span>
                    <span>😰 Stressed</span>
                </div>
            </div>
        </div>
        
        <script>
        (async function() {
            const video = document.getElementById('webcam');
            const statusDiv = document.getElementById('status');
            const emotionDiv = document.getElementById('emotion-display');
            const stressFill = document.getElementById('stress-fill');
            const stressPercent = document.getElementById('stress-percent');
            
            // Simulated emotion detection based on motion/brightness
            let prevBrightness = 128;
            let stressLevel = 0.5;
            
            function updateDisplay(stress) {
                const percent = Math.round(stress * 100);
                stressPercent.textContent = percent + '% stress';
                stressFill.style.width = percent + '%';
                
                if (stress < 0.3) {
                    stressFill.style.background = '#4CAF50';
                    emotionDiv.textContent = '😊 Confident';
                    emotionDiv.style.color = '#4CAF50';
                } else if (stress < 0.5) {
                    stressFill.style.background = '#8BC34A';
                    emotionDiv.textContent = '🙂 Calm';
                    emotionDiv.style.color = '#8BC34A';
                } else if (stress < 0.7) {
                    stressFill.style.background = '#ffc107';
                    emotionDiv.textContent = '😐 Neutral';
                    emotionDiv.style.color = '#ffc107';
                } else {
                    stressFill.style.background = '#f44336';
                    emotionDiv.textContent = '😰 Stressed';
                    emotionDiv.style.color = '#f44336';
                }
            }
            
            function analyzeFrame() {
                const canvas = document.createElement('canvas');
                canvas.width = 64;
                canvas.height = 48;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(video, 0, 0, 64, 48);
                
                const imageData = ctx.getImageData(0, 0, 64, 48);
                const data = imageData.data;
                
                // Calculate average brightness and motion
                let brightness = 0;
                for (let i = 0; i < data.length; i += 4) {
                    brightness += (data[i] + data[i+1] + data[i+2]) / 3;
                }
                brightness /= (data.length / 4);
                
                // Motion detection (brightness change)
                const motion = Math.abs(brightness - prevBrightness) / 255;
                prevBrightness = brightness;
                
                // Simulate stress based on motion (more movement = more stress)
                // This is a simplified heuristic - actual model would be more accurate
                const targetStress = 0.3 + motion * 5;
                stressLevel = stressLevel * 0.9 + Math.min(1, targetStress) * 0.1;
                
                updateDisplay(stressLevel);
            }
            
            try {
                const stream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: 'user', width: 320, height: 240 }
                });
                
                video.srcObject = stream;
                await video.play();
                
                statusDiv.textContent = '📹 Webcam active';
                
                // Analyze frames periodically
                setInterval(analyzeFrame, 500);
                
            } catch (e) {
                statusDiv.textContent = '⚠️ ' + e.message;
                console.error('Webcam error:', e);
            }
        })();
        </script>
    </body>
    </html>
    '''
