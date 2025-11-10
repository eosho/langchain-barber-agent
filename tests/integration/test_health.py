"""Integration test for API health check."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app


@pytest.mark.asyncio
async def test_api_health():
    """Test that the API server starts and is healthy."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as client:
        response = await client.get("/")
        assert response.status_code == 200
