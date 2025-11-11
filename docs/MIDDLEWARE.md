# Middleware Architecture

Middleware components that provide cross-cutting concerns for the booking agent using LangChain v1's middleware pattern.

## Middleware Stack

```mermaid
graph LR
    USER[User Input] --> BR[BusinessRules]
    BR --> CS[ConversationSummary]
    CS --> PII[PII Masking]
    PII --> MODEL[LLM Call]
    MODEL --> UT[UsageTracking]
    UT --> HITL[HumanInLoop]
    HITL --> TOOL[Tool Execution]
    TOOL --> RESPONSE[Response]

    style BR fill:#ffcdd2
    style CS fill:#e3f2fd
    style PII fill:#fff3e0
    style UT fill:#f3e5f5
    style HITL fill:#ffcdd2
```

## Middleware Hooks

| Hook | When | Used By |
|------|------|---------|
| `before_model` | Before each LLM call | ConversationSummary, PII |
| `after_model` | After LLM response | UsageTracking, HumanInLoop |
| `before_tool_call` | Before tool execution | BusinessRules |

## Components

### BusinessRulesMiddleware
**Location**: `src/agent/middleware/business_rules.py`

Enforces booking policies and business rules BEFORE tool execution to prevent violations.

**Policies Enforced**:
- ✅ 2-hour minimum notice for same-day bookings
- ✅ Same-day booking cutoff (2:00 PM default)
- ✅ 24-hour cancellation policy
- ✅ Maximum advance booking (14 days default)
- ✅ Business hours validation
- ✅ No past date bookings

**Validated Tools**:
- `create_booking`: Validates date/time against all policies
- `cancel_booking`: Validates cancellation notice requirement
- `update_booking`: Validates new date/time if changed

**Error Response Format**:
```python
{
    "error": "Same-day bookings require at least 2.0 hours notice",
    "policy": "minimum_notice",
    "hours_needed": 2.0,
    "hours_available": 1.5,
    "suggestion": "Please book for 2025-11-11 15:00 or later"
}
```

**Benefits**:
- 🛡️ Prevents policy violations before API calls
- 💰 Reduces unnecessary database queries
- 🤖 Provides structured feedback for LLM
- 📝 Centralized policy enforcement

---

### ConversationSummaryMiddleware
**Location**: `src/agent/middleware/conversation_summary.py`

Manages conversation memory by trimming message history when it exceeds limits.

**Configuration**:
- `max_messages`: 20 (default)

**Behavior**:
- Preserves system messages
- Adds summary message for context
- Prevents token bloat in long conversations

---

### PIIMiddleware (Built-in)
**Location**: `langchain.agents.middleware.PIIMiddleware`

Redacts or masks Personally Identifiable Information before sending to LLM.

**Current Configuration**:
```python
PIIMiddleware("email", strategy="mask", apply_to_input=True)
PIIMiddleware("credit_card", strategy="mask", apply_to_input=True)
```

**PII Types**:
- `email`: Email addresses → `[MASKED_EMAIL]`
- `credit_card`: Card numbers → `****-****-****-1234`
- `ip`: IP addresses → `[MASKED_IP]`
- `mac_address`, `url`: Additional types available

**Strategies**:
- `mask`: Partially obscure (e.g., last 4 digits)
- `redact`: Replace with `[REDACTED_TYPE]`
- `hash`: Replace with deterministic hash
- `block`: Raise exception when detected

---

### UsageTrackingMiddleware
**Location**: `src/agent/middleware/usage_tracking.py`

Tracks LLM token consumption for monitoring and cost analysis.

**Tracks**:
- Input tokens
- Output tokens
- Total tokens per call
- Session totals

**Usage**:
```python
# Get current statistics
stats = usage_tracking_middleware.get_stats()
# {'total_input_tokens': 1200, 'total_output_tokens': 450, 'total_calls': 5}

# Reset for new session
usage_tracking_middleware.reset_stats()
```

---

### HumanInTheLoopMiddleware (Built-in)
**Location**: `langchain.agents.middleware.HumanInTheLoopMiddleware`

Pauses execution for human approval on sensitive operations.

**Configuration**:
```python
HumanInTheLoopMiddleware(
    interrupt_on={
        "create_booking": {"allowed_decisions": ["approve", "reject"]},
        "cancel_booking": {"allowed_decisions": ["approve", "reject"]},
        "modify_booking": {"allowed_decisions": ["approve", "reject"]},
    },
    description_prefix="Booking action pending approval"
)
```

**Flow**:
1. Agent decides to call sensitive tool
2. Execution pauses with `__interrupt__` flag
3. User reviews action details
4. User approves or rejects
5. Execution resumes or cancels

**Resumption**:
```python
from langchain_core.command import Command

# Approve and continue
agent.invoke(
    Command(resume={"decisions": [{"type": "approve"}]}),
    config={"configurable": {"thread_id": "session_123"}}
)
```

**Note**: Requires `MemorySaver` checkpointer for state persistence.

---

## Execution Order

```mermaid
sequenceDiagram
    participant User
    participant BC as BookingContext
    participant CS as ConversationSummary
    participant PII
    participant Model as LLM
    participant UT as UsageTracking
    participant HITL as HumanInLoop
    participant Tool

    User->>BC: Message
    BC->>BC: Inject date/context
    BC->>CS: Enhanced state
    CS->>CS: Trim history
    CS->>PII: Managed history
    PII->>PII: Mask sensitive data
    PII->>Model: Sanitized input
    Model->>UT: Response
    UT->>UT: Track tokens
    UT->>HITL: Check for tool calls

    alt Sensitive Tool
        HITL->>User: Request approval
        User->>HITL: Approve/Reject
    end

    HITL->>Tool: Execute if approved
    Tool->>User: Result
```

## Testing

### Test PII Masking
```python
# Email
agent.invoke({"messages": [{"role": "user", "content": "Email: john@example.com"}]})
# LLM sees: "Email: [MASKED_EMAIL]"

# Credit card
agent.invoke({"messages": [{"role": "user", "content": "Card: 4532-1234-5678-9010"}]})
# LLM sees: "Card: ****-****-****-9010"
```

### Test Usage Tracking
```python
# Run conversation
agent.invoke({"messages": [...]})

# Check statistics
stats = usage_tracking_middleware.get_stats()
print(f"Total tokens: {stats['total_tokens']}")
print(f"Total calls: {stats['total_calls']}")
```

### Test Human-in-the-Loop
```python
# First call - triggers interrupt
result = agent.invoke(
    {"messages": [{"role": "user", "content": "Book me for tomorrow 2pm"}]},
    config={"configurable": {"thread_id": "test_123"}}
)

# Check interrupt
if "__interrupt__" in result:
    print(f"Pending: {result['__interrupt__']}")

# Resume with approval
result = agent.invoke(
    Command(resume={"decisions": [{"type": "approve"}]}),
    config={"configurable": {"thread_id": "test_123"}}
)
```

## Adding Custom Middleware

Extend `AgentMiddleware` and implement desired hooks:

```python
from langchain.agents.middleware import AgentMiddleware

class CustomMiddleware(AgentMiddleware):
    @property
    def name(self) -> str:
        return "custom_middleware"

    def before_model(self, state, config):
        # Modify state before LLM call
        state["custom_field"] = "value"
        return state

    def after_model(self, output, state, config):
        # Process LLM response
        print(f"Model generated: {output}")
        return output

# Add to agent
agent = create_agent(
    model=llm,
    tools=tools,
    middleware=[
        conversation_summary_middleware,
        CustomMiddleware(),  # Your middleware
        usage_tracking_middleware,
    ]
)
```
