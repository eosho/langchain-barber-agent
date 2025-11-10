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
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.models.schemas import ErrorResponse, HealthResponse
from src.api.routers import barbers, bookings, customers, services
from src.core.config import get_settings
from src.core.database import close_db, init_db
from src.core.exceptions import BarbershopError

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
    print(f"🚀 Starting {settings.app_name} v{settings.app_version}")
    print(f"🌍 Environment: {settings.environment}")

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
    version=settings.app_version,
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
# Exception Handlers
# ============================================================================


@app.exception_handler(BarbershopError)
async def barbershop_error_handler(
    request: Any,  # noqa: ARG001
    exc: BarbershopError,
) -> JSONResponse:
    """Handle custom barbershop errors.

    Args:
        request: The incoming request.
        exc: The barbershop exception.

    Returns:
        JSON response with error details.
    """
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error=exc.__class__.__name__, message=exc.message, details=exc.details
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Any,  # noqa: ARG001
    exc: Exception,
) -> JSONResponse:
    """Handle unexpected errors.

    Args:
        request: The incoming request.
        exc: The exception.

    Returns:
        JSON response with error details.
    """
    error_message = str(exc) if settings.debug else "An unexpected error occurred"

    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="InternalServerError",
            message=error_message,
            details={"type": exc.__class__.__name__} if settings.debug else None,
        ).model_dump(),
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
        "version": settings.app_version,
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
        {"status": "healthy", "version": "0.1.0", "timestamp": "2024-11-09T..."}
    """
    return HealthResponse(status="healthy", version=settings.app_version, timestamp=datetime.now())


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
