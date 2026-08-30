# Recovery Firewall
### AI Decision Infrastructure for Safe Revenue Recovery

**Hackathon Track:** Track 03 — AI Revenue Recovery  
**Product Type:** AI-powered financial decision and execution system  
**Primary Integration:** Razorpay Test Mode APIs + Webhooks  
**Frontend:** Next.js + TypeScript  
**Backend:** FastAPI + Python  
**Database:** PostgreSQL / Supabase  
**AI:** LLM-based investigation and recovery planning  
**Deployment:** Vercel + production backend deployment  
**Environment:** Razorpay Test Mode

---

# 1. Executive Summary

Recovery Firewall is an AI-powered decision layer that sits between a merchant's revenue-recovery workflow and payment execution.

The system addresses a subtle failure mode in automated revenue recovery:

> A payment that appears failed may not actually be financially resolved.

An automated recovery system that immediately creates another collection path can therefore cause premature intervention, duplicate collection, unnecessary customer communication, or conflicting financial actions.

Recovery Firewall reconstructs the financial state surrounding an obligation, evaluates the proposed recovery action, determines whether intervention is safe, and either:

- **ALLOW** the action,
- **WAIT** and reassess later,
- **BLOCK** the action, or
- **ESCALATE** to a human.

When an action is allowed, the system executes the real action against Razorpay Test Mode APIs and subsequently verifies the result through actual Razorpay events.

The central product principle is:

> **Do not recover money merely because a payment looks failed. Determine whether the money is actually lost first.**

---

# 2. Problem

## 2.1 The obvious problem

Merchants lose revenue when customers fail to complete payments.

Traditional recovery systems respond with:

```text
payment.failed
        ↓
retry
        ↓
payment link
        ↓
reminder
```

This assumes:

```text
payment.failed = money lost
```

That assumption is unsafe.

Razorpay's payment lifecycle is asynchronous, and its documentation explicitly describes scenarios where a payment can initially generate a failure event and subsequently move into a successful state through late authorization or customer retries.

Therefore, a recovery system needs to reason about the **trajectory of a financial obligation**, not merely its latest event.

---

# 3. The Deeper Problem

The merchant does not ultimately care about a single payment entity.

The merchant cares about:

> **Has the customer's financial obligation been satisfied?**

For example:

```text
Customer owes: ₹5,000

Payment A:
₹5,000
FAILED

Current assumption:
₹5,000 outstanding
```

A naive recovery agent might create another ₹5,000 Payment Link.

But if Payment A subsequently succeeds:

```text
Payment A → ₹5,000 CAPTURED
Payment B → ₹5,000 CAPTURED
```

the merchant may have collected:

```text
₹10,000
```

against a:

```text
₹5,000
```

obligation.

The system has transformed a recovery opportunity into a financial integrity problem.

---

# 4. Product Thesis

## Existing recovery automation asks:

> "What should I do after this payment failed?"

## Recovery Firewall asks:

> "Is there actually an unpaid obligation, and is this action safe given everything that has happened?"

This introduces a new abstraction:

# Financial Obligation

A financial obligation represents the amount the customer is expected to pay for a commercial transaction or recurring invoice.

The obligation can have multiple associated:

- payment attempts,
- payment IDs,
- Payment Links,
- invoices,
- recovery actions,
- refunds,
- state transitions.

The system reasons about the **obligation**, rather than treating every payment attempt as independent revenue.

---

# 5. Goals

## Primary Goals

1. Detect potentially recoverable revenue.
2. Reconstruct the current financial state of an obligation.
3. Determine whether a proposed recovery action is safe.
4. Prevent duplicate or premature collection.
5. Execute approved recovery actions through real Razorpay APIs.
6. Verify the result using real Razorpay webhook events.
7. Maintain a complete audit trail.
8. Provide evidence for every AI-assisted decision.
9. Enforce deterministic financial safety policies.
10. Measure actual recovery outcomes in Razorpay Test Mode.

---

# 6. Non-Goals

Recovery Firewall will NOT attempt to become:

- a generic payment gateway,
- a replacement for Razorpay,
- a generic CRM,
- a generic chatbot,
- a generic fraud detector,
- a payment analytics dashboard,
- an unrestricted autonomous financial agent,
- a system capable of moving real money.

The system will also not claim that test-mode revenue is real merchant revenue.

All monetary results will be explicitly identified as **Razorpay Test Mode results**.

---

# 7. Core Product Loop

The complete system follows:

```text
Razorpay Event
      ↓
Verify
      ↓
Persist
      ↓
Reconstruct Financial State
      ↓
Identify Obligation
      ↓
Investigate
      ↓
AI Recovery Recommendation
      ↓
Deterministic Firewall
      ↓
ALLOW / WAIT / BLOCK / ESCALATE
      ↓
Execute if ALLOWED
      ↓
Observe Razorpay Event
      ↓
Reconstruct State
      ↓
Verify Outcome
      ↓
Close / Continue / Escalate
```

---

# 8. Product Architecture

```text
                         RAZORPAY
                     TEST MODE APIs
                           │
                  ┌────────┴────────┐
                  │                 │
               REST API          WEBHOOKS
                  │                 │
                  └────────┬────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ Webhook Ingestion   │
                │                     │
                │ Signature Verify    │
                │ Idempotency         │
                │ Raw Event Storage   │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ Financial State     │
                │ Engine              │
                │                     │
                │ Payments            │
                │ Orders              │
                │ Obligations         │
                │ Payment Links       │
                │ Invoices            │
                │ Recovery Actions    │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ AI State            │
                │ Investigator        │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ AI Recovery         │
                │ Planner             │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ Recovery Firewall   │
                │                     │
                │ Obligation checks   │
                │ Policy checks       │
                │ Concurrency checks  │
                │ Idempotency checks  │
                │ Financial limits    │
                └──────────┬──────────┘
                           │
                 ┌─────────┼─────────┐
                 │         │         │
                 ▼         ▼         ▼
               ALLOW      WAIT      BLOCK
                 │         │
                 ▼         ▼
           Razorpay API  Re-evaluate
                 │
                 ▼
              WEBHOOK
                 │
                 └───────────────► State Engine
```

---

# 9. Razorpay Integration

The implementation must use Razorpay Test Mode rather than simulated payment APIs.

## 9.1 Required Razorpay capabilities

The MVP will use only capabilities that are actually available through Razorpay's documented APIs and Test Mode.

### Payments

Used for:

- retrieving payment information,
- observing payment state,
- associating payment attempts with obligations.

### Orders

Used for:

- establishing the commercial payment context,
- retrieving payments associated with an order.

### Payment Links

Used for actual recovery execution.

Required operations:

- create Payment Link,
- retrieve Payment Link,
- inspect Payment Link state,
- cancel Payment Link where permitted,
- send/notify where appropriate.

### Webhooks

Used as the event stream for:

- payment state changes,
- Payment Link state changes,
- subscription/invoice events where applicable.

### Subscriptions / Invoices

Not required for the narrowest MVP but supported as a second recovery scenario if the API surface is verified during implementation.

Razorpay documents that halted subscriptions can retain outstanding invoices and that previous unpaid charges are not automatically retried simply because a subscription later becomes active. This creates a genuine second revenue-recovery scenario.

---

# 10. Event Ingestion

All Razorpay webhook requests enter through:

```text
POST /webhooks/razorpay
```

## Processing sequence

```text
Webhook received
      ↓
Validate signature
      ↓
Extract event ID/entity ID
      ↓
Check duplicate event
      ↓
Persist raw payload
      ↓
Return successful response
      ↓
Process asynchronously
```

The raw event must be retained.

No state transition may occur without an originating event or verified API observation.

---

# 11. Webhook Idempotency

Webhook processing must be idempotent.

The system must not process the same event twice.

Example:

```text
event_123
payment.captured
```

received twice:

```text
First:
PROCESS

Second:
ALREADY_PROCESSED
```

The second delivery must not:

- create another recovery action,
- update money totals twice,
- create duplicate records,
- trigger another customer action.

---

# 12. Financial Obligation Model

The system introduces:

```text
financial_obligation
```

Example:

```text
Obligation OBL_123

Expected amount:
₹5,000

Currency:
INR

Satisfied:
₹0

In-flight:
₹5,000

Outstanding:
₹5,000

Status:
UNRESOLVED
```

The obligation aggregates associated financial entities.

```text
OBLIGATION
│
├── ORDER
│
├── PAYMENT ATTEMPT #1
│
├── PAYMENT ATTEMPT #2
│
├── PAYMENT LINK
│
├── RECOVERY ACTIONS
│
└── REFUND EVENTS
```

---

# 13. Obligation State

The system will maintain deterministic states:

```text
UNRESOLVED
PARTIALLY_SATISFIED
SATISFIED
OVER_COLLECTED
AMBIGUOUS
EXPIRED
ESCALATED
```

The state is derived from persisted facts.

The LLM cannot directly modify the financial state.

---

# 14. Amount Accounting

The system must distinguish:

```text
obligation_amount
satisfied_amount
in_flight_amount
outstanding_amount
```

Conceptually:

```text
outstanding =
obligation_amount
-
satisfied_amount
-
valid_in_flight_amount
```

The implementation must additionally account for duplicate relationships and invalidated/cancelled actions rather than blindly summing transactions.

The LLM must never be the source of truth for these calculations.

---

# 15. AI Component #1 — State Investigator

The State Investigator receives structured evidence.

Example:

```json
{
  "obligation_amount": 5000,
  "payments": [
    {
      "id": "pay_x",
      "amount": 5000,
      "status": "failed",
      "method": "upi"
    }
  ],
  "recovery_actions": [],
  "payment_links": [],
  "timeline": [...]
}
```

The model produces a structured investigation:

```json
{
  "financial_state": "AMBIGUOUS",
  "recovery_needed": false,
  "duplicate_exposure": "HIGH",
  "confidence": 0.93,
  "recommended_wait_seconds": 90,
  "evidence": [
    "Original payment failed recently",
    "No existing recovery path",
    "Payment trajectory is not yet conclusively resolved"
  ]
}
```

The AI is responsible for:

- pattern recognition,
- contextual interpretation,
- explanation,
- hypothesis generation,
- prioritization.

The AI is NOT responsible for:

- calculating balances,
- authorizing money movement,
- bypassing policies,
- modifying financial records directly.

---

# 16. AI Component #2 — Recovery Planner

The Recovery Planner determines the best possible intervention.

Supported actions:

```text
NO_ACTION
WAIT
RETRY_WHEN_SUPPORTED
CREATE_PAYMENT_LINK
NOTIFY
ESCALATE
```

The exact action set will be limited to capabilities that are genuinely executable through the chosen integration.

The planner must output structured data.

Example:

```json
{
  "action": "CREATE_PAYMENT_LINK",
  "amount": 5000,
  "reason": "Original payment appears conclusively unresolved",
  "confidence": 0.89,
  "expected_outcome": "Recover outstanding obligation"
}
```

---

# 17. AI Must Never Execute Directly

This is a fundamental architectural constraint.

Incorrect:

```text
LLM
 ↓
Razorpay API
```

Correct:

```text
LLM
 ↓
Structured Recommendation
 ↓
Firewall
 ↓
Policy Validation
 ↓
Razorpay API
```

The LLM is advisory.

The Firewall is authoritative.

---

# 18. Recovery Firewall

The Firewall is deterministic.

It evaluates every proposed financial action.

Input:

```text
proposed action
+
obligation state
+
payment state
+
existing recovery actions
+
merchant policy
+
concurrency state
```

Output:

```text
ALLOW
WAIT
BLOCK
ESCALATE
```

---

# 19. Mandatory Firewall Rules

## Rule 1 — Obligation Already Satisfied

If:

```text
outstanding_amount <= 0
```

then:

```text
BLOCK
```

Reason:

> Financial obligation already satisfied.

---

## Rule 2 — Existing Active Recovery Path

If an equivalent Payment Link or recovery mechanism is already active:

```text
BLOCK
```

Reason:

> Existing collection path detected.

---

## Rule 3 — Ambiguous Original Payment

If a payment remains within a defined unresolved state window:

```text
WAIT
```

The system must reassess rather than immediately creating another collection mechanism.

---

## Rule 4 — Concurrent Action

If another action is currently executing:

```text
WAIT
```

or:

```text
BLOCK
```

depending on the action.

---

## Rule 5 — Duplicate Action

Every consequential action receives an idempotency key.

The same logical recovery operation cannot execute twice.

---

## Rule 6 — Financial Limit

Merchant-defined autonomous recovery limits apply.

Example:

```text
max_autonomous_recovery_amount = ₹50,000
```

Above the limit:

```text
ESCALATE
```

---

## Rule 7 — Low Confidence

If AI confidence falls below the configured threshold:

```text
ESCALATE
```

---

## Rule 8 — State Uncertainty

If the financial state cannot be reconstructed reliably:

```text
BLOCK
```

The system must prefer:

> "I don't know"

over an unsafe financial action.

---

# 20. Recovery Action Lifecycle

Every action follows:

```text
PROPOSED
   ↓
VALIDATING
   ↓
ALLOWED
   ↓
EXECUTING
   ↓
AWAITING_CONFIRMATION
   ↓
CONFIRMED
```

Failure path:

```text
EXECUTING
   ↓
FAILED
   ↓
RETRY / ESCALATE
```

Safety path:

```text
PROPOSED
   ↓
BLOCKED
```

No action may jump directly from:

```text PROPOSED → EXECUTED
```

---

# 21. Example End-to-End Scenario A — Safe Recovery

Initial obligation:

```text
₹5,000
```

Payment:

```text
FAILED
```

Time since failure:

```text
47 minutes
```

No active Payment Link.

No other successful payment.

State Investigator:

```text
Recovery appears appropriate.
```

Recovery Planner:

```text
CREATE_PAYMENT_LINK
₹5,000
```

Firewall:

```text
ALLOW
```

Backend calls the actual Razorpay Payment Link API.

Razorpay returns the real Payment Link entity.

Customer completes the Test Mode payment.

Razorpay emits the corresponding webhook.

Webhook processor updates:

```text
satisfied_amount = ₹5,000
outstanding_amount = ₹0
```

Obligation becomes:

```text
SATISFIED
```

Recovery action becomes:

```text
CONFIRMED
```

Dashboard displays:

```text
₹5,000 recovered
```

This number must originate from actual persisted Razorpay test-mode events.

---

# 22. Example End-to-End Scenario B — Recovery Blocked

Initial obligation:

```text
₹5,000
```

Original payment:

```text
FAILED
```

Only a few seconds have passed.

Recovery Planner proposes:

```text
CREATE_PAYMENT_LINK
₹5,000
```

Firewall evaluates:

```text
Original payment unresolved
+
short elapsed time
+
duplicate exposure
```

Decision:

```text
WAIT
```

The system does NOT call Razorpay to create the Payment Link.

Later:

```text
payment.captured
```

arrives.

Financial obligation:

```text
SATISFIED
```

Pending recovery proposal:

```text
CANCELLED
```

Result:

```text
₹5,000 recovered naturally
₹5,000 duplicate collection prevented
```

The second figure represents the amount of an action that the Firewall prevented; it must be labelled as **prevented duplicate exposure**, not actual recovered revenue.

---

# 23. Example End-to-End Scenario C — Already Recovered

Customer obligation:

```text
₹5,000
```

Payment Link:

```text
PAID
₹5,000
```

An AI recovery proposal arrives:

```text
CREATE_PAYMENT_LINK
₹5,000
```

Firewall:

```text
BLOCK
```

Reason:

```text
Obligation satisfied.
```

No Razorpay API action occurs.

---

# 24. Failure Handling

Failure is a first-class product state.

Example:

```text
CREATE_PAYMENT_LINK
        ↓
Razorpay API failure
        ↓
ACTION FAILED
```

The system must:

1. Persist the failed action.
2. Preserve the original idempotency key.
3. Determine whether retry is safe.
4. Avoid blindly repeating financial operations.
5. Re-query/reconcile state where necessary.
6. Escalate when uncertainty remains.

UI:

```text
ACTION FAILED

Payment Link creation could not be confirmed.

No second collection attempt was made.

Status:
ESCALATED

Reason:
Financial action outcome is uncertain.
```

---

# 25. Audit Trail

Every consequential decision must be traceable.

Example:

```text
Recovery Case #REC_1024

Obligation:
OBL_8392

Amount:
₹5,000

Trigger:
payment.failed

AI Investigation:
AMBIGUOUS

AI Confidence:
0.93

Proposed Action:
CREATE_PAYMENT_LINK

Firewall Decision:
WAIT

Rules Triggered:
- unresolved payment
- duplicate exposure

Reassessment:
90 seconds

Subsequent Event:
payment.captured

Final Outcome:
OBLIGATION SATISFIED

Recovery Action:
NOT EXECUTED
```

The audit trail must answer:

> What happened?

> What did the AI believe?

> What evidence did it use?

> What action did it propose?

> What policy evaluated it?

> Why was the action allowed or blocked?

> What actually happened afterward?

---

# 26. Database Schema

## `razorpay_events`

```text
id
event_id
event_type
entity_type
entity_id
payload
signature_verified
received_at
processed_at
processing_status
```

## `financial_obligations`

```text
id
external_reference
customer_reference
amount
currency
satisfied_amount
in_flight_amount
outstanding_amount
status
created_at
updated_at
```

## `payment_attempts`

```text
id
obligation_id
razorpay_payment_id
razorpay_order_id
amount
method
status
created_at
updated_at
```

## `payment_links`

```text
id
obligation_id
razorpay_payment_link_id
amount
amount_paid
status
created_at
updated_at
```

## `recovery_actions`

```text
id
obligation_id
action_type
amount
idempotency_key
status
requested_at
started_at
completed_at
failure_reason
```

## `agent_decisions`

```text
id
obligation_id
investigation
recommendation
confidence
evidence
model
created_at
```

## `policy_decisions`

```text
id
recovery_action_id
decision
rules_triggered
policy_version
created_at
```

## `state_transitions`

```text
id
entity_type
entity_id
previous_state
new_state
trigger_event_id
created_at
```

---

# 27. API Architecture

## Webhooks

```http
POST /webhooks/razorpay
```

## Obligations

```http
GET /api/obligations
GET /api/obligations/:id
```

## Recovery

```http
POST /api/recovery/:obligation_id/evaluate
POST /api/recovery/:obligation_id/execute
```

## Agent

```http
POST /api/agent/investigate/:obligation_id
POST /api/agent/plan/:obligation_id
```

## Audit

```http
GET /api/audit/:obligation_id
```

## Metrics

```http
GET /api/metrics
```

---

# 28. Frontend

The frontend is a merchant control center, not a chatbot.

## Dashboard

Primary metrics:

```text
Revenue at Risk
Outstanding Obligations
Recovered Revenue
Blocked Actions
Pending Decisions
Active Recoveries
```

All metrics derive from database state.

---

# 29. Recovery Queue

Example:

```text
RECOVERY QUEUE

┌──────────────────────────────────────────────┐
│ ₹5,000   PAYMENT AMBIGUOUS        WAIT      │
│ ₹12,000  RECOVERY ELIGIBLE        REVIEW    │
│ ₹3,200   OBLIGATION SATISFIED     BLOCKED   │
│ ₹45,000  HIGH VALUE               ESCALATE  │
└──────────────────────────────────────────────┘
```

---

# 30. Decision Detail

The most important interface.

```text
RECOVERY DECISION

₹5,000

Proposed Action
Create Payment Link

Firewall Decision

        WAIT

Why?

Original payment is unresolved.

Evidence:

• payment.failed received 14 seconds ago
• UPI payment
• no final capture/reversal
• no existing recovery path

Risk

Duplicate collection exposure: HIGH

Next reassessment

90 seconds
```

---

# 31. Live Event Timeline

Each obligation has a timeline:

```text
12:41:04
Payment created

12:41:22
Payment failed

12:41:23
Recovery agent evaluated

12:41:23
Firewall → WAIT

12:42:53
Reassessment triggered

12:43:01
Payment captured

12:43:02
Obligation marked SATISFIED
```

This makes the system's reasoning observable.

---

# 32. Financial Metrics

The dashboard will distinguish:

### Revenue at Risk

Outstanding eligible obligations.

### Recovered Revenue

Amount confirmed as successfully collected through an actual Razorpay Test Mode event following a recovery action.

### Natural Recovery

Amount that became satisfied without a recovery action.

### Prevented Duplicate Exposure

Amount of proposed/recoverable collection that the Firewall blocked because the obligation was already satisfied or otherwise unsafe.

### Recovery Rate

```text
recovered revenue
------------------
eligible revenue
```

### Intervention Rate

```text
recovery actions executed
-------------------------
eligible cases
```

### False Intervention Rate

Cases where an intervention was executed but subsequent evidence indicates that intervention was unnecessary or unsafe.

The methodology must be documented rather than inventing a target number.

---

# 33. Evaluation Framework

We will not claim:

> "Our AI is 94% accurate"

without a reproducible evaluation.

The evaluation set will contain real Razorpay Test Mode workflows and known expected outcomes.

Each scenario will have:

```text
initial state
event sequence
expected financial state
expected safe action
actual system decision
actual outcome
```

Example:

```text
Scenario:
Recent UPI failure

Expected:
WAIT

Actual:
WAIT

PASS
```

Another:

```text
Scenario:
Existing obligation already satisfied

Expected:
BLOCK

Actual:
BLOCK

PASS
```

Another:

```text
Scenario:
Conclusive unresolved payment

Expected:
ALLOW recovery

Actual:
ALLOW

PASS
```

---

# 34. Evaluation Metrics

## Decision Precision

Of all actions the system allowed:

```text
safe actions
------------
allowed actions
```

## Unsafe Action Rate

```text
unsafe actions
--------------
all consequential actions
```

Target:

```text
0 unsafe autonomous financial actions
```

This is a safety objective, not a claim that the system is perfect.

## Block Precision

How often a blocked action was genuinely unsafe or unnecessary.

## Recovery Success

Confirmed successful recoveries / executed recovery actions.

## Duplicate Prevention

Number and monetary value of duplicate-exposure scenarios correctly blocked.

## State Reconstruction Accuracy

Correctly reconstructed financial states / evaluated scenarios.

---

# 35. Security

Required:

- Razorpay secret keys stored only on backend.
- No secret keys exposed to frontend.
- Webhook signature verification.
- Authentication for merchant dashboard.
- Server-side authorization.
- Structured validation of LLM output.
- No direct LLM access to credentials.
- Idempotency keys for consequential operations.
- Audit logging.
- Rate limiting on sensitive endpoints.

---

# 36. AI Safety Boundary

The AI may:

```text
READ
ANALYZE
CLASSIFY
EXPLAIN
RECOMMEND
PRIORITIZE
```

The AI may NOT independently:

```text
MOVE MONEY
CHANGE FINANCIAL BALANCES
BYPASS POLICY
OVERRIDE BLOCKS
ALTER WEBHOOK HISTORY
EXECUTE UNVALIDATED API CALLS
```

The deterministic backend remains authoritative.

---

# 37. Merchant Policy Configuration

The merchant can configure:

```text
Maximum autonomous recovery amount
Maximum recovery attempts
Minimum waiting period
Maximum active recovery paths
High-value escalation threshold
AI confidence threshold
```

Example:

```text
Autonomous recovery limit:
₹10,000

High-value threshold:
₹25,000

Maximum recovery attempts:
2

Minimum reassessment delay:
90 seconds
```

These policies are versioned.

Every decision records:

```text
policy_version
```

so historical decisions remain explainable.

---

# 38. State Re-Evaluation

The system must not assume that an old AI decision remains valid.

If new Razorpay evidence arrives:

```text
payment.failed
```

followed later by:

```text
payment.captured
```

the system must invalidate stale recovery proposals.

General principle:

> **New financial evidence invalidates stale decisions.**

This is one of the central architectural properties of the system.

---

# 39. Concurrency Control

Before executing a financial action:

```text
1. Acquire obligation lock
2. Re-read current obligation state
3. Re-check active recovery actions
4. Re-check financial balance
5. Re-check idempotency key
6. Execute API action
7. Persist result
8. Release lock
```

The system must never rely exclusively on the state observed when the AI generated its recommendation.

---

# 40. Failure Scenario Requirements

At least one failure must be demonstrated live.

Preferred scenario:

```text
Recovery Action
       ↓
External API failure
       ↓
Uncertain result
       ↓
System refuses duplicate retry
       ↓
Reconciliation
       ↓
Escalation if necessary
```

The demo must show that the system behaves safely when an external operation fails.

---

# 41. MVP

The MVP must contain:

### Backend

- FastAPI
- PostgreSQL/Supabase
- Razorpay authentication
- webhook endpoint
- webhook signature verification
- idempotent event processing
- payment state persistence
- financial obligation model
- recovery action model
- policy engine
- AI investigator
- AI recovery planner
- Razorpay Payment Link creation
- Payment Link state tracking
- audit trail

### Frontend

- authentication
- merchant dashboard
- recovery queue
- obligation detail page
- decision detail page
- event timeline
- audit trail
- live metrics

### Demonstrable scenarios

1. Safe recovery.
2. Premature recovery blocked.
3. Already-satisfied obligation blocked.
4. External action failure handled safely.

---

# 42. Stretch Features

Only after the MVP is completely stable:

### Subscription Debt Recovery

Add:

```text
Subscription
 ↓
Historical invoices
 ↓
Outstanding obligations
 ↓
Recovery recommendation
```

### Partial Payment Intelligence

Support obligations such as:

```text
₹20,000 owed

₹5,000 paid
₹7,000 paid
₹8,000 outstanding
```

### Multi-Action Recovery

Allow:

```text
WAIT
 ↓
REASSESS
 ↓
PAYMENT LINK
 ↓
VERIFY
 ↓
ESCALATE
```

### Merchant Policy Editor

Visual configuration of:

- limits,
- thresholds,
- stopping rules.

### Natural-language Audit Explanation

Allow merchants to ask:

> "Why didn't you recover this payment?"

The system answers using the persisted evidence trail.

---

# 43. Explicit Anti-Mock Requirement

The following are prohibited in the final product:

### Prohibited

```text
fake payment success
fake webhook
fake Razorpay response
fake recovered revenue
hardcoded dashboard metrics
simulated API response presented as real
setTimeout-based payment simulation
fake customer transactions presented as production activity
```

### Allowed

```text
Razorpay Test Mode
synthetic scenario configuration
controlled test accounts
test-mode payments
test-mode webhook events
predefined evaluation cases
```

Any synthetic evaluation data must be explicitly labelled as such.

---

# 44. Demo Environment

The demo will use:

```text
Razorpay Test Mode
        ↓
Recovery Firewall Backend
        ↓
Supabase/Postgres
        ↓
Next.js Dashboard
```

The system will expose its webhook endpoint through a publicly reachable HTTPS deployment so Razorpay can deliver actual webhook events to the application.

---

# 45. Demo Narrative

## Scenario 1 — The obvious failure

Create a real Test Mode payment.

Cause an actual payment failure.

System receives:

```text
payment.failed
```

Recovery agent evaluates it.

Firewall determines:

```text
WAIT
```

Narrative:

> "The payment failed. But we haven't concluded that the money is lost."

---

## Scenario 2 — The payment resolves

Razorpay subsequently produces the successful state.

Dashboard updates:

```text
OBLIGATION SATISFIED
```

The recovery action is never executed.

Narrative:

> "The agent didn't recover the payment. It prevented us from unnecessarily recovering it."

---

## Scenario 3 — Genuine recovery

Use a genuinely unresolved test-mode obligation.

Agent:

```text
RECOVERY RECOMMENDED
```

Firewall:

```text
ALLOW
```

Backend creates an actual Razorpay Payment Link.

Customer completes payment.

Webhook arrives.

Dashboard:

```text
₹X RECOVERED
```

---

## Scenario 4 — Duplicate prevention

Attempt another recovery action against the same satisfied obligation.

Firewall:

```text
BLOCK
```

Reason:

```text
OBLIGATION ALREADY SATISFIED
```

---

## Scenario 5 — Failure

Cause an external API/action failure or otherwise reproduce an uncertain-action condition.

System:

```text
DO NOT BLINDLY RETRY
```

Then:

```text
RECONCILE
```

and:

```text
ESCALATE
```

if certainty cannot be established.

---

# 46. Five-Minute Pitch Structure

## 0:00–0:30 — Problem

> "Payment recovery has a hidden problem: a failed payment isn't necessarily lost revenue."

Show the duplicate-recovery scenario.

---

## 0:30–1:20 — Product

Introduce:

> **Recovery Firewall**

```text
Agent wants to collect
        ↓
Firewall asks:
"Is this actually safe?"
```

---

## 1:20–2:30 — Live Demo

Real Razorpay Test Mode:

```text
payment
→ failure
→ webhook
→ AI investigation
→ WAIT
→ eventual state
```

---

## 2:30–3:30 — Real Recovery

```text
unresolved obligation
→ ALLOW
→ Razorpay Payment Link
→ actual test payment
→ webhook
→ recovered
```

---

## 3:30–4:15 — Safety

Show:

```text
AI recommendation
        ↓
Firewall
        ↓
BLOCK
```

Then show audit trail.

---

## 4:15–5:00 — Metrics + Closing

Show:

```text
Revenue recovered
Natural recoveries
Unsafe actions blocked
Duplicate exposure prevented
Decision precision
```

Closing:

> **"Most recovery systems ask how to collect money. Recovery Firewall asks whether you should collect it at all."**

---

# 47. Success Criteria

The project is considered complete only if:

- Razorpay Test Mode is genuinely integrated.
- Webhooks are genuinely received.
- Webhook signatures are verified.
- Duplicate webhook delivery is safely handled.
- Financial state is persisted.
- AI produces structured decisions.
- AI cannot bypass deterministic policy.
- At least one recovery action executes through Razorpay.
- At least one recovery action is blocked.
- At least one recovery scenario is verified through a real webhook.
- Every financial decision has an audit trail.
- The dashboard derives metrics from persisted state.
- No financial result is hardcoded.
- At least one external/action failure is handled safely.
- The complete demo can be reproduced from a clean deployment.

---

# 48. Product Definition

## One sentence

> **Recovery Firewall is an AI-powered financial safety layer that determines whether a merchant's proposed revenue-recovery action is actually safe to execute, using payment trajectories, outstanding obligations, existing recovery paths, merchant policies, and real-time Razorpay events.**

## Core insight

> **A failed payment is an event. An unpaid obligation is a business state.**

## Core innovation

> **Recovery decisions are made against the financial obligation rather than the latest payment status.**

## Core safety principle

> **The AI recommends. The Firewall authorizes. Razorpay executes. Webhooks verify.**

## Core metric

> **Money recovered without creating unnecessary or duplicate collection.**

---

# 49. Implementation Principle

The implementation order is:

```text
Razorpay connectivity
        ↓
Webhook reliability
        ↓
Database/event model
        ↓
Financial obligation engine
        ↓
Deterministic Firewall
        ↓
Real Razorpay action execution
        ↓
AI investigator
        ↓
AI planner
        ↓
Frontend
        ↓
Evaluation
        ↓
Demo hardening
```

We will NOT begin by building the AI UI.

We will first prove that:

```text
Razorpay
   ↓
Webhook
   ↓
Backend
   ↓
Database
   ↓
State
```

works correctly.

Only then will AI be placed on top of it.