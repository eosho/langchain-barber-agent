"""FastAPI main application for the barbershop booking system.

This module creates and configures the FastAPI application with all
routes, middleware, and lifecycle hooks.

Example:
    Run the API server:
    $ uvicorn src.api.main:app --reload
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src import __version__
from src.api.models.schemas import HealthResponse
from src.api.routers import barbers, bookings, customers, services
from src.core.config import get_settings
from src.core.database import close_db, init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # noqa: ARG001
    """Manage application lifecycle.

    This context manager handles startup and shutdown events for the
    FastAPI application.

    Args:
        app: The FastAPI application instance.

    Yields:
        None: Control flow during application runtime.
    """
    # Startup
    print("🚀 Starting application")

    # Initialize database
    if settings.environment == "development":
        await init_db()
        print("✅ Database initialized")

    yield

    # Shutdown
    print("👋 Shutting down application")
    await close_db()
    print("✅ Database connections closed")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description="AI-powered barbershop booking system with conversational interface",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_credentials,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)


# ============================================================================
# Root Routes
# ============================================================================


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """Root endpoint with API information.

    Returns:
        Dictionary with API metadata.
    """
    return {
        "name": settings.app_name,
        "version": __version__,
        "status": "operational",
        "docs": "/docs" if settings.debug else "disabled",
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check endpoint.

    Returns:
        Health status with version and timestamp.

    Example:
        >>> import httpx
        >>> response = httpx.get("http://localhost:8000/health")
        >>> response.json()
        {"status": "healthy", "version": "0.1.1", "timestamp": "2024-11-09T..."}
    """
    return HealthResponse(status="healthy", version=__version__, timestamp=datetime.now())


# ============================================================================
# Include Routers
# ============================================================================

app.include_router(barbers.router, prefix="/api/v1/barbers", tags=["Barbers"])
app.include_router(bookings.router, prefix="/api/v1/bookings", tags=["Bookings"])
app.include_router(customers.router, prefix="/api/v1/customers", tags=["Customers"])
app.include_router(services.router, prefix="/api/v1/services", tags=["Services"])


# ============================================================================
# Development helpers
# ============================================================================


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower(),
    )
