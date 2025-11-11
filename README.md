# 💈 Barbershop Booking Agent

AI-powered barbershop booking system with conversational interface, built on LangChain agents with FastAPI backend.

## Features

- **Conversational AI Agent**: Natural language booking interface powered by LangChain
- **Business Rules Enforcement**: Validates bookings (2-hour minimum notice, 24-hour cancellation policy)
- **Middleware Stack**: PII masking, usage tracking, context injection, human-in-the-loop
- **REST API**: FastAPI backend for customers, barbers, services, and bookings
- **Async SQLAlchemy**: Database layer with Alembic migrations

## Example Booking Flow

### Successful Booking Journey

```mermaid
sequenceDiagram
    participant User
    participant Agent
    participant BR as Business Rules
    participant Tools
    participant HITL as Human-in-Loop
    participant DB as Database

    User->>Agent: "Book haircut with Donny tomorrow at 7pm"<br/>Email: james.w@email.com

    Agent->>Tools: lookup_customer(email)
    Tools->>DB: Query customer by email
    DB-->>Tools: Customer record
    Tools-->>Agent: ✓ Found: James Wilson (ID: f31601...)

    Agent->>Tools: search_barber(name="Donny")
    Tools->>DB: Query barbers by name
    DB-->>Tools: Barber record
    Tools-->>Agent: ✓ Found: Donny Rodriguez (ID: 3b9c70...)

    Agent->>Tools: list_services()
    Tools->>DB: Query available services
    DB-->>Tools: Service records
    Tools-->>Agent: ✓ Premium Haircut ($45, 45min)

    Agent->>Tools: check_availability(barber_id, date, time)
    Tools->>DB: Query existing bookings
    DB-->>Tools: Schedule data
    Tools-->>Agent: ✓ Available: Nov 11, 7:00 PM

    Agent->>BR: Validate before create_booking()
    Note over BR: Check business rules:<br/>✓ Not in past<br/>✓ >2h notice (31h)<br/>✓ Before 2pm cutoff<br/>✓ Within 14 days<br/>✓ Business hours (9am-8pm)
    BR-->>Agent: ✓ Policy compliant

    Agent->>HITL: ⚠️ Booking requires approval
    Note over HITL: Customer: James Wilson<br/>Barber: Donny Rodriguez<br/>Service: Premium Haircut ($45)<br/>Date/Time: Nov 11, 7:00 PM

    User->>HITL: Approve ✓
    HITL-->>Agent: Approved

    Agent->>Tools: create_booking(customer, barber, service, datetime)
    Tools->>DB: INSERT booking record
    DB-->>Tools: Booking ID: a1b2c3d4...
    Tools-->>Agent: ✓ Booking created

    Agent->>User: ✅ Booking confirmed!<br/>ID: a1b2c3d4...<br/>Donny Rodriguez<br/>Nov 11, 2025 at 7:00 PM<br/>Premium Haircut ($45)
```

### Policy Violation - Same-Day After Cutoff

```mermaid
sequenceDiagram
    participant User
    participant Agent
    participant BR as Business Rules
    participant Tools

    User->>Agent: "Book a haircut today at 8pm with Tony"<br/>Current time: 7:42 PM

    Agent->>Tools: lookup_customer(email)
    Tools-->>Agent: ✓ Found customer

    Agent->>Tools: search_barber(name="Tony")
    Tools-->>Agent: ✓ Found: Tony Martinez

    Agent->>BR: Validate before create_booking()
    Note over BR: Check same-day rules:<br/>Current: 7:42 PM<br/>Cutoff: 2:00 PM<br/>❌ After cutoff time
    BR-->>Agent: ❌ Policy violation: same_day_cutoff

    Note over Agent: LLM receives error:<br/>"Same-day bookings must be<br/>made before 14:00"

    Agent->>User: ❌ Sorry, same-day bookings must be<br/>made before 2:00 PM. The cutoff<br/>has passed for today.<br/><br/>Would you like to book for<br/>tomorrow (Nov 11) or later?
```

### Successful Cancellation Journey

```mermaid
sequenceDiagram
    participant User
    participant Agent
    participant BR as Business Rules
    participant Tools
    participant HITL as Human-in-Loop
    participant DB as Database

    User->>Agent: "Cancel my booking for next week"<br/>Email: james.w@email.com

    Agent->>Tools: lookup_customer(email)
    Tools->>DB: Query customer
    DB-->>Tools: Customer record
    Tools-->>Agent: ✓ Found: James Wilson

    Agent->>Tools: get_bookings(customer_id, status="scheduled")
    Tools->>DB: Query bookings
    DB-->>Tools: Booking records
    Tools-->>Agent: ✓ Found: Nov 18, 2:00 PM<br/>with Tony Martinez

    Agent->>BR: Validate before cancel_booking()
    Note over BR: Check cancellation policy:<br/>Booking: Nov 18, 2:00 PM<br/>Current: Nov 10, 7:42 PM<br/>Notice: 174+ hours<br/>✓ >24h requirement met
    BR-->>Agent: ✓ Policy compliant

    Agent->>HITL: ⚠️ Cancellation requires approval
    Note over HITL: Cancel booking:<br/>Customer: James Wilson<br/>Barber: Tony Martinez<br/>Service: Basic Haircut<br/>Date/Time: Nov 18, 2:00 PM<br/>ID: xyz789...

    User->>HITL: Approve ✓
    HITL-->>Agent: Approved

    Agent->>Tools: cancel_booking(booking_id)
    Tools->>DB: UPDATE status = 'cancelled'
    DB-->>Tools: Success
    Tools-->>Agent: ✓ Booking cancelled

    Agent->>User: ✅ Your booking has been cancelled:<br/>Nov 18, 2025 at 2:00 PM<br/>with Tony Martinez<br/><br/>Feel free to book again anytime!
```

### Policy Violation - Insufficient Cancellation Notice

```mermaid
sequenceDiagram
    participant User
    participant Agent
    participant BR as Business Rules
    participant Tools

    User->>Agent: "Cancel my appointment tomorrow at 2pm"<br/>Current: Nov 10, 7:42 PM

    Agent->>Tools: lookup_customer(email)
    Tools-->>Agent: ✓ Found customer

    Agent->>Tools: get_bookings(customer_id)
    Tools-->>Agent: ✓ Found: Nov 11, 2:00 PM

    Agent->>BR: Validate before cancel_booking()
    Note over BR: Check cancellation policy:<br/>Booking: Nov 11, 2:00 PM<br/>Current: Nov 10, 7:42 PM<br/>Notice: ~18 hours<br/>❌ <24h requirement
    BR-->>Agent: ❌ Policy violation: cancellation_notice

    Note over Agent: LLM receives error:<br/>"Cancellations require at least<br/>24 hours notice"

    Agent->>User: ❌ Sorry, cancellations require at<br/>least 24 hours notice. Your booking<br/>is in 18 hours.<br/><br/>Our policy helps barbers manage<br/>their schedules. You can still<br/>reschedule if you'd like.
```

### Successful Update Booking Journey

```mermaid
sequenceDiagram
    participant User
    participant Agent
    participant BR as Business Rules
    participant Tools
    participant HITL as Human-in-Loop
    participant DB as Database

    User->>Agent: "Move my appointment to Friday at 3pm"<br/>Email: james.w@email.com

    Agent->>Tools: lookup_customer(email)
    Tools-->>Agent: ✓ Found: James Wilson

    Agent->>Tools: get_bookings(customer_id)
    Tools-->>Agent: ✓ Current: Nov 11, 7:00 PM

    Agent->>Tools: check_availability(barber_id, new_date, new_time)
    Tools-->>Agent: ✓ Available: Nov 14, 3:00 PM

    Agent->>BR: Validate before update_booking()
    Note over BR: Check business rules for new time:<br/>✓ Not in past<br/>✓ >2h notice (if same-day)<br/>✓ Within 14 days<br/>✓ Business hours
    BR-->>Agent: ✓ Policy compliant

    Agent->>HITL: ⚠️ Update requires approval
    Note over HITL: Update booking:<br/>FROM: Nov 11, 7:00 PM<br/>TO: Nov 14, 3:00 PM<br/>Customer: James Wilson<br/>Barber: Donny Rodriguez

    User->>HITL: Approve ✓
    HITL-->>Agent: Approved

    Agent->>Tools: update_booking(booking_id, new_date, new_time)
    Tools->>DB: UPDATE booking record
    DB-->>Tools: Success
    Tools-->>Agent: ✓ Booking updated

    Agent->>User: ✅ Booking updated successfully!<br/>New appointment:<br/>Nov 14, 2025 at 3:00 PM<br/>with Donny Rodriguez
```

### Policy Enforcement Flow

```mermaid
flowchart TD
    Start([User: Book today at 2pm]) --> CheckTime{Check current time}

    CheckTime -->|After 2pm cutoff| Reject[❌ Same-day cutoff passed]
    CheckTime -->|Before cutoff| CheckNotice{At least 2h notice?}

    CheckNotice -->|No| Reject
    CheckNotice -->|Yes| CheckAvail[Check barber availability]

    CheckAvail --> IsAvail{Barber available?}
    IsAvail -->|No| Suggest[Suggest alternative times]
    IsAvail -->|Yes| Check24h{Cancellation: 24h notice?}

    Reject --> Offer[Offer tomorrow or later]
    Offer --> End([User chooses alternative])

    Check24h -->|No| Warn[⚠️ Cannot cancel within 24h]
    Check24h -->|Yes| HITL[Human-in-Loop Approval]

    HITL --> Approved{User approves?}
    Approved -->|Yes| Success[✅ Booking created]
    Approved -->|No| Cancelled([Booking cancelled])

    Success --> End
    Suggest --> End
    Warn --> End

    style Reject fill:#ffcdd2
    style Success fill:#c8e6c9
    style HITL fill:#fff9c4
    style Warn fill:#ffe0b2
```

## Documentation

Detailed documentation available in the `docs/` folder:

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture, tech stack, and design decisions
- **[AGENT_IMPLEMENTATIONS.md](docs/AGENT_IMPLEMENTATIONS.md)** - Agent implementation details and patterns
- **[MIDDLEWARE.md](docs/MIDDLEWARE.md)** - Middleware components and execution flow

## Development Setup

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- OpenAI API key

### Installation

```bash
# Clone repository
git clone <repository-url>
cd barbershop

# Install dependencies with uv
uv sync

# Or with pip
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### Database Setup

```bash
# Initialize database schema
uv run poe db-init

# Seed with sample data
uv run poe db-seed

# List all data
uv run poe db-list

# List specific entities
uv run poe db-list-customers
uv run poe db-list-barbers
uv run poe db-list-services
uv run poe db-list-availability
uv run poe db-list-bookings

# Clear and reseed
uv run poe db-seed-clear
```

## Running the Application

### Development Servers

```bash
# Start FastAPI backend (port 8005)
uv run poe dev-api

# Start Chainlit UI (port 8006)
uv run poe dev-ui

# Run CLI agent directly
uv run poe dev-agent

# Start both API and UI together
uv run poe dev-all
```

### Database Management

The project uses Alembic for database migrations with async SQLAlchemy support.

```bash
# Create new migration (after modifying models)
uv run poe db-migrate "description of changes"
# Or directly: uv run alembic revision --autogenerate -m "message"

# Apply migrations
uv run poe db-upgrade
# Or directly: uv run alembic upgrade head

# Rollback one migration
uv run poe db-downgrade
# Or directly: uv run alembic downgrade -1

# Check current migration version
uv run poe db-current

# View migration history
uv run poe db-history

# Reset database (downgrade + upgrade)
uv run poe db-reset
```

**Configuration:**
- `alembic.ini` - Alembic configuration file
- `alembic/env.py` - Async migration environment setup
- `alembic/versions/` - Migration scripts directory

**Best Practices:**
- Always create a migration after modifying database models
- Review auto-generated migrations before applying them
- Test migrations on a development database first
- Never modify migration files after they've been applied to production

## Testing

```bash
# Run all tests
uv run poe test

# Unit tests only
uv run poe test-unit

# Integration tests only
uv run poe test-integration

# Generate coverage report
uv run poe test-cov
```

## Code Quality

```bash
# Linting
uv run poe lint           # Check for issues
uv run poe lint-fix       # Auto-fix issues

# Formatting
uv run poe format         # Format code with black
uv run poe format-check   # Check formatting

# Type checking
uv run poe type-check     # Run mypy

# Combined quality checks
uv run poe quality        # format + lint-fix + type-check
uv run poe check          # format-check + lint + type-check + test
uv run poe pre-commit     # quality + test (run before committing)
```

## Pre-commit Hooks

Install pre-commit hooks for automatic code quality checks:

```bash
# Install pre-commit
pip install pre-commit

# Install git hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

Pre-commit hooks include:
- Ruff linting and formatting
- Black formatting
- MyPy type checking
- Trailing whitespace removal
- YAML/JSON validation
- Security scanning with Bandit

## CI/CD

GitHub Actions workflows are configured in `.github/workflows/`:

### Continuous Integration (CI)
Runs on push and pull requests:
- **Lint & Format**: Ruff and Black checks
- **Type Check**: MyPy static analysis
- **Tests**: Unit and integration tests (Python 3.11 & 3.12)
- **Security**: Bandit security scanning
- **Build**: Package build verification
- **CodeQL**: Security vulnerability scanning

### Continuous Deployment (CD)
Triggered by version tags (`v*.*.*`):
- **Build & Push**: Docker image to GitHub Container Registry
- **Deploy Staging**: Auto-deploy to staging environment
- **Deploy Production**: Deploy to production (requires approval)
- **Release**: Create GitHub release with changelog

**Trigger deployment**:
```bash
# Create and push version tag
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

## Docker

Build and run with Docker:

```bash
# Build image
docker build -t barbershop-agent .

# Run API server
docker run -p 8005:8005 -e OPENAI_API_KEY=sk-... barbershop-agent

# Run with docker-compose (create docker-compose.yml first)
docker-compose up
```

## Project Structure

```
barbershop/
├── src/
│   ├── agent/              # LangChain agent implementation
│   │   ├── middleware/     # Middleware components
│   │   ├── tools/          # Agent tools (booking, customer, etc.)
│   │   └── llm/            # LLM registry
│   ├── api/                # FastAPI application
│   │   ├── models/         # Database models & schemas
│   │   └── routers/        # API endpoints
│   ├── core/               # Core configuration
│   └── ui/                 # Chainlit chat interface
├── tests/
│   ├── unit/               # Unit tests
│   └── integration/        # Integration tests
├── docs/                   # Documentation
├── alembic/                # Database migrations
├── run.py                  # CLI agent runner
└── pyproject.toml          # Project configuration
```

## Middleware Stack

The agent uses the following middleware (in execution order):

1. **business_rules** - Enforces booking policies BEFORE tool execution:
   - 2-hour minimum notice for same-day bookings
   - 24-hour cancellation policy
   - Business hours validation
   - Maximum advance booking window (14 days)
2. **conversation_summary** - Trims conversation history to prevent context overflow
3. **PII masking** - Masks emails and credit card numbers before sending to LLM
4. **usage_tracking** - Tracks token consumption for monitoring
5. **human_in_the_loop** - Requires approval for sensitive operations (`create_booking`, `cancel_booking`, `update_booking`)

See [MIDDLEWARE.md](docs/MIDDLEWARE.md) for details.

## License

MIT License
