# Barbershop Booking Agent

AI-powered barbershop booking system with conversational interface, built on LangChain agents with FastAPI backend.

## Features

- **Conversational AI Agent**: Natural language booking interface powered by LangChain
- **Business Rules Enforcement**: Validates bookings (2-hour minimum notice, 24-hour cancellation policy)
- **Middleware Stack**: PII masking, usage tracking, context injection, human-in-the-loop
- **REST API**: FastAPI backend for customers, barbers, services, and bookings
- **Chat UI**: Chainlit-powered conversational interface
- **Async SQLAlchemy**: Database layer with Alembic migrations

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

```bash
# Create new migration
uv run poe db-migrate "description of changes"

# Apply migrations
uv run poe db-upgrade

# Rollback one migration
uv run poe db-downgrade

# Reset database (downgrade + upgrade)
uv run poe db-reset
```

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

Test suite includes:
- **28 unit tests** - Middleware components (business rules, usage tracking, booking context)
- **8 integration tests** - Agent middleware integration
- **29 API tests** - FastAPI endpoints

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

1. **booking_context** - Injects current date and business context
2. **conversation_summary** - Trims conversation history
3. **PII masking** - Masks emails and credit card numbers
4. **usage_tracking** - Tracks token consumption
5. **human_in_the_loop** - Requires approval for sensitive operations (`create_booking`, `cancel_booking`, `update_booking`)

See [MIDDLEWARE.md](docs/MIDDLEWARE.md) for details.

## Business Rules

- **Minimum booking notice**: 2 hours
- **Maximum booking window**: 90 days
- **Business hours**: 9 AM - 6 PM
- **Closed**: Sundays
- **Cancellation policy**: 24 hours notice required

## License

MIT
