"""
antigravity_agent.py
====================
Google Antigravity Agentic Workflow Engine

This module introduces an agentic workflow to the HireSense AI application.
Instead of a single LLM prompt, the Antigravity Agent uses tools to reason about
the candidate's profile, emotional state, and company culture before deciding
what question to ask next.

Hackathon Criteria Addressed:
- Agentic Reasoning & Workflow
- Action Simulation & Outcome
- Google Antigravity Integration (Simulated via Agentic framework)
"""

from typing import List, Dict, Any, Iterator
import json
import time
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

# We import ChatOpenRouter from interview_arena to use the same LLM config
from interview_arena import ChatOpenRouter

class AntigravityInterviewerAgent:
    def __init__(self, model_name: str = "google/gemini-2.0-flash-001", temperature: float = 0.5):
        self.llm = ChatOpenRouter(
            model_name=model_name,
            temperature=temperature,
            streaming=False # We use non-streaming for the thought process, then streaming for the final answer
        )
        self.stream_llm = ChatOpenRouter(
            model_name=model_name,
            temperature=temperature,
            streaming=True
        )

    def tool_profile_analyzer(self, context: str) -> str:
        """Analyzes the candidate's RAG context for weaknesses or missing skills."""
        prompt = f"Analyze the following candidate context (Resume and JD) and identify 1-2 potential weaknesses or areas that need further probing.\n\nContext:\n{context[:1500]}"
        response = self.llm.invoke([SystemMessage(content="You are a Profile Analyzer Tool."), HumanMessage(content=prompt)])
        return response.content if hasattr(response, 'content') else "No weaknesses identified."

    def tool_emotion_adaptation(self, emotion: str) -> str:
        """Determines the correct interviewing strategy based on current emotion."""
        if emotion == "stressed":
            return "Candidate is Stressed. Strategy: Lower difficulty, use a warm and supportive tone, offer hints if needed."
        elif emotion == "confident":
            return "Candidate is Confident. Strategy: Increase difficulty, ask probing technical follow-ups, challenge their assumptions."
        else:
            return "Candidate is Neutral. Strategy: Maintain professional, balanced questioning."

    def tool_company_culture(self, company: str) -> str:
        """Fetches company-specific cultural values to inject into the question."""
        prompt = f"What are the core cultural values or leadership principles of {company}? Keep it to 2 sentences."
        response = self.llm.invoke([SystemMessage(content="You are a Company Culture Tool."), HumanMessage(content=prompt)])
        return response.content if hasattr(response, 'content') else "Standard professional values."

    def run_agentic_loop(
        self, 
        rag_context: str, 
        conversation_history: List[Dict[str, str]], 
        emotional_state: str, 
        question_number: int, 
        total_questions: int, 
        interview_type: str,
        company: str = "general"
    ) -> Iterator[Dict[str, Any]]:
        """
        Runs the agentic reasoning loop.
        Yields intermediate trace steps (thoughts, tool usages) and finally the streamed question chunks.
        """
        yield {"type": "trace", "content": "Starting Antigravity Agent reasoning sequence..."}
        time.sleep(0.5)

        # Step 1: Use Emotion Tool
        yield {"type": "trace", "content": f"Invoking EmotionAdaptationTool with state: '{emotional_state}'"}
        emotion_strategy = self.tool_emotion_adaptation(emotional_state)
        yield {"type": "tool_use", "tool": "EmotionAdaptationTool", "result": emotion_strategy}
        time.sleep(0.5)

        # Step 2: Use Profile Analyzer Tool
        yield {"type": "trace", "content": "Invoking ProfileAnalyzerTool to scan for weaknesses..."}
        profile_insights = self.tool_profile_analyzer(rag_context)
        yield {"type": "tool_use", "tool": "ProfileAnalyzerTool", "result": profile_insights}
        
        # Step 3: Use Company Culture Tool if applicable
        culture_insights = ""
        if company and company.lower() != "general":
            yield {"type": "trace", "content": f"Invoking CompanyCultureTool for: '{company}'"}
            culture_insights = self.tool_company_culture(company)
            yield {"type": "tool_use", "tool": "CompanyCultureTool", "result": culture_insights}
        
        yield {"type": "trace", "content": "Reasoning complete. Formulating final question..."}
        time.sleep(0.5)

        # Construct the final prompt to generate the question
        system_prompt = f"""You are HireSense AI, an expert interviewer powered by Google Antigravity Agentic workflows.
You must strictly follow the strategy derived from the agent's tool usage:

=== EMOTION STRATEGY ===
{emotion_strategy}

=== CANDIDATE PROFILE INSIGHTS ===
{profile_insights}

=== COMPANY CULTURE INSIGHTS ===
{culture_insights}

=== INTERVIEW TYPE ===
{interview_type}

Based on these agentic insights, ask question {question_number} out of {total_questions}. 
Keep the question natural and conversational as if spoken aloud."""

        messages = [SystemMessage(content=system_prompt)]
        
        # Add conversation history
        for entry in conversation_history[-6:]:
            if entry["role"] == "assistant":
                messages.append(AIMessage(content=entry["content"]))
            else:
                messages.append(HumanMessage(content=entry["content"]))
        
        # Request next question
        if question_number == 1:
            messages.append(HumanMessage(content=f"Please introduce yourself briefly as HireSense AI and ask the first {interview_type.lower()} question based on my profile insights."))
        else:
            messages.append(HumanMessage(content=f"Ask the next {interview_type.lower()} interview question based on the strategy and insights."))

        # Stream the final answer
        for chunk in self.stream_llm.stream(messages):
            if hasattr(chunk, 'content') and chunk.content:
                yield {"type": "question_chunk", "content": chunk.content}
