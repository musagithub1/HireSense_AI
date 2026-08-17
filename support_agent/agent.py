"""LangGraph support-resolution agent backed by AgentRouter."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, TypedDict

from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from .schemas import CaseClassification, IncomingMessage, ResolutionPlan
from .tools import (
    execute_approved_action,
    lookup_customer,
    lookup_order,
    retrieve_policies,
    validate_action,
)


class GraphState(TypedDict, total=False):
    message: dict[str, Any]
    classification: CaseClassification | None
    customer: dict[str, Any] | None
    order: dict[str, Any] | None
    retrieved_context: list[dict[str, Any]]
    risk_flags: list[str]
    plan: ResolutionPlan | None
    approval_required: bool
    approved: bool | None
    execution_result: dict[str, Any] | None
    status: str
    audit_events: list[dict[str, Any]]
    error: str | None


DEFAULT_AGENTROUTER_BASE_URL = "https://agentrouter.org/v1"
DEFAULT_AGENTROUTER_MODEL = "gpt-5.5"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _event(name: str, **details: Any) -> dict[str, Any]:
    return {"timestamp": _now(), "event": name, **details}


def create_agentrouter_llm(
    *,
    model: str | None = None,
    temperature: float = 0,
    api_key: str | None = None,
    base_url: str | None = None,
) -> ChatOpenAI:
    """Create an OpenAI-compatible ChatOpenAI client pointed at AgentRouter.

    AgentRouter's official OpenAI-compatible guide uses
    ``https://agentrouter.org/v1`` and model ID ``gpt-5.5``. The key is read
    from ``AGENTROUTER_API_KEY`` and is never hard-coded.
    """

    load_dotenv()
    resolved_key = api_key or os.getenv("AGENTROUTER_API_KEY")
    if not resolved_key:
        raise RuntimeError(
            "AGENTROUTER_API_KEY is not configured. Add your AgentRouter API key "
            "to the environment before invoking the live agent."
        )
    return ChatOpenAI(
        api_key=resolved_key,
        base_url=base_url or os.getenv("AGENTROUTER_BASE_URL", DEFAULT_AGENTROUTER_BASE_URL),
        model=model or os.getenv("AGENTROUTER_MODEL", DEFAULT_AGENTROUTER_MODEL),
        temperature=temperature,
    )


def _json_messages(message: IncomingMessage) -> list[Any]:
    return [
        SystemMessage(
            content=(
                "You are an e-commerce customer-support triage specialist. "
                "Return only the requested structured fields. Never invent an order "
                "number or policy. Supported intents are order_status, delivery_delay, "
                "return_policy, damaged_item, refund_or_replacement, and other."
            )
        ),
        HumanMessage(
            content=json.dumps(
                {
                    "customer_email": message.customer_email,
                    "subject": message.subject,
                    "body": message.body,
                },
                ensure_ascii=False,
            )
        ),
    ]


def classify_case_node(llm: BaseChatModel):
    structured_llm = llm.with_structured_output(CaseClassification)

    def classify_case(state: GraphState) -> GraphState:
        message = IncomingMessage.model_validate(state["message"])
        classification = structured_llm.invoke(_json_messages(message))
        if not isinstance(classification, CaseClassification):
            classification = CaseClassification.model_validate(classification)
        events = list(state.get("audit_events", []))
        events.append(
            _event(
                "case_classified",
                intent=classification.intent,
                urgency=classification.urgency,
                confidence=classification.confidence,
            )
        )
        return {
            "classification": classification,
            "status": "received",
            "audit_events": events,
        }

    return classify_case


def lookup_records_node(state: GraphState) -> GraphState:
    message = IncomingMessage.model_validate(state["message"])
    classification = state.get("classification")
    email = (classification.customer_email if classification else None) or message.customer_email
    order_id = classification.order_id if classification else None
    customer = lookup_customer(email)
    order = lookup_order(order_id, email)
    events = list(state.get("audit_events", []))
    events.append(
        _event(
            "records_looked_up",
            customer_found=bool(customer),
            order_found=bool(order),
            order_id=order_id,
        )
    )
    return {"customer": customer, "order": order, "audit_events": events}


def retrieve_context_node(state: GraphState) -> GraphState:
    classification = state.get("classification")
    topic = classification.intent if classification else None
    context = retrieve_policies(topic)
    events = list(state.get("audit_events", []))
    events.append(_event("policy_context_retrieved", policy_count=len(context)))
    return {"retrieved_context": context, "audit_events": events}


def validate_risk_node(state: GraphState) -> GraphState:
    classification = state.get("classification")
    order = state.get("order")
    customer = state.get("customer")
    flags = list(classification.risk_flags if classification else [])
    message_text = str(state["message"].get("body", "")).lower()
    for keyword in ("chargeback", "fraud", "lawsuit", "legal action"):
        if keyword in message_text:
            flags.append(f"keyword_{keyword.replace(' ', '_')}")
    if classification and classification.confidence < 0.75:
        flags.append("low_classification_confidence")
    if not customer:
        flags.append("customer_identity_unverified")
    if classification and classification.intent in {
        "damaged_item",
        "refund_or_replacement",
    } and not order:
        flags.append("order_not_verified")
    events = list(state.get("audit_events", []))
    events.append(_event("risk_validated", risk_flags=sorted(set(flags))))
    return {"risk_flags": sorted(set(flags)), "audit_events": events}


def plan_resolution_node(llm: BaseChatModel):
    structured_llm = llm.with_structured_output(ResolutionPlan)

    def plan_resolution(state: GraphState) -> GraphState:
        classification = state.get("classification")
        message = IncomingMessage.model_validate(state["message"])
        evidence = {
            "classification": classification.model_dump() if classification else None,
            "customer": state.get("customer"),
            "order": state.get("order"),
            "policies": state.get("retrieved_context", []),
            "risk_flags": state.get("risk_flags", []),
        }
        prompt = (
            "Create a safe resolution plan for this support case. Use only the supplied "
            "evidence. If evidence is missing, request more information or escalate. "
            "Refund and replacement actions are approval-gated. Write a concise, polite "
            "customer reply.\n\n"
            f"Customer message: {message.body}\n"
            f"Evidence JSON: {json.dumps(evidence, ensure_ascii=False)}"
        )
        plan = structured_llm.invoke([HumanMessage(content=prompt)])
        if not isinstance(plan, ResolutionPlan):
            plan = ResolutionPlan.model_validate(plan)
        action_allowed, action_reasons = validate_action(
            plan.action,
            state.get("order"),
            state.get("customer"),
            state.get("risk_flags", []),
        )
        risk_flags = sorted(set(state.get("risk_flags", []) + action_reasons))
        approval_required = bool(
            risk_flags
            or plan.approval_required
            or plan.action in {"refund", "replacement", "escalate"}
            or not action_allowed
        )
        events = list(state.get("audit_events", []))
        events.append(
            _event(
                "resolution_planned",
                action=plan.action,
                approval_required=approval_required,
                action_allowed=action_allowed,
            )
        )
        return {
            "plan": plan,
            "risk_flags": risk_flags,
            "approval_required": approval_required,
            "audit_events": events,
        }

    return plan_resolution


def approval_gate_node(state: GraphState) -> GraphState:
    """Pause logically until the caller explicitly supplies approved=True."""

    approval_required = state.get("approval_required", False)
    approved = state.get("approved") is True
    events = list(state.get("audit_events", []))
    if approval_required and not approved:
        events.append(_event("approval_required", status="waiting_for_human"))
        return {"status": "ready_for_approval", "audit_events": events}
    events.append(_event("approval_granted" if approval_required else "approval_not_needed"))
    return {"status": "action_pending", "audit_events": events}


def route_after_gate(state: GraphState) -> str:
    if state.get("status") == "ready_for_approval":
        return "wait"
    if state.get("plan") and state["plan"].action not in {"answer_only", "request_more_information"}:
        return "execute"
    return "resolve"


def execute_action_node(state: GraphState) -> GraphState:
    plan = state.get("plan")
    if not plan:
        return {"execution_result": {"ok": False, "error": "missing_resolution_plan"}}
    result = execute_approved_action(
        plan.action,
        state.get("order"),
        state.get("customer"),
        approved=state.get("approved") is True,
    )
    events = list(state.get("audit_events", []))
    events.append(_event("action_executed", result=result))
    return {"execution_result": result, "audit_events": events}


def finalize_node(state: GraphState) -> GraphState:
    plan = state.get("plan")
    result = state.get("execution_result")
    if plan and plan.action == "escalate":
        status = "escalated"
    elif result is not None and not result.get("ok", False):
        status = "escalated"
    else:
        status = "resolved"
    events = list(state.get("audit_events", []))
    events.append(_event("case_finalized", status=status))
    return {"status": status, "audit_events": events}


def build_graph(llm: BaseChatModel | None = None):
    """Build and compile the support-resolution graph.

    Pass an injected model in tests. In production, omitting it creates a
    ChatOpenAI client configured for AgentRouter and ``gpt-5.5``.
    """

    live_llm = llm or create_agentrouter_llm()
    graph = StateGraph(GraphState)
    graph.add_node("classify_case", classify_case_node(live_llm))
    graph.add_node("lookup_records", lookup_records_node)
    graph.add_node("retrieve_context", retrieve_context_node)
    graph.add_node("validate_risk", validate_risk_node)
    graph.add_node("plan_resolution", plan_resolution_node(live_llm))
    graph.add_node("approval_gate", approval_gate_node)
    graph.add_node("execute_action", execute_action_node)
    graph.add_node("finalize", finalize_node)
    graph.add_edge(START, "classify_case")
    graph.add_edge("classify_case", "lookup_records")
    graph.add_edge("lookup_records", "retrieve_context")
    graph.add_edge("retrieve_context", "validate_risk")
    graph.add_edge("validate_risk", "plan_resolution")
    graph.add_edge("plan_resolution", "approval_gate")
    graph.add_conditional_edges(
        "approval_gate",
        route_after_gate,
        {"wait": END, "execute": "execute_action", "resolve": "finalize"},
    )
    graph.add_edge("execute_action", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()


def run_case(
    message: IncomingMessage,
    *,
    llm: BaseChatModel | None = None,
    approved: bool | None = None,
    prior_state: GraphState | None = None,
) -> GraphState:
    """Run a new case or resume a previously gated case."""

    if prior_state is not None:
        state = dict(prior_state)
        state["approved"] = approved
        if state.get("status") == "ready_for_approval":
            gated_state = {**state, **approval_gate_node(state)}
            if route_after_gate(gated_state) == "execute":
                executed_state = {**gated_state, **execute_action_node(gated_state)}
                return {**executed_state, **finalize_node(executed_state)}
            return gated_state
        return build_graph(llm).invoke(state)
    compiled = build_graph(llm)
    initial: GraphState = {
        "message": message.model_dump(),
        "approved": approved,
        "audit_events": [_event("case_received", conversation_id=message.conversation_id)],
    }
    return compiled.invoke(initial)


def approval_request(state: GraphState) -> dict[str, Any] | None:
    """Convert a gated graph state into a UI-friendly approval payload."""

    plan = state.get("plan")
    if state.get("status") != "ready_for_approval" or not plan:
        return None
    return {
        "conversation_id": state["message"].get("conversation_id"),
        "action": plan.action,
        "rationale": plan.rationale,
        "evidence": {
            "customer": state.get("customer"),
            "order": state.get("order"),
            "policies": state.get("retrieved_context", []),
        },
        "draft_reply": plan.customer_reply,
        "risk_flags": state.get("risk_flags", []),
    }
