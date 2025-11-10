"""Availability checking tools for the availability sub-agent.

This module provides tools for checking available appointment time slots
and helping customers find suitable booking times.
"""

import json
from datetime import datetime, timedelta
from typing import Any

import httpx
from langchain.tools import tool
from pydantic import BaseModel, Field, field_validator

from src.core.config import get_settings

settings = get_settings()


class AvailabilityInput(BaseModel):
    """Input schema for availability checker with validation.

    Attributes:
        date: Date to check in YYYY-MM-DD format.
        service_id: Service ID to check availability for.
        preferred_stylist: Optional preferred stylist name.
    """

    date: str = Field(
        description="Date to check in YYYY-MM-DD format",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    service_id: str = Field(
        description="Service ID to check availability for (UUID)",
        min_length=1,
    )
    preferred_stylist: str | None = Field(
        default=None,
        description="Optional preferred stylist name",
        max_length=100,
    )

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        """Validate date format and ensure it's not in the past."""
        try:
            check_date = datetime.strptime(v, "%Y-%m-%d").date()
        except ValueError as e:
            raise ValueError(f"Invalid date format. Use YYYY-MM-DD: {e}") from e

        # Check if date is in the past
        if check_date < datetime.now().date():
            raise ValueError("Cannot check availability for past dates")

        # Check if date is too far in advance
        max_date = datetime.now().date() + timedelta(days=settings.booking_advance_days)
        if check_date > max_date:
            raise ValueError(f"Can only book up to {settings.booking_advance_days} days in advance")

        return v


@tool("check_availability", args_schema=AvailabilityInput)
async def check_availability(
    date: str,
    service_id: str,
    preferred_stylist: str | None = None,
) -> str:
    """Check available time slots for a service on a specific date.

    Use this when a customer asks about availability or wants to book an appointment.
    Validates date format and booking policies before checking availability.

    Args:
        date: Date to check in YYYY-MM-DD format.
        service_id: Service ID to check availability for.
        preferred_stylist: Optional preferred stylist name.

    Returns:
        JSON string with available time slots or error message.

    Example:
        >>> result = await check_availability(
        ...     date="2025-11-15",
        ...     service_id=2,
        ...     preferred_stylist="Jane"
        ... )
        >>> print(result)
        {"date": "2025-11-15", "available_slots": [...], "total_available": 5}
    """
    try:
        # Validation already done by Pydantic schema
        check_date = datetime.strptime(date, "%Y-%m-%d").date()

        # Build API URL
        api_url = f"http://{settings.api_host}:{settings.api_port}/api/v1/bookings/availability/"

        payload: dict[str, Any] = {
            "service_id": service_id,
            "date": date,
        }

        if preferred_stylist:
            payload["preferred_stylist"] = preferred_stylist

        # Make HTTP request
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(api_url, json=payload)
            response.raise_for_status()
            slots = response.json()

        if not slots:
            return f"No available time slots for {check_date.strftime('%A, %B %d, %Y')}"

        # Format response
        slot_list = []
        for slot in slots:
            slot_info = {
                "time": slot["start_time"],
                "duration": f"{slot['start_time']} - {slot['end_time']}",
                "available": slot["available"],
            }
            slot_list.append(slot_info)

        return json.dumps(
            {
                "date": date,
                "available_slots": slot_list,
                "total_available": len([s for s in slot_list if s["available"]]),
            },
            indent=2,
        )

    except ValueError:
        return "Error: Invalid date format. Please use YYYY-MM-DD format."
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Error: Service with ID {service_id} not found"
        return f"Error checking availability: API returned {e.response.status_code}"
    except httpx.RequestError as e:
        return f"Error connecting to API: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


def get_availability_tools() -> list[Any]:
    """Get all availability checking tools.

    Returns a list of LangChain tools for checking appointment availability,
    time slots, and stylist schedules.

    Returns:
        List of availability checker tools ready for agent registration.

    Example:
        >>> tools = get_availability_tools()
        >>> llm_with_tools = llm.bind_tools(tools)
    """
    return [
        check_availability,
    ]
