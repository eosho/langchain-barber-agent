"""Integration tests for Services API endpoints."""

from httpx import AsyncClient


class TestServicesAPI:
    """Test service CRUD endpoints."""

    async def test_list_services(self, client: AsyncClient):
        """Test GET /api/v1/services."""
        response = await client.get("/api/v1/services")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) > 0  # Should have seed data

    async def test_get_service(self, client: AsyncClient):
        """Test GET /api/v1/services/{service_id}."""
        # Get a service first
        list_response = await client.get("/api/v1/services?limit=1")
        if list_response.json():
            service_id = list_response.json()[0]["id"]
            response = await client.get(f"/api/v1/services/{service_id}")
            assert response.status_code == 200
            assert response.json()["id"] == service_id

    async def test_get_service_not_found(self, client: AsyncClient):
        """Test GET /api/v1/services/{service_id} with invalid ID."""
        response = await client.get("/api/v1/services/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    async def test_create_service(self, client: AsyncClient):
        """Test POST /api/v1/services."""
        import uuid

        unique_id = str(uuid.uuid4())[:8]
        service_data = {
            "name": f"Test Service {unique_id}",
            "description": "Test description",
            "price": 49.99,
            "duration_minutes": 60,
            "category": "test",
        }
        response = await client.post("/api/v1/services", json=service_data)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == service_data["name"]
        assert data["price"] == service_data["price"]

        # Clean up - delete the created service
        service_id = data["id"]
        await client.delete(f"/api/v1/services/{service_id}")

    async def test_update_service(self, client: AsyncClient):
        """Test PUT /api/v1/services/{service_id}."""
        # Get a service first
        list_response = await client.get("/api/v1/services?limit=1")
        if list_response.json():
            service_id = list_response.json()[0]["id"]
            original_price = list_response.json()[0]["price"]
            new_price = original_price + 10.0
            update_data = {"price": new_price}
            response = await client.put(f"/api/v1/services/{service_id}", json=update_data)
            assert response.status_code == 200
            assert response.json()["price"] == new_price

    async def test_delete_service(self, client: AsyncClient):
        """Test DELETE /api/v1/services/{service_id}."""
        import uuid

        unique_id = str(uuid.uuid4())[:8]
        # Create a service to delete
        service_data = {
            "name": f"Delete Test Service {unique_id}",
            "description": "To be deleted",
            "price": 1.00,
            "duration_minutes": 15,
            "category": "test",
        }
        create_response = await client.post("/api/v1/services", json=service_data)
        service_id = create_response.json()["id"]

        # Delete it (soft delete)
        response = await client.delete(f"/api/v1/services/{service_id}")
        assert response.status_code == 204

        # Verify it's marked as inactive (soft delete)
        get_response = await client.get(f"/api/v1/services/{service_id}")
        assert get_response.status_code == 200
        assert get_response.json()["is_active"] is False
