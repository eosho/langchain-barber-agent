"""Integration tests for Customer API endpoints."""

import pytest
from httpx import AsyncClient


class TestCustomersAPI:
    """Test customer CRUD endpoints."""

    async def test_list_customers(self, client: AsyncClient):
        """Test GET /api/v1/customers."""
        response = await client.get("/api/v1/customers")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_list_customers_with_filters(self, client: AsyncClient):
        """Test GET /api/v1/customers with filters."""
        response = await client.get("/api/v1/customers?email=john&limit=10")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_get_customer(self, client: AsyncClient):
        """Test GET /api/v1/customers/{customer_id}."""
        # First get list to find a valid ID
        list_response = await client.get("/api/v1/customers?limit=1")
        if list_response.json():
            customer_id = list_response.json()[0]["id"]
            response = await client.get(f"/api/v1/customers/{customer_id}")
            assert response.status_code == 200
            assert response.json()["id"] == customer_id

    async def test_get_customer_not_found(self, client: AsyncClient):
        """Test GET /api/v1/customers/{customer_id} with invalid ID."""
        response = await client.get("/api/v1/customers/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    async def test_lookup_customer_by_email(self, client: AsyncClient):
        """Test GET /api/v1/customers/lookup/by-contact with email."""
        # Get a customer first
        list_response = await client.get("/api/v1/customers?limit=1")
        if list_response.json():
            email = list_response.json()[0]["email"]
            response = await client.get(f"/api/v1/customers/lookup/by-contact?email={email}")
            assert response.status_code == 200
            data = response.json()
            assert data is not None
            assert data["email"] == email

    async def test_lookup_customer_by_phone(self, client: AsyncClient):
        """Test GET /api/v1/customers/lookup/by-contact with phone."""
        from urllib.parse import quote

        # Get a customer first
        list_response = await client.get("/api/v1/customers?limit=10")
        if list_response.json():
            # Find a customer with a phone number
            for customer in list_response.json():
                if customer.get("phone"):
                    phone = customer["phone"]
                    # URL encode the phone number to preserve '+'
                    encoded_phone = quote(phone)
                    response = await client.get(
                        f"/api/v1/customers/lookup/by-contact?phone={encoded_phone}"
                    )
                    assert response.status_code == 200
                    data = response.json()
                    assert data is not None
                    assert data["phone"] == phone
                    return
            # If no customer has phone, skip test
            pytest.skip("No customers with phone numbers in database")

    async def test_create_customer(self, client: AsyncClient):
        """Test POST /api/v1/customers."""
        import random

        # Generate a unique 10-digit phone number
        unique_num = random.randint(1000000000, 9999999999)
        customer_data = {
            "name": "Test Customer",
            "email": f"test_{unique_num}@example.com",
            "phone": f"+1{unique_num}",
        }
        response = await client.post("/api/v1/customers", json=customer_data)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == customer_data["email"]
        assert "id" in data

        # Clean up - delete the created customer
        customer_id = data["id"]
        await client.delete(f"/api/v1/customers/{customer_id}")

    async def test_update_customer(self, client: AsyncClient):
        """Test PUT /api/v1/customers/{customer_id}."""
        # Get a customer first
        list_response = await client.get("/api/v1/customers?limit=1")
        if list_response.json():
            customer_id = list_response.json()[0]["id"]
            update_data = {"name": "Updated Name"}
            response = await client.put(f"/api/v1/customers/{customer_id}", json=update_data)
            assert response.status_code == 200
            assert response.json()["name"] == "Updated Name"

    async def test_delete_customer(self, client: AsyncClient):
        """Test DELETE /api/v1/customers/{customer_id}."""
        import random

        unique_num = random.randint(1000000000, 9999999999)
        # Create a customer to delete
        customer_data = {
            "name": "Delete Test",
            "email": f"delete_{unique_num}@example.com",
            "phone": f"+1{unique_num}",
        }
        create_response = await client.post("/api/v1/customers", json=customer_data)
        customer_id = create_response.json()["id"]

        # Delete it
        response = await client.delete(f"/api/v1/customers/{customer_id}")
        assert response.status_code == 204

        # Verify it's gone
        get_response = await client.get(f"/api/v1/customers/{customer_id}")
        assert get_response.status_code == 404
