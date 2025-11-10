"""Integration tests for Bookings API endpoints."""

from datetime import datetime, timedelta

from httpx import AsyncClient


class TestBookingsAPI:
    """Test booking CRUD and availability endpoints."""

    async def test_list_bookings(self, client: AsyncClient):
        """Test GET /api/v1/bookings."""
        response = await client.get("/api/v1/bookings")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_list_bookings_with_filters(self, client: AsyncClient):
        """Test GET /api/v1/bookings with filters."""
        # Get a customer first
        customer_response = await client.get("/api/v1/customers?limit=1")
        if customer_response.json():
            customer_id = customer_response.json()[0]["id"]
            response = await client.get(f"/api/v1/bookings?customer_id={customer_id}")
            assert response.status_code == 200
            assert isinstance(response.json(), list)

    async def test_get_booking(self, client: AsyncClient):
        """Test GET /api/v1/bookings/{booking_id}."""
        # Get a booking first
        list_response = await client.get("/api/v1/bookings?limit=1")
        if list_response.json():
            booking_id = list_response.json()[0]["id"]
            response = await client.get(f"/api/v1/bookings/{booking_id}")
            assert response.status_code == 200
            assert response.json()["id"] == booking_id

    async def test_get_booking_not_found(self, client: AsyncClient):
        """Test GET /api/v1/bookings/{booking_id} with invalid ID."""
        response = await client.get("/api/v1/bookings/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    async def test_create_booking(self, client: AsyncClient):
        """Test POST /api/v1/bookings."""
        import random

        # Get customer and service
        customer_response = await client.get("/api/v1/customers?limit=1")
        service_response = await client.get("/api/v1/services?limit=1")

        if customer_response.json() and service_response.json():
            # Use a distant future date with random hour to avoid conflicts
            future_date = datetime.now() + timedelta(days=365)
            # Random hour between 9 AM and 3 PM
            random_hour = random.randint(9, 15)
            future_date = future_date.replace(hour=random_hour, minute=0, second=0, microsecond=0)

            booking_data = {
                "customer_id": customer_response.json()[0]["id"],
                "service_id": service_response.json()[0]["id"],
                "start_time": future_date.isoformat(),
                "stylist_name": "Test Barber",
                "notes": "Test booking",
            }
            response = await client.post("/api/v1/bookings", json=booking_data)
            assert response.status_code == 201
            data = response.json()
            assert data["customer_id"] == booking_data["customer_id"]
            assert "id" in data

            # Clean up - cancel the created booking
            booking_id = data["id"]
            await client.delete(f"/api/v1/bookings/{booking_id}")

    async def test_update_booking(self, client: AsyncClient):
        """Test PUT /api/v1/bookings/{booking_id}."""
        # Get a booking first
        list_response = await client.get("/api/v1/bookings?limit=1")
        if list_response.json():
            booking_id = list_response.json()[0]["id"]
            update_data = {"notes": "Updated notes via test"}
            response = await client.put(f"/api/v1/bookings/{booking_id}", json=update_data)
            assert response.status_code == 200
            assert response.json()["notes"] == "Updated notes via test"

    async def test_cancel_booking(self, client: AsyncClient):
        """Test DELETE /api/v1/bookings/{booking_id} (cancel via soft delete)."""
        # Create a booking to cancel
        customer_response = await client.get("/api/v1/customers?limit=1")
        service_response = await client.get("/api/v1/services?limit=1")

        if customer_response.json() and service_response.json():
            # Use a far future date
            future_date = datetime.now() + timedelta(days=60)
            booking_data = {
                "customer_id": customer_response.json()[0]["id"],
                "service_id": service_response.json()[0]["id"],
                "start_time": future_date.isoformat(),
                "stylist_name": "Test Barber",
            }
            create_response = await client.post("/api/v1/bookings", json=booking_data)
            if create_response.status_code == 201:
                booking_id = create_response.json()["id"]

                # Cancel it (DELETE sets status to 'cancelled')
                response = await client.delete(f"/api/v1/bookings/{booking_id}")
                assert response.status_code == 204  # DELETE returns 204 No Content

    async def test_check_availability(self, client: AsyncClient):
        """Test POST /api/v1/bookings/availability/."""
        service_response = await client.get("/api/v1/services?limit=1")
        if service_response.json():
            # Check availability for a future date
            future_date = datetime.now() + timedelta(days=90)
            availability_data = {
                "service_id": service_response.json()[0]["id"],
                "date": future_date.strftime("%Y-%m-%d"),
            }
            response = await client.post("/api/v1/bookings/availability/", json=availability_data)
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)  # Returns list of time slots
            if data:  # If there are slots
                assert "start_time" in data[0]
                assert "available" in data[0]
