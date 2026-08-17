"""Offline tests for the LangGraph e-commerce support agent."""

from __future__ import annotations

from typing import Any

from support_agent import (
    IncomingMessage,
    approval_request,
    create_agentrouter_llm,
    run_case,
)


class FakeStructuredRunnable:
    def __init__(self, responses: list[dict[str, Any]]):
        self.responses = responses

    def invoke(self, _messages: Any) -> dict[str, Any]:
        return self.responses.pop(0)


class FakeStructuredModel:
    def __init__(self, responses: list[dict[str, Any]]):
        self.responses = responses

    def with_structured_output(self, _schema: Any) -> FakeStructuredRunnable:
        return FakeStructuredRunnable(self.responses)


def test_answer_only_case_resolves_without_side_effect() -> None:
    llm = FakeStructuredModel(
        [
            {
                "intent": "order_status",
                "urgency": "normal",
                "confidence": 0.98,
                "customer_email": "alex@example.com",
                "order_id": "ORD-1001",
                "risk_flags": [],
            },
            {
                "action": "answer_only",
                "amount": None,
                "rationale": "The order has a valid in-transit tracking record.",
                "customer_reply": "Your order is in transit with DHL. Tracking: DHL123456.",
                "confidence": 0.96,
                "approval_required": False,
            },
        ]
    )
    state = run_case(
        IncomingMessage(
            conversation_id="case-1",
            customer_email="alex@example.com",
            body="Where is order ORD-1001?",
        ),
        llm=llm,
    )
    assert state["status"] == "resolved"
    assert state.get("execution_result") is None
    assert state["order"]["order_id"] == "ORD-1001"
    assert any(event["event"] == "case_finalized" for event in state["audit_events"])


def test_refund_case_stops_for_approval_then_resumes_safely() -> None:
    llm = FakeStructuredModel(
        [
            {
                "intent": "refund_or_replacement",
                "urgency": "normal",
                "confidence": 0.97,
                "customer_email": "alex@example.com",
                "order_id": "ORD-1001",
                "risk_flags": [],
            },
            {
                "action": "refund",
                "amount": 89.0,
                "rationale": "The customer requests a refund for the verified order.",
                "customer_reply": "We can process the refund after approval.",
                "confidence": 0.94,
                "approval_required": True,
            },
        ]
    )
    message = IncomingMessage(
        conversation_id="case-2",
        customer_email="alex@example.com",
        body="Please refund order ORD-1001.",
    )
    waiting = run_case(message, llm=llm)
    assert waiting["status"] == "ready_for_approval"
    request = approval_request(waiting)
    assert request is not None
    assert request["action"] == "refund"
    assert "refund_above_auto_approval_threshold" in waiting["risk_flags"]

    completed = run_case(message, prior_state=waiting, approved=True)
    assert completed["status"] == "resolved"
    assert completed["execution_result"]["ok"] is True
    assert completed["execution_result"]["mode"] == "demo_no_external_side_effect"


def test_agentrouter_factory_uses_gpt_5_5_and_official_base_url(monkeypatch) -> None:
    monkeypatch.setenv("AGENTROUTER_API_KEY", "test-key")
    monkeypatch.delenv("AGENTROUTER_MODEL", raising=False)
    monkeypatch.delenv("AGENTROUTER_BASE_URL", raising=False)
    llm = create_agentrouter_llm()
    assert llm.model_name == "gpt-5.5"
    assert str(llm.openai_api_base).rstrip("/") == "https://agentrouter.org/v1"
