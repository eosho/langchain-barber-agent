"""Integration tests for Barbers API endpoints."""

from httpx import AsyncClient


class TestBarbersAPI:
    """Test barber CRUD endpoints."""

    async def test_list_barbers(self, client: AsyncClient):
        """Test GET /api/v1/barbers."""
        response = await client.get("/api/v1/barbers")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) > 0  # Should have seed data

    async def test_get_barber(self, client: AsyncClient):
        """Test GET /api/v1/barbers/{barber_id}."""
        # Get a barber first
        list_response = await client.get("/api/v1/barbers?limit=1")
        if list_response.json():
            barber_id = list_response.json()[0]["id"]
            response = await client.get(f"/api/v1/barbers/{barber_id}")
            assert response.status_code == 200
            assert response.json()["id"] == barber_id

    async def test_get_barber_not_found(self, client: AsyncClient):
        """Test GET /api/v1/barbers/{barber_id} with invalid ID."""
        response = await client.get("/api/v1/barbers/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    async def test_create_barber(self, client: AsyncClient):
        """Test POST /api/v1/barbers."""
        import random

        unique_num = random.randint(1000000000, 9999999999)
        barber_data = {
            "name": "New Test Barber",
            "email": f"newbarber_{unique_num}@example.com",
            "phone": f"+1{unique_num}",
            "specialties": ["Haircut", "Beard Trim"],
        }
        response = await client.post("/api/v1/barbers", json=barber_data)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == barber_data["email"]
        assert "id" in data

        # Clean up - delete the created barber
        barber_id = data["id"]
        await client.delete(f"/api/v1/barbers/{barber_id}")

    async def test_update_barber(self, client: AsyncClient):
        """Test PUT /api/v1/barbers/{barber_id}."""
        # Get a barber first
        list_response = await client.get("/api/v1/barbers?limit=1")
        if list_response.json():
            barber_id = list_response.json()[0]["id"]
            update_data = {"specialties": ["haircut", "fade", "beard"]}
            response = await client.put(f"/api/v1/barbers/{barber_id}", json=update_data)
            assert response.status_code == 200
            assert len(response.json()["specialties"]) == 3

    async def test_delete_barber(self, client: AsyncClient):
        """Test DELETE /api/v1/barbers/{barber_id}."""
        import random

        unique_num = random.randint(1000000000, 9999999999)
        # Create a barber to delete
        barber_data = {
            "name": f"Delete Test Barber {unique_num}",
            "email": f"deletebarber_{unique_num}@example.com",
            "phone": f"+1{unique_num}",
            "specialties": ["test"],
        }
        create_response = await client.post("/api/v1/barbers", json=barber_data)
        barber_id = create_response.json()["id"]

        # Delete it (soft delete)
        response = await client.delete(f"/api/v1/barbers/{barber_id}")
        assert response.status_code == 204

        # Verify it's marked as inactive (soft delete)
        get_response = await client.get(f"/api/v1/barbers/{barber_id}")
        assert get_response.status_code == 200
        assert get_response.json()["is_active"] is False
