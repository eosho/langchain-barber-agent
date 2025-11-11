# Architecture Documentation

AI-powered barbershop booking system architecture using LangChain agents with FastAPI backend.

## System Overview

```mermaid
graph TB
    subgraph "Client Layer"
        CLI[CLI Agent<br/>run.py]
        EXT[External Apps<br/>HTTP/REST]
    end

    subgraph "Application Layer"
        subgraph "Agent"
            AGENT[create_agent<br/>LangChain v1]
            MW[Middleware<br/>5 components]
            TOOLS[Custom Tools<br/>8 tools]
        end

        subgraph "API"
            ROUTER[FastAPI<br/>REST Endpoints]
            MODELS[SQLAlchemy<br/>ORM Models]
        end

        AGENT --> MW
        AGENT --> TOOLS
        TOOLS --> ROUTER
        ROUTER --> MODELS
    end

    subgraph "Data Layer"
        DB[(SQLite/PostgreSQL<br/>5 tables)]
    end

    CLI -->|Terminal| AGENT
    EXT -->|HTTP| ROUTER
    MODELS -->|SQL| DB

    style AGENT fill:#e1f5ff
    style MW fill:#fff3e0
    style DB fill:#f3e5f5
```

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Agent** | LangChain v1 `create_agent` | Conversational booking logic |
| **LLM** | GPT-4-mini | Natural language understanding |
| **Middleware** | LangChain middleware pattern | Context, PII, tracking, approval |
| **API** | FastAPI + Uvicorn | REST endpoints |
| **Database** | SQLAlchemy + SQLite/PostgreSQL | Data persistence |
| **Migrations** | Alembic | Schema management |

## Agent Architecture

### Why create_agent?

Using LangChain's `create_agent` instead of raw LangGraph:

```python
agent = create_agent(
    model=llm,
    tools=[...],                    # 8 custom tools
    system_prompt=prompt,           # Formatted with context
    middleware=[...],               # 5 middleware components
    checkpointer=MemorySaver()      # For HITL interrupts
)
```

**Tools** (see [AGENT_IMPLEMENTATIONS.md](AGENT_IMPLEMENTATIONS.md)):
- `check_availability` - Query available time slots
- `get_barbers` - List barbers and specialties
- `get_services` - List services and pricing
- `lookup_customer` - Find customer by email/phone
- `create_booking` - Create new booking
- `modify_booking` - Change existing booking
- `cancel_booking` - Cancel booking
- `check_policies` - Query business policies

**Middleware** (see [MIDDLEWARE.md](MIDDLEWARE.md)):
1. BusinessRules - Enforce booking policies before tool execution
2. ConversationSummary - Trim message history
3. PIIMiddleware (email) - Mask sensitive data
4. PIIMiddleware (credit_card) - Mask card numbers
5. UsageTracking - Track token usage
6. HumanInTheLoop - Approval for sensitive ops

## Data Flow

### Booking Creation Flow

```mermaid
sequenceDiagram
    actor User
    participant Agent
    participant Tools
    participant API
    participant DB

    User->>Agent: "Book haircut Friday 2pm"

    Agent->>Tools: check_availability(date, service)
    Tools->>API: GET /bookings/availability
    API->>DB: Query slots
    DB-->>API: Available times
    API-->>Tools: [14:00, 14:30, 15:00]
    Tools-->>Agent: Slots available

    Agent->>User: "2 PM available. Name & phone?"
    User->>Agent: "John Smith, 555-0123"

    Note over Agent,Tools: HumanInLoop interrupt
    Agent->>User: 🔔 Approve booking?
    User->>Agent: Approve

    Agent->>Tools: create_booking(...)
    Tools->>API: POST /bookings
    API->>DB: INSERT booking
    DB-->>API: Success: BK0001
    API-->>Tools: Booking created
    Tools-->>Agent: ✅ Confirmed

    Agent->>User: "Booked! Friday 2 PM. ID: BK0001"
```

### State Management

```mermaid
stateDiagram-v2
    [*] --> Initial

    Initial --> ServiceKnown: User mentions service
    ServiceKnown --> DateTimeKnown: User specifies date/time
    DateTimeKnown --> CustomerKnown: User provides contact
    CustomerKnown --> AwaitingApproval: Agent calls create_booking

    AwaitingApproval --> Complete: User approves
    AwaitingApproval --> DateTimeKnown: User rejects

    Complete --> [*]

    note right of Initial
        {}
    end note

    note right of ServiceKnown
        {service_type: "haircut"}
    end note

    note right of DateTimeKnown
        {service: "haircut",
         date: "2024-11-15",
         time: "14:00"}
    end note

    note right of Complete
        {service: "haircut",
         date: "2024-11-15",
         time: "14:00",
         customer: "John Smith",
         phone: "+15550123",
         booking_id: "BK0001"}
    end note
```

## API Architecture

### Endpoints

| Route | Methods | Purpose |
|-------|---------|---------|
| `/bookings` | GET, POST | List/create bookings |
| `/bookings/{id}` | GET, PUT, DELETE | Manage booking |
| `/bookings/availability` | GET | Check available slots |
| `/customers` | GET, POST | List/create customers |
| `/customers/{id}` | GET, PUT, DELETE | Manage customer |
| `/customers/lookup` | GET | Find by email/phone |
| `/barbers` | GET, POST | List/create barbers |
| `/barbers/{id}` | GET, PUT, DELETE | Manage barber |
| `/services` | GET, POST | List/create services |
| `/services/{id}` | GET, PUT, DELETE | Manage service |

### Database Schema

```mermaid
erDiagram
    CUSTOMERS ||--o{ BOOKINGS : makes
    BARBERS ||--o{ BOOKINGS : assigned
    BARBERS ||--o{ AVAILABILITY : has
    SERVICES ||--o{ BOOKINGS : includes

    CUSTOMERS {
        uuid id PK
        string name
        string email UK
        string phone UK
        datetime created_at
    }

    BARBERS {
        uuid id PK
        string name
        string specialty
        boolean active
    }

    SERVICES {
        uuid id PK
        string name
        int duration_minutes
        decimal price
    }

    BOOKINGS {
        uuid id PK
        uuid customer_id FK
        uuid barber_id FK
        uuid service_id FK
        datetime start_time
        string status
        datetime created_at
    }

    AVAILABILITY {
        uuid id PK
        uuid barber_id FK
        int day_of_week
        time start_time
        time end_time
    }
```

## Configuration

Uses Pydantic Settings for type-safe configuration:

```python
from src.core.config import get_settings

settings = get_settings()

# Type-checked access
api_port: int = settings.api_port
openai_key: str = settings.openai_api_key
db_url: str = settings.database_url
```

**Environment Variables**:
```bash
# LLM
OPENAI_API_KEY=sk-...

# API
API_HOST=0.0.0.0
API_PORT=8005

# Database
DATABASE_URL=sqlite:///./barbershop.db

# Agent
AGENT_MODEL=gpt-4-mini
AGENT_TEMPERATURE=0.7
```

## Error Handling

```mermaid
graph TD
    ERROR[Error Occurs] --> LEVEL{Where?}

    LEVEL -->|Tool| T[Tool catches specific errors]
    LEVEL -->|Middleware| M[Middleware wraps calls]
    LEVEL -->|API| A[FastAPI exception handlers]

    T --> T1[BookingConflictError]
    T --> T2[ValidationError]
    T --> T3[DatabaseError]
    T1 & T2 & T3 --> MSG[User-friendly message]

    M --> M1[Validate before tool]
    M --> M2[Catch unexpected errors]
    M1 & M2 --> MSG

    A --> A1[400 Bad Request]
    A --> A2[404 Not Found]
    A --> A3[409 Conflict]
    A --> A4[500 Internal Error]
    A1 & A2 & A3 & A4 --> JSON[JSON error response]

    MSG --> AGENT[Agent suggests alternatives]
    JSON --> CLIENT[Client handles error]
```

## Tool Design Pattern

All tools follow this structure:

```python
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

class ToolInput(BaseModel):
    """Input schema with validation."""
    param: str = Field(description="Parameter description")

class CustomTool(BaseTool):
    """Tool description for agent."""

    name: str = "tool_name"
    description: str = "When to use this tool"
    args_schema: type[BaseModel] = ToolInput

    async def _arun(self, **kwargs) -> str:
        """Execute tool logic."""
        try:
            # 1. Validate inputs
            # 2. Call API
            # 3. Format response
            return "Success message"
        except SpecificError as e:
            return f"Error: {user_friendly_message}"
```

**Principles**:
- Return strings (agent-readable)
- Include success and error paths
- Validate inputs with Pydantic
- Single responsibility
- Detailed descriptions for agent

## Development Workflow

```bash
# Start API server
uv run poe dev-api

# Run agent CLI
uv run poe dev-agent

# Run tests
uv run poe test

# Code quality
uv run poe lint
uv run poe format
uv run poe type-check
```

See [README.md](../README.md) for full development setup.
