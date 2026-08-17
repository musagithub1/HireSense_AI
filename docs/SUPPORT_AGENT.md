# E-commerce Support-Resolution Agent

This repository now includes a LangGraph MVP for an e-commerce customer-support resolution workflow. The agent classifies a support message, looks up a customer and order in a deterministic demo store, retrieves the relevant policy, validates risk, proposes a resolution, and stops at an approval gate before a refund, replacement, or escalation action.

## AgentRouter configuration

AgentRouter’s official OpenAI-compatible guide specifies the following configuration:

| Variable | Value |
|---|---|
| `AGENTROUTER_API_KEY` | Your private AgentRouter API key |
| `AGENTROUTER_BASE_URL` | `https://agentrouter.org/v1` |
| `AGENTROUTER_MODEL` | `gpt-5.5` |

The project intentionally uses `gpt-5.5`, not `gpt-5.6`, because the official AgentRouter guide currently lists `gpt-5.5` as an available OpenAI-compatible model identifier. Keep the model configurable so it can be changed when AgentRouter publishes another supported identifier.

Do not commit the API key. Add it to a local `.env` file or to the deployment environment:

```dotenv
AGENTROUTER_API_KEY=replace_with_your_agentrouter_key
AGENTROUTER_BASE_URL=https://agentrouter.org/v1
AGENTROUTER_MODEL=gpt-5.5
```

## Install and run

Install the project dependencies, including LangGraph:

```bash
pip install -r requirements.txt
```

The public API is available from `support_agent`:

```python
from support_agent import IncomingMessage, approval_request, run_case

message = IncomingMessage(
    conversation_id="demo-001",
    customer_email="alex@example.com",
    subject="Where is my order?",
    body="Can you tell me where order ORD-1001 is?",
)

state = run_case(message)
print(state["status"])
print(approval_request(state))
```

A real AgentRouter call requires `AGENTROUTER_API_KEY`. Tests should inject a fake LangChain chat model instead of making network requests. For a case that reaches the approval gate, persist the returned state in the application database and resume it only after a human decision:

```python
approved_state = run_case(
    message,
    prior_state=state,
    approved=True,
)
print(approved_state["status"])
```

## Graph behavior

```text
classify_case -> lookup_records -> retrieve_context -> validate_risk
     -> plan_resolution -> approval_gate
          -> wait for human approval
          -> execute_action -> finalize
          -> finalize for answer-only or request-more-information cases
```

The action tools are demo adapters. Replace `lookup_customer`, `lookup_order`, and `execute_approved_action` in `support_agent/tools.py` with Shopify, help-desk, carrier, and payment-provider adapters. Preserve the deterministic checks: identity matching, order verification, policy thresholds, idempotency, and audit logging.

## Safety boundary

The MVP does not permit unverified refunds or replacements. It flags missing customer identity, missing order records, low classification confidence, chargeback language, fraud language, legal threats, and refunds above the configured threshold. All action proposals remain auditable through `audit_events`. The demo executor explicitly reports `demo_no_external_side_effect` and does not modify a real store.

## Official AgentRouter source

AgentRouter OpenAI-compatible setup: <https://agentrouter.org/docs/cline.html>
