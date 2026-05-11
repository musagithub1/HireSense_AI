# HireSense AI

[![Python Version](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Streamlit Version](https://img.shields.io/badge/Streamlit-1.28%2B-orange.svg)](https://streamlit.io/)
[![LangChain](https://img.shields.io/badge/LangChain-0.1%2B-purple.svg)](https://www.langchain.com/)
[![OpenRouter](https://img.shields.io/badge/OpenRouter-API-brightgreen.svg)](https://openrouter.ai/)

**HireSense AI** is an intelligent, adaptive interview platform that helps job seekers prepare for their dream roles. By combining cutting-edge AI with real-time emotion detection, HireSense AI creates a realistic and personalized HireSense Session that adapts to your emotional state, providing actionable feedback to improve your performance.

---

## Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [How It Works](#-how-it-works)
- [Tech Stack](#-tech-stack)
- [Architecture](#-architecture)
- [File Structure](#-file-structure)
- [Setup and Installation](#-setup-and-installation)
- [Configuration](#-configuration)
- [Usage Guide](#-usage-guide)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

Preparing for a job interview can be stressful. Traditional practice methods lack the dynamic, real-world pressure of an actual interview. **HireSense AI** solves this by creating an immersive HireSense Session that:

- **Personalizes questions** based on your resume and the target job description.
- **Reads your emotions** in real-time using your webcam.
- **Adapts its behavior** to be supportive when you're stressed or more challenging when you're confident.
- **Lets you speak naturally** with voice input and text-to-speech output.
- **Provides a detailed performance report** with analytics and AI-generated feedback.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| **📚 RAG Personalization** | Upload your resume and the job description. The AI uses Retrieval-Augmented Generation (RAG) to create highly relevant, personalized interview questions tailored to your background and the role you're applying for. |
| **🎭 Real-Time Emotion Detection** | Using your webcam and a client-side TensorFlow.js model, HireSense AI analyzes your facial expressions to detect your emotional state (e.g., stressed, confident, neutral) throughout the interview. |
| **🔄 Adaptive AI Interviewer** | The AI interviewer dynamically adjusts its tone and question difficulty based on your detected emotional state. If you seem nervous, it becomes more supportive. If you're confident, it increases the challenge. |
| **🎤 Voice Input & 🔊 TTS Output** | Speak your answers using your microphone, just like a real interview. The AI interviewer's questions are read aloud using the browser's Text-to-Speech (TTS) API for a more immersive experience. |
| **📊 Interview Analytics & AI Report Card** | After the interview, receive a comprehensive performance dashboard. This includes stress level graphs over time, composure scores, engagement metrics, and a detailed AI-generated report card with personalized recommendations for improvement. |
| **🎯 Interview Type Selection** | Choose from 5 interview types: **Technical** (coding, system design), **Behavioral** (STAR method, soft skills), **HR** (culture fit, career goals), **Case Study** (analytical thinking), or **Mixed** (comprehensive). The AI tailors questions accordingly. |
| **📚 Question Bank & History** | All your past interviews are saved to your browser's localStorage. Review previous sessions, see your answers, and track your improvement over time. Filter by interview type. |
| **🌐 Multi-Language Support** | Practice interviews in multiple languages including English, Spanish, French, German, Chinese, Japanese, and more. The AI adapts its questions and feedback to your chosen language. |
| **🏢 Company-Specific Prep** | Get tailored preparation for top companies like Google, Amazon, Meta, Apple, Microsoft, and more. Learn about their interview styles, leadership principles, and common questions. |
| **🎬 Video Recording** | Record your interview sessions for later review. Watch your performance, analyze your body language, and identify areas for improvement. |
| **🔄 AI Follow-up Questions** | The AI interviewer asks intelligent follow-up questions based on your answers, just like a real interviewer would. This helps you practice thinking on your feet. |
| **📊 Skill Gap Analysis** | Upload your resume and a job description to get a detailed analysis of your skill gaps. Receive personalized recommendations and learning paths to close those gaps. |
| **🤖 Live Interview Copilot** | Get real-time assistance during your actual interviews on Zoom, Teams, or Meet. The copilot listens to questions and provides smart suggestions, STAR-formatted answers, and confidence boosts. |
| **💻 Integrated Coding & Whiteboard** | Practice coding problems with a full-featured code editor supporting Python, JavaScript, Java, C++, and SQL. Use the digital whiteboard for system design diagrams. Get AI-powered code reviews and hints. |
| **🔍 Advanced Non-Verbal Analysis** | After recording your interview, get detailed feedback on your non-verbal communication: eye contact tracking, posture analysis, and filler word detection. Uses MediaPipe for computer vision and speech analysis. |

---

## ⚙️ How It Works

The HireSense AI interview process follows these steps:

1.  **Setup:** You upload your resume (PDF) and the job description (PDF or text). The system parses these documents to build a personalized context.

2.  **Session Start:** HireSense AI introduces itself and begins asking questions. Questions are generated based on the RAG context from your resume and the job description.

3.  **Real-Time Analysis:** As you answer, the webcam component continuously analyzes your facial expressions. The detected emotion (stressed, confident, neutral) is fed back to the AI.

4.  **Adaptive Questioning:** The AI uses your emotional state to adapt its next question. A stressed candidate might receive a simpler, more encouraging question, while a confident candidate might face a more probing follow-up.

5.  **Voice Interaction:** You can speak your answers, which are transcribed in real-time. The AI's questions are spoken aloud via TTS.

6.  **Completion & HireSense Report:** Once all questions are answered, the session ends. You are presented with an analytics dashboard showing your stress timeline, composure score, and other metrics. The HireSense Report provides detailed feedback and areas for improvement.

---

## 🛠️ Tech Stack

| Category | Technology |
|---|---|
| **Frontend** | Streamlit, HTML, CSS, JavaScript |
| **AI/LLM** | OpenRouter.ai (Gemini, GLM models), LangChain |
| **Emotion Detection** | TensorFlow.js (client-side), face-api.js |
| **Voice Input** | Web Speech Recognition API |
| **Text-to-Speech** | Web Speech Synthesis API |
| **PDF Processing** | PyPDF2 |
| **Monitoring (Optional)** | LangSmith |

---

## 🏗️ Architecture

HireSense AI is built with a modular architecture, separating concerns into distinct Python modules:

| Module | Responsibility |
|---|---|
| `app.py` | The main Streamlit application. It handles the UI, session state, and orchestrates calls to other modules. |
| `config.py` | Manages loading environment variables from the `.env` file. |
| `interview_arena.py` | Contains the core interview logic: RAG context building, adaptive prompt selection based on emotion, question generation, answer evaluation, and final report generation. All LLM calls are streamed. |
| `webcam_component.py` | Generates the HTML/JavaScript for the webcam-based emotion detection component. It uses TensorFlow.js and face-api.js for client-side inference. |
| `voice_input_component.py` | Generates the HTML/JavaScript for the voice input component, using the Web Speech Recognition API. |
| `analytics_dashboard.py` | Calculates performance metrics (composure, engagement, etc.) and renders the analytics dashboard using Streamlit and Pandas. |
| `language_support.py` | Handles multi-language support for the UI and interview sessions. |
| `company_prep.py` | Contains company-specific interview preparation data and guidance. |
| `video_recording.py` | Manages video recording functionality for interview sessions. |
| `followup_questions.py` | Generates intelligent follow-up questions based on candidate answers. |
| `skill_gap_analysis.py` | Analyzes skill gaps between resume and job requirements. |
| `live_copilot.py` | Provides real-time interview assistance with speech recognition and smart suggestions. |
| `coding_whiteboard.py` | Integrated coding environment with Monaco Editor and digital whiteboard. |
| `nonverbal_analysis.py` | Analyzes eye contact, posture, and filler words using MediaPipe and speech analysis. |

**Data Flow:**

```
User Input (Resume, JD) --> RAG Context Builder --> AI Interviewer (LLM)
                                                        |
                                                        v
User Answer (Voice/Text) <-- Question (TTS) <-- Adaptive Prompt Selection
        |                                               ^
        v                                               |
  Answer Evaluation (LLM) --> Emotion Detector (Webcam) --+
        |
        v
  Analytics Dashboard & AI Report Card
```

---

## 📁 File Structure

```
HireSense_AI/
├── .env.example                 # Example environment variables file
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── app.py                       # Main Streamlit application
├── config.py                    # Environment variable loader
├── interview_arena.py           # Core interview logic (RAG, adaptive AI, report)
├── analytics_dashboard.py       # Performance metrics and dashboard
├── webcam_component.py          # Webcam emotion detection (HTML/JS)
├── voice_input_component.py     # Voice input (HTML/JS)
├── voice_recorder.py            # Alternative voice recorder utility
├── language_support.py          # Multi-language support module
├── company_prep.py              # Company-specific interview preparation
├── video_recording.py           # Video recording functionality
├── followup_questions.py        # AI follow-up question generation
├── skill_gap_analysis.py        # Skill gap analysis module
├── live_copilot.py              # Live interview copilot (NEW)
├── coding_whiteboard.py         # Coding & whiteboard environment (NEW)
├── nonverbal_analysis.py        # Non-verbal communication analysis (NEW)
├── models/
│   └── viva_defense_final.keras # Original Keras emotion model (for reference)
└── tfjs_model/                  # TensorFlow.js model for client-side inference
    ├── model.json
    ├── group1-shard1of2.bin
    └── group1-shard2of2.bin
```

---

## 🚀 Setup and Installation

Follow these steps to get HireSense AI running on your local machine.

### Prerequisites

- Python 3.11 or higher
- A modern web browser (Google Chrome or Microsoft Edge recommended for best voice/webcam support)
- A webcam and microphone

### Installation Steps

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/HireSense_AI.git
    cd HireSense_AI
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure your API key:**
    ```bash
    cp .env.example .env
    ```
    Open the `.env` file in a text editor and replace `your_openrouter_api_key_here` with your actual API key from [OpenRouter.ai](https://openrouter.ai/).

5.  **Run the application:**
    ```bash
    streamlit run app.py
    ```
    The application will open in your default web browser at `http://localhost:8501`.

---

## ⚙️ Configuration

HireSense AI requires an API key from OpenRouter to power its AI features.

### Required: OpenRouter API Key

1.  Go to [OpenRouter.ai](https://openrouter.ai/) and create an account.
2.  Generate an API key.
3.  Add the key to your `.env` file:
    ```
    OPENROUTER_API_KEY=sk-or-v1-your-actual-key-here
    ```

### Optional: LangSmith Tracing

For debugging and monitoring LLM calls, you can enable LangSmith tracing.

1.  Go to [LangSmith](https://smith.langchain.com/) and create an account.
2.  Generate an API key.
3.  Add the following to your `.env` file:
    ```
    LANGCHAIN_API_KEY=your_langsmith_api_key_here
    LANGCHAIN_PROJECT=HireSense_AI
    LANGCHAIN_TRACING_V2=true
    ```

---

## 📖 Usage Guide

### Starting a HireSense Session

1.  **Upload Your Resume:** Click the file uploader and select your resume in PDF format.
2.  **Provide the Job Description:** Either upload a PDF or paste the job description text directly.
3.  **Select Interview Type:** Choose from Technical, Behavioral, HR, Case Study, or Mixed.
4.  **Configure Settings:** Choose the number of questions and enable/disable TTS, webcam, and voice input.
5.  **Start the Session:** Click the "Start HireSense Session" button.

### During the Session

- **Listen to the Question:** If TTS is enabled, HireSense AI will speak the question.
- **Answer:** Type your answer in the text area, or click the microphone button to speak your answer.
- **Submit:** Click "Submit Answer" to proceed to the next question.
- **Monitor Your Emotions:** The webcam panel shows your detected emotional state in real-time.

### After the Session

- **View Analytics:** The dashboard displays your stress timeline, composure score, and engagement metrics.
- **Generate HireSense Report:** Click "Generate HireSense Report" for a comprehensive analysis with personalized feedback.
- **Review Transcript:** Expand the "Full Session Transcript" section to see all questions and answers.

### Question Bank

- Click **"📚 Question Bank"** in the sidebar to view all past interviews.
- Filter interviews by type (Technical, Behavioral, etc.).
- Review your answers and AI reports from previous sessions.
- Data is stored in your browser's localStorage and persists across page refreshes.

### Tips for Best Results

- **Use Chrome or Edge:** These browsers have the best support for the Web Speech API.
- **Good Lighting:** Ensure your face is well-lit for accurate emotion detection.
- **Quiet Environment:** Minimize background noise for better voice transcription.
- **Speak Clearly:** Enunciate your words for the speech-to-text to work effectively.

---

## 🛠️ Troubleshooting

### "OPENROUTER_API_KEY must be set"

- Ensure you have created a `.env` file (not just `.env.example`).
- Verify that your API key is correctly pasted in the `.env` file without extra spaces or quotes.

### Voice Input Not Working

- **Use Chrome or Edge.** Firefox has limited support for the Web Speech API.
- **Allow microphone permissions** when prompted by the browser.
- **Check your microphone settings** in your operating system to ensure the correct device is selected.
- **Refresh the page** and try again.

### Webcam Not Working

- **Allow camera permissions** when prompted by the browser.
- Ensure no other application is using the webcam.
- Try refreshing the page.

### No Sound from TTS

- Check that your speakers or headphones are connected and the volume is up.
- Some browsers require a user interaction (like a click) before playing audio. Try clicking anywhere on the page first.

---

## 🤝 Contributing

Contributions are welcome! If you have ideas for new features, improvements, or bug fixes, please feel free to:

1.  Fork the repository.
2.  Create a new branch for your feature (`git checkout -b feature/your-feature-name`).
3.  Commit your changes (`git commit -m 'Add some feature'`).
4.  Push to the branch (`git push origin feature/your-feature-name`).
5.  Open a Pull Request.

---

## 📜 License

This project is licensed under the MIT License.

---

**HireSense AI** - *Ace your next interview with the power of AI.*
