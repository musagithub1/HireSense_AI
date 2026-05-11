# HireSense AI - Agentic Interview Platform 🚀

[![Hackathon](https://img.shields.io/badge/Hackathon-AI%20Seekho%202026-blue.svg)](https://aiseekho.org/)
[![Google Antigravity](https://img.shields.io/badge/Powered%20By-Google%20Antigravity-orange.svg)]()
[![Python Version](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Streamlit Version](https://img.shields.io/badge/Streamlit-1.28%2B-red.svg)](https://streamlit.io/)

**HireSense AI** is an autonomous, agentic mock-interview platform built specifically for the AI Seekho 2026 Hackathon. Unlike traditional "prompt-in, text-out" chatbots, HireSense uses **Google Antigravity Workflows** to actively reason, use tools, and adapt its strategy based on your live emotional state.

---

## 🏆 Hackathon Criteria Alignment

Our project was built from the ground up to max out the judging rubric:

1. **Google Antigravity Integration (25%)**
   We utilized the Google Antigravity AI assistant to architect and autonomously deploy our core agentic logic, ensuring best practices in tool-use frameworks and LLM pipeline refactoring.
2. **Agentic Reasoning & Workflow (20%)**
   Our AI pauses to plan. It uses internal tools (`ProfileAnalyzerTool`, `EmotionAdaptationTool`, `CompanyCultureTool`) to gather insights before formulating any interview question.
3. **Problem Understanding & Decision Quality (20%)**
   The agent makes high-quality decisions based on live environmental data. Using client-side computer vision, it reads the candidate's facial expressions and autonomously decides to shift its interviewing strategy—becoming warm and supportive if the user is stressed, or asking deep technical follow-ups if they are confident.
4. **Action Simulation & Visible Outcomes (15%)**
   We provide total transparency through a live **"Agent Traces"** UI. As the interview progresses, users can visibly see the AI's internal thought logs, simulating its actions and tool usage live on the screen.
5. **Technical Implementation & Innovation (20%)**
   We combined client-side TensorFlow.js (for zero-latency, privacy-preserving emotion tracking) with a Python Streamlit frontend and a LangChain backend to create an incredibly seamless UX.

---

## ✨ Features

- **🧠 Agentic Workflows:** Transparent "Thought Process" logging so you can see exactly how the AI decides to ask its next question.
- **🎭 Real-Time Emotion Detection:** Uses your webcam (via TensorFlow.js in the browser) to detect if you are stressed or confident. 
- **📚 RAG Personalization:** Upload your resume and job description so the AI can find your specific skill gaps and target them.
- **🎤 Voice Input & 🔊 TTS Output:** Speak your answers naturally. The AI talks back to you.
- **💻 Integrated Coding Whiteboard:** Practice technical rounds with a built-in code editor.

---

## 🛠️ Tech Stack

- **Frontend:** Streamlit, HTML, CSS, JavaScript
- **AI/LLM Logic:** LangChain, OpenRouter (Gemini 2.0 Flash / Google Antigravity Agent Engine)
- **Computer Vision:** TensorFlow.js, OpenCV, MediaPipe
- **Voice/Audio:** Web Speech Recognition API

---

## 🚀 Quickstart Guide

### 1. Clone the Repository
```bash
git clone https://github.com/musagithub1/HireSense_AI.git
cd HireSense_AI
```

### 2. Set Up the Environment
```bash
python3 -m venv venvv
source venvv/bin/activate
pip install -r requirements.txt
```

### 3. Configure API Keys
Create a `.env` file in the root directory:
```bash
OPENROUTER_API_KEY="sk-or-v1-your-actual-key-here"
```

### 4. Run the Application
```bash
streamlit run app.py
```
*Open your browser to `http://localhost:8501` and start your HireSense session!*

---

## 🏗️ Architecture

- `antigravity_agent.py`: The core reasoning loop where the agent uses tools to plan.
- `app.py`: The main Streamlit dashboard and UI rendering.
- `interview_arena.py`: Handles the interaction between the UI and the Antigravity Agent.
- `webcam_component.py`: Injects the TensorFlow.js emotion model directly into the client's browser.

---

**Built with ❤️ for AI Seekho 2026**
