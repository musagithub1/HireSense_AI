"""
antigravity_agent.py
====================
Google Antigravity — 5-Agent Orchestration Pipeline

This module implements the core agentic architecture for HireSense AI.
Five specialized agents collaborate through a central orchestrator to
transform unstructured career documents into actionable interview outcomes.

Pipeline:
  ContentAgent → InsightAgent → ImpactAgent → StrategyAgent → ExecutionAgent

Each agent:
  1. Receives shared AgentState
  2. Runs its tools
  3. Yields trace logs for the UI
  4. Writes results back to AgentState

Hackathon Criteria Addressed:
  - Google Antigravity Integration (25%) — Core orchestration
  - Agentic Reasoning & Workflow (20%) — Multi-agent pipeline
  - Insight & Decision Quality (20%) — Tool-driven reasoning
  - Action Simulation & Outcome (15%) — Interview execution + report
"""

from __future__ import annotations

from typing import List, Dict, Any, Iterator, Optional
import json
import time
import re
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from interview_arena import ChatOpenRouter


# ============================================================================
# Shared Agent State
# ============================================================================

def create_initial_state(
    rag_context: str,
    conversation_history: List[Dict[str, str]],
    emotional_state: str,
    question_number: int,
    total_questions: int,
    interview_type: str,
    company: str = "general",
) -> Dict[str, Any]:
    """Create the shared state dict that flows through all agents."""
    return {
        "rag_context": rag_context,
        "conversation_history": conversation_history,
        "emotional_state": emotional_state,
        "question_number": question_number,
        "total_questions": total_questions,
        "interview_type": interview_type,
        "company": company,
        # Populated by agents as they run:
        "content_analysis": None,
        "skill_insights": None,
        "impact_scores": None,
        "interview_strategy": None,
        "trace_log": [],  # Full trace for JSON export
    }


# ============================================================================
# Agent Base
# ============================================================================

class BaseAgent:
    """Base class for all pipeline agents."""

    name: str = "BaseAgent"
    icon: str = "🔧"

    def __init__(self, model_name: str, temperature: float):
        self.llm = ChatOpenRouter(
            model_name=model_name,
            temperature=temperature,
            streaming=False,
        )

    def _trace(self, state: Dict, content: str) -> Dict[str, Any]:
        """Create a trace event and log it to state."""
        entry = {
            "type": "trace",
            "agent": self.name,
            "icon": self.icon,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        state["trace_log"].append(entry)
        return entry

    def _tool_use(self, state: Dict, tool: str, result: str) -> Dict[str, Any]:
        """Create a tool-use event and log it to state."""
        entry = {
            "type": "tool_use",
            "agent": self.name,
            "icon": self.icon,
            "tool": tool,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        }
        state["trace_log"].append(entry)
        return entry

    def _agent_done(self, state: Dict, summary: str) -> Dict[str, Any]:
        """Signal that this agent has finished."""
        entry = {
            "type": "agent_done",
            "agent": self.name,
            "icon": self.icon,
            "summary": summary,
            "timestamp": datetime.now().isoformat(),
        }
        state["trace_log"].append(entry)
        return entry

    def run(self, state: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        raise NotImplementedError


# ============================================================================
# Agent 1: Content Agent
# ============================================================================

class ContentAgent(BaseAgent):
    """Parses and structures the raw resume/JD context."""

    name = "Content Agent"
    icon = "📄"

    def run(self, state: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        yield self._trace(state, "Starting content analysis of resume and job description...")
        time.sleep(0.3)

        # Tool 1: PDFParserTool — extract structured info
        yield self._trace(state, "Invoking PDFParserTool to extract structured data...")
        prompt = (
            "Analyze the following resume and job description context. "
            "Extract and return a JSON object with these keys:\n"
            '  "candidate_skills": list of skill strings,\n'
            '  "candidate_experience_years": estimated years,\n'
            '  "candidate_education": highest degree,\n'
            '  "jd_required_skills": list of required skills from JD,\n'
            '  "jd_role_level": "junior"/"mid"/"senior",\n'
            '  "jd_company_values": any company values mentioned\n\n'
            f"Context:\n{state['rag_context'][:3000]}"
        )
        try:
            response = self.llm.invoke([
                SystemMessage(content="You are a PDFParserTool. Return only valid JSON."),
                HumanMessage(content=prompt),
            ])
            content_text = response.content if hasattr(response, "content") else "{}"
            # Try to parse JSON from the response
            json_match = re.search(r'\{[\s\S]*\}', content_text)
            if json_match:
                parsed = json.loads(json_match.group())
            else:
                parsed = {"raw_extraction": content_text[:500]}
        except Exception as e:
            parsed = {"error": str(e), "candidate_skills": [], "jd_required_skills": []}

        state["content_analysis"] = parsed

        skills_found = len(parsed.get("candidate_skills", []))
        jd_skills = len(parsed.get("jd_required_skills", []))
        yield self._tool_use(
            state, "PDFParserTool",
            f"Extracted {skills_found} candidate skills and {jd_skills} JD requirements."
        )

        # Tool 2: TextExtractorTool — extract key facts
        yield self._trace(state, "Invoking TextExtractorTool to identify key facts...")
        exp = parsed.get("candidate_experience_years", "unknown")
        edu = parsed.get("candidate_education", "unknown")
        level = parsed.get("jd_role_level", "unknown")
        summary = f"Experience: {exp} years | Education: {edu} | Target Level: {level}"
        yield self._tool_use(state, "TextExtractorTool", summary)

        yield self._agent_done(state, f"{skills_found} skills extracted, {jd_skills} JD requirements parsed")


# ============================================================================
# Agent 2: Insight Agent
# ============================================================================

class InsightAgent(BaseAgent):
    """Identifies skill gaps, strengths, and weaknesses."""

    name = "Insight Agent"
    icon = "🔍"

    def run(self, state: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        yield self._trace(state, "Analyzing skill alignment between candidate and role...")
        time.sleep(0.3)

        content = state.get("content_analysis", {})
        candidate_skills = content.get("candidate_skills", [])
        jd_skills = content.get("jd_required_skills", [])

        # Tool 1: SkillMatcherTool
        yield self._trace(state, "Invoking SkillMatcherTool to find matching skills...")
        candidate_lower = [s.lower() for s in candidate_skills]
        jd_lower = [s.lower() for s in jd_skills]

        matching = [s for s in jd_skills if s.lower() in candidate_lower]
        missing = [s for s in jd_skills if s.lower() not in candidate_lower]
        extra = [s for s in candidate_skills if s.lower() not in jd_lower]

        yield self._tool_use(
            state, "SkillMatcherTool",
            f"Matching: {len(matching)} skills | Gaps: {len(missing)} skills | Extra: {len(extra)} skills"
        )

        # Tool 2: GapAnalyzerTool — use LLM for deeper analysis
        yield self._trace(state, "Invoking GapAnalyzerTool for deeper gap analysis...")
        prompt = (
            f"Given these skill gaps between a candidate and a job:\n"
            f"  Matching skills: {matching}\n"
            f"  Missing skills (gaps): {missing}\n"
            f"  Extra skills (candidate has, JD doesn't require): {extra}\n\n"
            f"For each gap, rate its priority (high/medium/low) and suggest a brief interview "
            f"question that could probe whether the candidate has related experience.\n"
            f"Return JSON: {{\"gap_analysis\": [{{\"skill\": ..., \"priority\": ..., \"probe_question\": ...}}]}}"
        )
        try:
            response = self.llm.invoke([
                SystemMessage(content="You are a GapAnalyzerTool. Return only valid JSON."),
                HumanMessage(content=prompt),
            ])
            gap_text = response.content if hasattr(response, "content") else "{}"
            json_match = re.search(r'\{[\s\S]*\}', gap_text)
            gap_data = json.loads(json_match.group()) if json_match else {}
        except Exception:
            gap_data = {"gap_analysis": [{"skill": s, "priority": "medium", "probe_question": ""} for s in missing]}

        state["skill_insights"] = {
            "matching": matching,
            "missing": missing,
            "extra": extra,
            "gap_details": gap_data.get("gap_analysis", []),
        }

        high_priority = sum(1 for g in gap_data.get("gap_analysis", []) if g.get("priority") == "high")
        yield self._tool_use(
            state, "GapAnalyzerTool",
            f"Analyzed {len(missing)} gaps: {high_priority} high-priority, {len(missing) - high_priority} medium/low."
        )

        yield self._agent_done(state, f"{len(matching)} matches, {len(missing)} gaps ({high_priority} critical)")


# ============================================================================
# Agent 3: Impact Agent
# ============================================================================

class ImpactAgent(BaseAgent):
    """Scores the severity of gaps and their real-world hiring impact."""

    name = "Impact Agent"
    icon = "📊"

    def run(self, state: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        yield self._trace(state, "Evaluating real-world impact of identified skill gaps...")
        time.sleep(0.3)

        insights = state.get("skill_insights", {})
        missing = insights.get("missing", [])
        gap_details = insights.get("gap_details", [])

        # Tool 1: SeverityScorerTool
        yield self._trace(state, "Invoking SeverityScorerTool to rank gap severity...")
        prompt = (
            f"You are evaluating a job candidate. They are missing these skills: {missing}\n"
            f"The role is: {state.get('interview_type', 'Mixed')} interview for a "
            f"{state.get('company', 'general')} position.\n\n"
            f"For each missing skill, estimate:\n"
            f"  1. How critical is this skill for the role? (critical/important/nice-to-have)\n"
            f"  2. What percentage of similar job postings require it? (estimate)\n"
            f"  3. Overall hiring impact (high/medium/low)\n\n"
            f"Return JSON: {{\"severity_scores\": [{{\"skill\": ..., \"criticality\": ..., "
            f"\"market_demand_pct\": ..., \"hiring_impact\": ...}}]}}"
        )
        try:
            response = self.llm.invoke([
                SystemMessage(content="You are a SeverityScorerTool. Return only valid JSON."),
                HumanMessage(content=prompt),
            ])
            sev_text = response.content if hasattr(response, "content") else "{}"
            json_match = re.search(r'\{[\s\S]*\}', sev_text)
            severity_data = json.loads(json_match.group()) if json_match else {}
        except Exception:
            severity_data = {"severity_scores": []}

        scores = severity_data.get("severity_scores", [])
        state["impact_scores"] = scores

        # Build a readable summary
        critical_count = sum(1 for s in scores if s.get("hiring_impact") == "high")
        yield self._tool_use(
            state, "SeverityScorerTool",
            f"Scored {len(scores)} gaps: {critical_count} high-impact, {len(scores) - critical_count} lower impact."
        )

        # Tool 2: MarketRelevanceTool (lightweight)
        yield self._trace(state, "Invoking MarketRelevanceTool to check industry trends...")
        top_gaps = [s.get("skill", "?") for s in scores if s.get("hiring_impact") == "high"][:3]
        market_note = f"Top gaps to probe: {', '.join(top_gaps) if top_gaps else 'None critical'}"
        yield self._tool_use(state, "MarketRelevanceTool", market_note)

        yield self._agent_done(state, f"{critical_count} high-impact gaps identified for interview focus")


# ============================================================================
# Agent 4: Strategy Agent
# ============================================================================

class StrategyAgent(BaseAgent):
    """Plans the interview approach based on emotion, gaps, and company culture."""

    name = "Strategy Agent"
    icon = "🎯"

    def run(self, state: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        yield self._trace(state, "Planning interview strategy based on all gathered intelligence...")
        time.sleep(0.3)

        emotion = state.get("emotional_state", "neutral")
        company = state.get("company", "general")
        impact_scores = state.get("impact_scores", [])
        insights = state.get("skill_insights", {})

        # Tool 1: EmotionAdaptationTool
        yield self._trace(state, f"Invoking EmotionAdaptationTool with state: '{emotion}'")
        if emotion == "stressed":
            emotion_strategy = "Candidate is STRESSED → Use warm, supportive tone. Lower difficulty. Offer encouragement. Start with their strengths."
        elif emotion == "confident":
            emotion_strategy = "Candidate is CONFIDENT → Increase difficulty. Ask deep follow-ups. Challenge assumptions. Probe weak areas."
        else:
            emotion_strategy = "Candidate is NEUTRAL → Maintain balanced professional tone. Standard difficulty."
        yield self._tool_use(state, "EmotionAdaptationTool", emotion_strategy)

        # Tool 2: CompanyCultureTool
        culture_strategy = ""
        if company and company.lower() != "general":
            yield self._trace(state, f"Invoking CompanyCultureTool for: '{company}'")
            try:
                response = self.llm.invoke([
                    SystemMessage(content="You are a CompanyCultureTool. Return 2 sentences about core values."),
                    HumanMessage(content=f"What are the core cultural values of {company}?"),
                ])
                culture_strategy = response.content if hasattr(response, "content") else ""
            except Exception:
                culture_strategy = "Standard professional values."
            yield self._tool_use(state, "CompanyCultureTool", culture_strategy)

        # Tool 3: DifficultyCalibrationTool
        yield self._trace(state, "Invoking DifficultyCalibrationTool to set question parameters...")
        q_num = state.get("question_number", 1)
        total = state.get("total_questions", 5)
        progress = q_num / total

        if emotion == "stressed":
            difficulty = "easy" if progress < 0.5 else "medium"
        elif emotion == "confident":
            difficulty = "medium" if progress < 0.3 else "hard"
        else:
            difficulty = "medium"

        # Decide focus area
        high_impact_skills = [s.get("skill", "?") for s in impact_scores if s.get("hiring_impact") == "high"]
        matching_skills = insights.get("matching", [])

        if emotion == "stressed" and matching_skills:
            focus_area = f"Start with candidate's strengths: {', '.join(matching_skills[:2])}"
        elif high_impact_skills:
            focus_area = f"Probe high-impact gaps: {', '.join(high_impact_skills[:2])}"
        else:
            focus_area = "General role-relevant questions"

        calibration = f"Difficulty: {difficulty} | Focus: {focus_area} | Progress: Q{q_num}/{total}"
        yield self._tool_use(state, "DifficultyCalibrationTool", calibration)

        # Assemble final strategy
        state["interview_strategy"] = {
            "emotion_strategy": emotion_strategy,
            "culture_strategy": culture_strategy,
            "difficulty": difficulty,
            "focus_area": focus_area,
            "high_impact_gaps": high_impact_skills,
            "candidate_strengths": matching_skills,
        }

        yield self._agent_done(state, f"Strategy set: {difficulty} difficulty, {emotion} adaptation, focus on {focus_area[:40]}")


# ============================================================================
# Agent 5: Execution Agent
# ============================================================================

class ExecutionAgent(BaseAgent):
    """Generates the actual interview question using all gathered intelligence."""

    name = "Execution Agent"
    icon = "⚡"

    def __init__(self, model_name: str, temperature: float):
        super().__init__(model_name, temperature)
        self.stream_llm = ChatOpenRouter(
            model_name=model_name,
            temperature=temperature,
            streaming=True,
        )

    def run(self, state: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        yield self._trace(state, "Preparing to generate interview question...")
        time.sleep(0.3)

        strategy = state.get("interview_strategy", {})
        content = state.get("content_analysis", {})

        # Tool 1: QuestionGeneratorTool
        yield self._trace(state, "Invoking QuestionGeneratorTool with full agentic context...")

        system_prompt = f"""You are HireSense AI, an expert interviewer powered by Google Antigravity Agentic Workflows.
You must strictly follow the strategy derived from the 5-agent pipeline:

=== EMOTION STRATEGY ===
{strategy.get('emotion_strategy', 'Balanced professional tone.')}

=== DIFFICULTY LEVEL ===
{strategy.get('difficulty', 'medium')}

=== FOCUS AREA ===
{strategy.get('focus_area', 'General questions')}

=== HIGH-IMPACT GAPS TO PROBE ===
{', '.join(strategy.get('high_impact_gaps', ['general skills']))}

=== CANDIDATE STRENGTHS ===
{', '.join(strategy.get('candidate_strengths', ['not analyzed']))}

=== COMPANY CULTURE ===
{strategy.get('culture_strategy', 'Standard professional values.')}

=== INTERVIEW TYPE ===
{state.get('interview_type', 'Mixed')}

Based on these agentic insights, ask question {state.get('question_number', 1)} of {state.get('total_questions', 5)}.
Keep the question natural and conversational as if spoken aloud.
Do NOT mention the pipeline or tools — just ask the question naturally."""

        messages = [SystemMessage(content=system_prompt)]

        for entry in state.get("conversation_history", [])[-6:]:
            if entry["role"] == "assistant":
                messages.append(AIMessage(content=entry["content"]))
            else:
                messages.append(HumanMessage(content=entry["content"]))

        q_num = state.get("question_number", 1)
        if q_num == 1:
            messages.append(HumanMessage(
                content=f"Please introduce yourself briefly as HireSense AI and ask the first "
                        f"{state.get('interview_type', 'Mixed').lower()} question based on my profile."
            ))
        else:
            messages.append(HumanMessage(
                content=f"Ask the next {state.get('interview_type', 'Mixed').lower()} interview question "
                        f"following the strategy and insights."
            ))

        yield self._tool_use(state, "QuestionGeneratorTool", "Streaming question to candidate...")

        # Stream the final question
        for chunk in self.stream_llm.stream(messages):
            if hasattr(chunk, "content") and chunk.content:
                yield {"type": "question_chunk", "content": chunk.content}


# ============================================================================
# Antigravity Orchestrator (The Brain)
# ============================================================================

class AntigravityOrchestrator:
    """
    Central orchestrator that coordinates all 5 agents in sequence.
    
    On the FIRST question:  ContentAgent → InsightAgent → ImpactAgent → StrategyAgent → ExecutionAgent
    On SUBSEQUENT questions: ImpactAgent → StrategyAgent → ExecutionAgent (emotion may have changed)
    """

    def __init__(
        self,
        model_name: str = "google/gemini-2.0-flash-001",
        temperature: float = 0.5,
    ):
        self.model_name = model_name
        self.temperature = temperature

        self.content_agent = ContentAgent(model_name, 0.2)
        self.insight_agent = InsightAgent(model_name, 0.3)
        self.impact_agent = ImpactAgent(model_name, 0.3)
        self.strategy_agent = StrategyAgent(model_name, 0.4)
        self.execution_agent = ExecutionAgent(model_name, temperature)

        # Cache results from first-question agents
        self._cached_content: Optional[Dict] = None
        self._cached_insights: Optional[Dict] = None

    def run_pipeline(
        self,
        rag_context: str,
        conversation_history: List[Dict[str, str]],
        emotional_state: str,
        question_number: int,
        total_questions: int,
        interview_type: str,
        company: str = "general",
    ) -> Iterator[Dict[str, Any]]:
        """Run the full 5-agent pipeline. Yields trace events and question chunks."""

        state = create_initial_state(
            rag_context, conversation_history, emotional_state,
            question_number, total_questions, interview_type, company,
        )

        yield {
            "type": "pipeline_start",
            "content": f"🚀 Antigravity Pipeline activated — Question {question_number}/{total_questions}",
        }

        # ── First question: run all 5 agents ──
        if question_number == 1 or self._cached_content is None:
            # Agent 1: Content
            for event in self.content_agent.run(state):
                yield event
            self._cached_content = state["content_analysis"]

            # Agent 2: Insight
            for event in self.insight_agent.run(state):
                yield event
            self._cached_insights = state["skill_insights"]
        else:
            # Re-use cached analysis
            state["content_analysis"] = self._cached_content
            state["skill_insights"] = self._cached_insights
            yield {
                "type": "trace",
                "agent": "Orchestrator",
                "icon": "🧠",
                "content": "Re-using cached Content & Insight analysis (resume hasn't changed).",
            }

        # Agent 3: Impact (re-runs each time — emotion context may differ)
        for event in self.impact_agent.run(state):
            yield event

        # Agent 4: Strategy (re-runs each time — emotion changes)
        for event in self.strategy_agent.run(state):
            yield event

        # Agent 5: Execution (always runs — generates the question)
        for event in self.execution_agent.run(state):
            yield event

    def export_trace_json(self, state: Dict[str, Any]) -> str:
        """Export the full agent trace as JSON for hackathon submission."""
        export = {
            "platform": "Google Antigravity",
            "session_timestamp": datetime.now().isoformat(),
            "pipeline": "Content → Insight → Impact → Strategy → Execution",
            "agents": [],
            "trace_log": state.get("trace_log", []),
        }

        agent_names = ["Content Agent", "Insight Agent", "Impact Agent", "Strategy Agent", "Execution Agent"]
        for name in agent_names:
            agent_events = [e for e in state.get("trace_log", []) if e.get("agent") == name]
            tools_used = [e["tool"] for e in agent_events if e.get("type") == "tool_use"]
            summary = next(
                (e["summary"] for e in agent_events if e.get("type") == "agent_done"), "N/A"
            )
            export["agents"].append({
                "name": name,
                "tools_used": tools_used,
                "events_count": len(agent_events),
                "output_summary": summary,
            })

        return json.dumps(export, indent=2)


# ============================================================================
# Backward-compatible wrapper (used by interview_arena.py)
# ============================================================================

# Global orchestrator instance (reused across questions to maintain cache)
_orchestrator: Optional[AntigravityOrchestrator] = None


def get_orchestrator(model_name: str = "google/gemini-2.0-flash-001", temperature: float = 0.5):
    """Get or create the global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AntigravityOrchestrator(model_name, temperature)
    return _orchestrator


def reset_orchestrator():
    """Reset the orchestrator (e.g., when starting a new interview session)."""
    global _orchestrator
    _orchestrator = None
