"""Fixtures shared across all API integration tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app
from src.core.database import get_db


@pytest.fixture
async def client():
    """Create an async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as ac:
        yield ac


@pytest.fixture
async def db_session():
    """Get a database session for test setup."""
    async for session in get_db():
        yield session
