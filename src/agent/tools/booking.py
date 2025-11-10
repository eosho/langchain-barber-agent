"""Booking management tools for the booking sub-agent.

This module provides tools for creating, modifying, canceling, and looking up
customer appointments.
"""

import json
from datetime import datetime
from typing import Any

import httpx
from langchain.tools import tool
from pydantic import BaseModel, Field, field_validator

from src.core.config import get_settings

settings = get_settings()


class CreateBookingInput(BaseModel):
    """Input schema for creating a booking with validation.

    Attributes:
        customer_id: Customer ID from customer lookup (UUID string).
        service_id: Service ID from services catalog.
        date: Booking date in YYYY-MM-DD format.
        time: Booking time in HH:MM format (24-hour).
        stylist_name: Name of the stylist for the appointment.
        notes: Optional additional notes for the booking.
    """

    customer_id: str = Field(description="Customer ID from customer lookup (UUID)", min_length=1)
    service_id: str = Field(description="Service ID from services catalog (UUID)", min_length=1)
    date: str = Field(
        description="Booking date in YYYY-MM-DD format",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    time: str = Field(
        description="Booking time in HH:MM format (24-hour)",
        pattern=r"^([01]\d|2[0-3]):([0-5]\d)$",
    )
    stylist_name: str = Field(
        description="Name of the stylist for the appointment",
        min_length=1,
        max_length=100,
    )
    notes: str | None = Field(
        default=None,
        description="Optional additional notes for the booking",
        max_length=500,
    )

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        """Validate date format.

        Args:
            v: Date string to validate.

        Returns:
            Validated date string.

        Raises:
            ValueError: If date format is invalid.
        """
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(f"Invalid date format. Use YYYY-MM-DD: {e}") from e
        return v

    @field_validator("time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        """Validate time format.

        Args:
            v: Time string to validate.

        Returns:
            Validated time string.

        Raises:
            ValueError: If time format is invalid.
        """
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError as e:
            raise ValueError(f"Invalid time format. Use HH:MM (24-hour): {e}") from e
        return v


class ModifyBookingInput(BaseModel):
    """Input schema for modifying a booking.

    Attributes:
        booking_id: ID of the booking to modify (UUID string).
        date: New booking date in YYYY-MM-DD format.
        time: New booking time in HH:MM format.
        stylist_name: New stylist name.
        notes: Updated notes.
    """

    booking_id: str = Field(description="ID of the booking to modify (UUID)", min_length=1)
    date: str | None = Field(
        default=None,
        description="New booking date in YYYY-MM-DD format",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    time: str | None = Field(
        default=None,
        description="New booking time in HH:MM format",
        pattern=r"^([01]\d|2[0-3]):([0-5]\d)$",
    )
    stylist_name: str | None = Field(
        default=None,
        description="New stylist name",
        max_length=100,
    )
    notes: str | None = Field(
        default=None,
        description="Updated notes",
        max_length=500,
    )

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str | None) -> str | None:
        """Validate date format if provided.

        Args:
            v: Date string to validate, or None.

        Returns:
            Validated date string or None.

        Raises:
            ValueError: If date format is invalid.
        """
        if v is not None:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError as e:
                raise ValueError(f"Invalid date format. Use YYYY-MM-DD: {e}") from e
        return v

    @field_validator("time")
    @classmethod
    def validate_time(cls, v: str | None) -> str | None:
        """Validate time format if provided.

        Args:
            v: Time string to validate, or None.

        Returns:
            Validated time string or None.

        Raises:
            ValueError: If time format is invalid.
        """
        if v is not None:
            try:
                datetime.strptime(v, "%H:%M")
            except ValueError as e:
                raise ValueError(f"Invalid time format. Use HH:MM (24-hour): {e}") from e
        return v


class CancelBookingInput(BaseModel):
    """Input schema for canceling a booking.

    Attributes:
        booking_id: ID of the booking to cancel (UUID string).
    """

    booking_id: str = Field(description="ID of the booking to cancel (UUID)", min_length=1)


class LookupBookingsInput(BaseModel):
    """Input schema for looking up bookings.

    Attributes:
        customer_id: Customer ID to lookup bookings for (UUID string).
    """

    customer_id: str = Field(
        description="Customer ID to lookup bookings for (UUID)",
        min_length=1,
    )


@tool("create_booking", args_schema=CreateBookingInput)
async def create_booking(
    customer_id: str,
    service_id: str,
    date: str,
    time: str,
    stylist_name: str,
    notes: str | None = None,
) -> str:
    """Create a new booking appointment.

    Use this when a customer wants to book an appointment. Validates all inputs
    before creating the booking.

    Args:
        customer_id: Customer ID from customer lookup.
        service_id: Service ID from services catalog.
        date: Booking date in YYYY-MM-DD format.
        time: Booking time in HH:MM format (24-hour).
        stylist_name: Name of the stylist for the appointment.
        notes: Optional additional notes for the booking.

    Returns:
        JSON string with booking confirmation details or error message.

    Example:
        >>> result = await create_booking(
        ...     customer_id=1,
        ...     service_id=2,
        ...     date="2025-11-15",
        ...     time="14:00",
        ...     stylist_name="Jane"
        ... )
    """
    try:
        # First, lookup barber by name
        barbers_url = f"http://{settings.api_host}:{settings.api_port}/api/v1/barbers/"
        async with httpx.AsyncClient(timeout=10.0) as client:
            barbers_response = await client.get(barbers_url)
            barbers_response.raise_for_status()
            barbers = barbers_response.json()

        # Find barber by name (case-insensitive)
        barber_id = None
        for barber in barbers:
            if barber["name"].lower() == stylist_name.lower():
                barber_id = barber["id"]
                break

        if not barber_id:
            return json.dumps({"error": f"Barber '{stylist_name}' not found"}, indent=2)

        # Combine date and time to create start_time
        start_time_str = f"{date}T{time}:00"

        base_url = f"http://{settings.api_host}:{settings.api_port}/api/v1/bookings/"

        payload = {
            "customer_id": customer_id,
            "service_id": service_id,
            "barber_id": barber_id,
            "start_time": start_time_str,
            "notes": notes or "",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(base_url, json=payload)
            response.raise_for_status()
            booking = response.json()

        return json.dumps(
            {
                "booking_id": booking["id"],
                "customer_id": booking["customer_id"],
                "service_id": booking["service_id"],
                "start_time": booking["start_time"],
                "end_time": booking["end_time"],
                "stylist": stylist_name,
                "status": booking["status"],
            },
            indent=2,
        )

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return "Error: Customer or service not found"
        elif e.response.status_code == 409:
            return "Error: Time slot is not available"
        return f"Error creating booking: API returned {e.response.status_code}"
    except httpx.RequestError as e:
        return f"Error connecting to API: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@tool("modify_booking", args_schema=ModifyBookingInput)
async def modify_booking(
    booking_id: str,
    date: str | None = None,
    time: str | None = None,
    stylist_name: str | None = None,
    notes: str | None = None,
) -> str:
    """Modify an existing booking appointment.

    Use this when a customer wants to change their appointment time, date, or stylist.
    At least one field must be provided to modify.

    Args:
        booking_id: ID of the booking to modify.
        date: New booking date in YYYY-MM-DD format.
        time: New booking time in HH:MM format.
        stylist_name: New stylist name.
        notes: Updated notes.

    Returns:
        JSON string with modification confirmation or error message.

    Example:
        >>> result = await modify_booking(
        ...     booking_id=5,
        ...     date="2025-11-16",
        ...     time="15:00"
        ... )
    """
    try:
        base_url = f"http://{settings.api_host}:{settings.api_port}/api/v1/bookings/"

        payload: dict[str, Any] = {}

        # Combine date and time into start_time if either is provided
        if date or time:
            # If modifying, we need to get current booking to fill in missing date/time
            async with httpx.AsyncClient(timeout=10.0) as client:
                get_response = await client.get(f"{base_url}{booking_id}")
                get_response.raise_for_status()
                current_booking = get_response.json()

            # Use provided date or fall back to current
            booking_date = date if date else current_booking["start_time"][:10]
            # Use provided time or fall back to current
            booking_time = time if time else current_booking["start_time"][11:16]

            # Combine into ISO format datetime
            payload["start_time"] = f"{booking_date}T{booking_time}:00"

        # Look up barber_id if stylist_name is provided
        if stylist_name:
            barbers_url = f"http://{settings.api_host}:{settings.api_port}/api/v1/barbers/"
            async with httpx.AsyncClient(timeout=10.0) as client:
                barbers_response = await client.get(barbers_url)
                barbers_response.raise_for_status()
                barbers = barbers_response.json()

            # Find barber by name
            barber = next((b for b in barbers if b["name"].lower() == stylist_name.lower()), None)
            if not barber:
                return f"Error: Barber '{stylist_name}' not found"
            payload["barber_id"] = barber["id"]

        if notes:
            payload["notes"] = notes

        if not payload:
            return "Error: No fields provided for modification"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.put(f"{base_url}{booking_id}", json=payload)
            response.raise_for_status()
            booking = response.json()

        return json.dumps(
            {
                "status": "modified",
                "booking_id": booking["id"],
                "date": booking["start_time"][:10],
                "time": booking["start_time"][11:16],
                "stylist": booking.get("barber", {}).get("name", "N/A"),
            },
            indent=2,
        )

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Error: Booking {booking_id} not found"
        return f"Error modifying booking: API returned {e.response.status_code} - {e.response.text}"
    except httpx.RequestError as e:
        return f"Error connecting to API: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@tool("cancel_booking", args_schema=CancelBookingInput)
async def cancel_booking(booking_id: str) -> str:
    """Cancel an existing booking appointment.

    Use this when a customer wants to cancel their appointment.

    Args:
        booking_id: ID of the booking to cancel.

    Returns:
        JSON string with cancellation confirmation or error message.

    Example:
        >>> result = await cancel_booking(booking_id=5)
    """
    try:
        base_url = f"http://{settings.api_host}:{settings.api_port}/api/v1/bookings/"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.delete(f"{base_url}{booking_id}")
            response.raise_for_status()

        return json.dumps(
            {
                "status": "cancelled",
                "booking_id": booking_id,
                "message": "Booking has been cancelled successfully",
            },
            indent=2,
        )

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Error: Booking {booking_id} not found"
        return f"Error cancelling booking: API returned {e.response.status_code}"
    except httpx.RequestError as e:
        return f"Error connecting to API: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@tool("lookup_bookings", args_schema=LookupBookingsInput)
async def lookup_bookings(customer_id: str) -> str:
    """Look up bookings for a customer.

    Use this to view existing bookings. Can filter by customer ID.

    Args:
        customer_id: Customer ID to lookup bookings for.

    Returns:
        JSON string with list of bookings or error message.

    Example:
        >>> result = await lookup_bookings(customer_id=1)
        >>> print(result)
        {"bookings": [{"id": 5, "date": "2025-11-15", ...}]}
    """
    try:
        base_url = f"http://{settings.api_host}:{settings.api_port}/api/v1/bookings/"
        params = {}
        if customer_id:
            params["customer_id"] = customer_id

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(base_url, params=params)
            response.raise_for_status()
            bookings = response.json()

        if not bookings:
            return "No bookings found"

        booking_list = []
        for booking in bookings:
            # Parse datetime to separate date and time
            start_time = booking["start_time"]
            if isinstance(start_time, str):
                # Parse ISO format datetime string
                from datetime import datetime

                dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                date_str = dt.strftime("%Y-%m-%d")
                time_str = dt.strftime("%H:%M")
            else:
                date_str = start_time
                time_str = ""

            booking_info = {
                "id": booking["id"],
                "customer_id": booking["customer_id"],
                "service_id": booking["service_id"],
                "service_name": booking.get("service", {}).get("name", "Unknown"),
                "date": date_str,
                "time": time_str,
                "stylist": booking.get("stylist_name", "Not assigned"),
                "status": booking["status"],
            }
            booking_list.append(booking_info)

        return json.dumps({"bookings": booking_list}, indent=2)

    except httpx.HTTPStatusError as e:
        return f"Error looking up bookings: API returned {e.response.status_code}"
    except httpx.RequestError as e:
        return f"Error connecting to API: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


def get_booking_tools() -> list[Any]:
    """Get all booking-related tools for LLM binding.

    Returns:
        List of LangChain tools for booking operations.

    Example:
        >>> tools = get_booking_tools()
        >>> llm_with_tools = llm.bind_tools(tools)
    """
    return [create_booking, modify_booking, cancel_booking, lookup_bookings]
