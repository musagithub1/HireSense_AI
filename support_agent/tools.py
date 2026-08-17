"""Demo tools used by the support agent.

Replace these functions with Shopify/help-desk adapters in production. The MVP
keeps side effects behind explicit policy checks and an approval flag.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

DEMO_CUSTOMERS: dict[str, dict[str, Any]] = {
    "alex@example.com": {"customer_id": "cus_1001", "name": "Alex Morgan"},
    "sam@example.com": {"customer_id": "cus_1002", "name": "Sam Lee"},
}

DEMO_ORDERS: dict[str, dict[str, Any]] = {
    "ORD-1001": {
        "order_id": "ORD-1001",
        "customer_email": "alex@example.com",
        "status": "in_transit",
        "carrier": "DHL",
        "tracking_number": "DHL123456",
        "total": 89.0,
        "delivered_at": None,
        "items": [{"name": "Canvas Backpack", "quantity": 1}],
    },
    "ORD-1002": {
        "order_id": "ORD-1002",
        "customer_email": "sam@example.com",
        "status": "delivered",
        "carrier": "UPS",
        "tracking_number": "UPS789012",
        "total": 42.0,
        "delivered_at": "2026-08-12",
        "items": [{"name": "Travel Mug", "quantity": 1}],
    },
}

POLICIES = [
    {
        "policy_id": "returns-v1",
        "topic": "return_policy",
        "text": "Unused items may be returned within 30 days of delivery. The customer must provide the order number.",
    },
    {
        "policy_id": "damaged-v1",
        "topic": "damaged_item",
        "text": "For damaged items, request photos and the order number before offering a replacement or refund.",
    },
    {
        "policy_id": "refunds-v1",
        "topic": "refund_or_replacement",
        "text": "Refunds above 50.00 USD require human approval. Never refund an order without matching the customer identity and order record.",
    },
    {
        "policy_id": "delivery-v1",
        "topic": "delivery_delay",
        "text": "For an in-transit package, provide the carrier and tracking number. Escalate if the customer reports a missing package after the carrier marks it delivered.",
    },
]


def lookup_customer(email: str | None) -> dict[str, Any] | None:
    """Return a copy of a demo customer record."""

    if not email:
        return None
    customer = DEMO_CUSTOMERS.get(email.strip().lower())
    return deepcopy(customer) if customer else None


def lookup_order(order_id: str | None, customer_email: str | None) -> dict[str, Any] | None:
    """Return an order only when its customer identity matches."""

    if not order_id:
        return None
    order = DEMO_ORDERS.get(order_id.strip().upper())
    if not order:
        return None
    if customer_email and order["customer_email"] != customer_email.strip().lower():
        return None
    return deepcopy(order)


def retrieve_policies(topic: str | None) -> list[dict[str, Any]]:
    """Return policy records relevant to the classified intent."""

    if not topic:
        return []
    matches = [policy for policy in POLICIES if policy["topic"] == topic]
    return deepcopy(matches)


def validate_action(
    action: str,
    order: dict[str, Any] | None,
    customer: dict[str, Any] | None,
    risk_flags: list[str],
    *,
    approved: bool = False,
) -> tuple[bool, list[str]]:
    """Enforce deterministic authorization rules before any side effect."""

    reasons = list(risk_flags)
    if action in {"refund", "replacement"} and not customer:
        reasons.append("customer_identity_unverified")
    if action in {"refund", "replacement"} and not order:
        reasons.append("order_not_verified")
    if (
        action == "refund"
        and order
        and float(order.get("total", 0)) > 50
        and not approved
    ):
        reasons.append("refund_above_auto_approval_threshold")
    return not reasons, sorted(set(reasons))


def execute_approved_action(
    action: str,
    order: dict[str, Any] | None,
    customer: dict[str, Any] | None,
    approved: bool,
) -> dict[str, Any]:
    """Simulate a side effect only after explicit approval and identity checks."""

    if not approved:
        return {"ok": False, "error": "human_approval_required", "action": action}
    allowed, reasons = validate_action(
        action,
        order,
        customer,
        [],
        approved=approved,
    )
    if not allowed:
        return {"ok": False, "error": "action_blocked", "reasons": reasons}
    return {
        "ok": True,
        "action": action,
        "order_id": order["order_id"] if order else None,
        "customer_id": customer["customer_id"] if customer else None,
        "mode": "demo_no_external_side_effect",
    }
