"""Typed schemas for the e-commerce support-resolution agent."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Intent = Literal[
    "order_status",
    "delivery_delay",
    "return_policy",
    "damaged_item",
    "refund_or_replacement",
    "other",
]
Urgency = Literal["low", "normal", "high"]
CaseStatus = Literal[
    "received",
    "needs_review",
    "ready_for_approval",
    "action_pending",
    "resolved",
    "escalated",
]


class IncomingMessage(BaseModel):
    """A normalized support message entering the graph."""

    conversation_id: str
    channel: str = "demo"
    customer_email: str | None = None
    subject: str = ""
    body: str


class CaseClassification(BaseModel):
    """Structured LLM classification output."""

    intent: Intent
    urgency: Urgency
    confidence: float = Field(ge=0, le=1)
    customer_email: str | None = None
    order_id: str | None = None
    risk_flags: list[str] = Field(default_factory=list)
    reasoning: str = ""


class ResolutionPlan(BaseModel):
    """Structured resolution proposal produced after evidence retrieval."""

    action: Literal[
        "answer_only",
        "request_more_information",
        "refund",
        "replacement",
        "escalate",
    ]
    amount: float | None = Field(default=None, ge=0)
    rationale: str
    customer_reply: str
    confidence: float = Field(ge=0, le=1)
    approval_required: bool = True


class ApprovalRequest(BaseModel):
    """Human-review payload for an action or risky case."""

    conversation_id: str
    action: str
    rationale: str
    evidence: dict[str, Any]
    draft_reply: str
    risk_flags: list[str] = Field(default_factory=list)


class SupportState(BaseModel):
    """Serializable graph state used by the public convenience API."""

    message: IncomingMessage
    intent: Intent | None = None
    urgency: Urgency | None = None
    customer: dict[str, Any] | None = None
    order: dict[str, Any] | None = None
    retrieved_context: list[dict[str, Any]] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    plan: ResolutionPlan | None = None
    approval_required: bool = False
    approved: bool | None = None
    execution_result: dict[str, Any] | None = None
    status: CaseStatus = "received"
    audit_events: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None
