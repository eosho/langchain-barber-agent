"""Booking management middleware for agents."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Annotated

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from langchain_core.messages import ToolMessage

from typing import NotRequired

import httpx
from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ModelCallResult,
    ModelRequest,
    ModelResponse,
    OmitFromInput,
)
from langchain.tools import InjectedToolCallId
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.types import Command
from typing_extensions import TypedDict

from src.core.config import get_settings

settings = get_settings()


class BookingInfo(TypedDict):
    """Booking information structure."""

    booking_id: str
    """Booking ID (UUID)."""

    customer_id: str
    """Customer ID (UUID)."""

    service_id: str
    """Service ID (UUID)."""

    barber_id: str
    """Barber/stylist ID (UUID)."""

    barber_name: str
    """Barber/stylist name."""

    booking_date: str
    """Booking date in YYYY-MM-DD format."""

    booking_time: str
    """Booking time in HH:MM format."""

    booking_status: str
    """Booking status (scheduled, confirmed, cancelled, etc.)."""

    booking_notes: str
    """Additional notes for the booking."""


class BookingState(AgentState):
    """State schema for booking middleware."""

    booking_info: Annotated[NotRequired[BookingInfo], OmitFromInput]
    """Currently active booking information."""


BOOKING_TOOL_DESCRIPTION_CREATE = """Create a new booking appointment.

Use this when a customer wants to book an appointment. Validates all inputs
before creating the booking. Updates agent state with booking details.

Required information:
- customer_id: From customer lookup
- service_id: From service catalog
- date: Booking date (YYYY-MM-DD)
- time: Booking time (HH:MM, 24-hour format)
- stylist_name: Name of the barber/stylist
- notes: Optional notes (can be empty string)"""


BOOKING_TOOL_DESCRIPTION_CANCEL = """Cancel an existing booking appointment.

Use this when a customer wants to cancel their appointment.
Updates agent state with cancellation status.

Required information:
- booking_id: The ID of the booking to cancel"""


BOOKING_TOOL_DESCRIPTION_MODIFY = """Modify an existing booking appointment.

Use this when a customer wants to change their appointment time, date, or stylist.
At least one field must be provided to modify. Updates agent state with changes.

Required information:
- booking_id: The ID of the booking to modify
- date: New booking date (optional)
- time: New booking time (optional)
- stylist_name: New stylist name (optional)
- notes: Updated notes (optional)"""


BOOKING_TOOL_DESCRIPTION_LOOKUP = """Look up bookings for a customer.

Use this to view existing bookings for a customer.

Required information:
- customer_id: The customer ID to lookup bookings for"""


BOOKING_SYSTEM_PROMPT = """## Booking Tools

You have access to booking management tools:
- `create_booking`: Book a new appointment
- `cancel_booking`: Cancel an existing appointment
- `modify_booking`: Change appointment details
- `lookup_bookings`: View customer's bookings

When a booking is successfully created, modified, or cancelled, the booking information
is automatically stored in the state for reference in subsequent operations."""


def _format_booking(booking: dict, stylist_name: str = "") -> str:
    """Format booking data for LLM consumption.

    Args:
        booking: Booking data dictionary from API.
        stylist_name: Stylist name (if not in booking dict).

    Returns:
        Formatted booking information string.
    """
    return json.dumps(
        {
            "booking_id": booking.get("id"),
            "customer_id": booking.get("customer_id"),
            "service_id": booking.get("service_id"),
            "start_time": booking.get("start_time"),
            "end_time": booking.get("end_time"),
            "stylist": stylist_name or booking.get("barber", {}).get("name", "N/A"),
            "status": booking.get("status"),
            "notes": booking.get("notes", ""),
        },
        indent=2,
    )


class BookingMiddleware(AgentMiddleware):
    """Middleware that provides booking management capabilities with state management.

    This middleware adds booking tools (create, cancel, modify, lookup) that allow agents
    to manage appointments. When a booking is created or modified, its information is
    automatically stored in the agent's state for use in subsequent operations.

    Example:
        ```python
        from langchain.agents.middleware.booking import BookingMiddleware
        from langchain.agents import create_agent

        agent = create_agent(
            "openai:gpt-4o",
            middleware=[BookingMiddleware()]
        )

        # Agent now has access to booking tools and booking state tracking
        result = await agent.invoke({
            "messages": [HumanMessage("Book a haircut for tomorrow at 2pm")]
        })

        print(result["booking_info"]["booking_id"])  # Created booking ID
        print(result["booking_info"]["booking_status"])  # Booking status
        ```

    Args:
        system_prompt: Custom system prompt to guide the agent on using the tools.
            If not provided, uses the default `BOOKING_SYSTEM_PROMPT`.
    """

    state_schema = BookingState

    def __init__(
        self,
        *,
        system_prompt: str = BOOKING_SYSTEM_PROMPT,
    ) -> None:
        """Initialize the BookingMiddleware with optional custom prompt.

        Args:
            system_prompt: Custom system prompt to guide the agent on using the tools.
        """
        super().__init__()
        self.system_prompt = system_prompt

        # Create booking tool
        @tool(description=BOOKING_TOOL_DESCRIPTION_CREATE)
        async def create_booking(
            customer_id: str,
            service_id: str,
            date: str,
            time: str,
            stylist_name: str,
            notes: str,
            tool_call_id: Annotated[str, InjectedToolCallId],
        ) -> Command:
            """Create a new booking and update state."""
            try:
                base_url = f"http://{settings.api_host}:{settings.api_port}/api/v1"

                # Look up barber by name
                barbers_url = f"{base_url}/barbers/"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    barbers_response = await client.get(barbers_url)
                    barbers_response.raise_for_status()
                    barbers = barbers_response.json()

                barber = next(
                    (b for b in barbers if b["name"].lower() == stylist_name.lower()), None
                )
                if not barber:
                    error_msg = json.dumps(
                        {"error": f"Barber '{stylist_name}' not found"}, indent=2
                    )
                    return Command(
                        update={"messages": [ToolMessage(error_msg, tool_call_id=tool_call_id)]}
                    )

                barber_id = barber["id"]

                # Create booking via API
                bookings_url = f"{base_url}/bookings/"
                start_time = f"{date}T{time}:00"
                payload = {
                    "customer_id": customer_id,
                    "service_id": service_id,
                    "barber_id": barber_id,
                    "start_time": start_time,
                    "notes": notes or "",
                }

                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(bookings_url, json=payload)
                    response.raise_for_status()
                    booking = response.json()

                # Create booking info for state
                booking_info: BookingInfo = {
                    "booking_id": booking["id"],
                    "customer_id": customer_id,
                    "service_id": service_id,
                    "barber_id": barber_id,
                    "barber_name": stylist_name,
                    "booking_date": date,
                    "booking_time": time,
                    "booking_status": booking["status"],
                    "booking_notes": notes or "",
                }

                formatted = _format_booking(booking, stylist_name)
                return Command(
                    update={
                        "booking_info": booking_info,
                        "messages": [ToolMessage(formatted, tool_call_id=tool_call_id)],
                    }
                )

            except httpx.HTTPStatusError as e:
                error_content = json.dumps(
                    {"error": f"API returned {e.response.status_code}"}, indent=2
                )
                return Command(
                    update={"messages": [ToolMessage(error_content, tool_call_id=tool_call_id)]}
                )
            except httpx.RequestError as e:
                error_content = json.dumps(
                    {"error": f"Error connecting to API: {str(e)}"}, indent=2
                )
                return Command(
                    update={"messages": [ToolMessage(error_content, tool_call_id=tool_call_id)]}
                )
            except Exception as e:
                error_content = json.dumps({"error": f"Unexpected error: {str(e)}"}, indent=2)
                return Command(
                    update={"messages": [ToolMessage(error_content, tool_call_id=tool_call_id)]}
                )

        # Cancel booking tool
        @tool(description=BOOKING_TOOL_DESCRIPTION_CANCEL)
        async def cancel_booking(
            booking_id: str,
            tool_call_id: Annotated[str, InjectedToolCallId],
        ) -> Command:
            """Cancel a booking and update state."""
            try:
                base_url = f"http://{settings.api_host}:{settings.api_port}/api/v1/bookings/"

                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.delete(f"{base_url}{booking_id}")
                    response.raise_for_status()

                success_message = json.dumps(
                    {
                        "status": "cancelled",
                        "booking_id": booking_id,
                        "message": "Booking has been cancelled successfully",
                    },
                    indent=2,
                )

                return Command(
                    update={
                        "booking_info": {
                            "booking_id": booking_id,
                            "booking_status": "cancelled",
                        },
                        "messages": [ToolMessage(success_message, tool_call_id=tool_call_id)],
                    }
                )

            except httpx.HTTPStatusError as e:
                error_content = json.dumps(
                    {"error": f"API returned {e.response.status_code}"}, indent=2
                )
                if e.response.status_code == 404:
                    error_content = json.dumps(
                        {"error": f"Booking {booking_id} not found"}, indent=2
                    )
                return Command(
                    update={"messages": [ToolMessage(error_content, tool_call_id=tool_call_id)]}
                )
            except httpx.RequestError as e:
                error_content = json.dumps(
                    {"error": f"Error connecting to API: {str(e)}"}, indent=2
                )
                return Command(
                    update={"messages": [ToolMessage(error_content, tool_call_id=tool_call_id)]}
                )
            except Exception as e:
                error_content = json.dumps({"error": f"Unexpected error: {str(e)}"}, indent=2)
                return Command(
                    update={"messages": [ToolMessage(error_content, tool_call_id=tool_call_id)]}
                )

        # Modify booking tool
        @tool(description=BOOKING_TOOL_DESCRIPTION_MODIFY)
        async def modify_booking(
            booking_id: str,
            date: str,
            time: str,
            stylist_name: str,
            notes: str,
            tool_call_id: Annotated[str, InjectedToolCallId],
        ) -> Command:
            """Modify a booking and update state."""
            try:
                base_url = f"http://{settings.api_host}:{settings.api_port}/api/v1/bookings/"
                payload = {}

                # Combine date and time into start_time if either is provided
                if date or time:
                    # Get current booking to fill in missing date/time
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        get_response = await client.get(f"{base_url}{booking_id}")
                        get_response.raise_for_status()
                        current_booking = get_response.json()

                    booking_date = date if date else current_booking["start_time"][:10]
                    booking_time = time if time else current_booking["start_time"][11:16]
                    payload["start_time"] = f"{booking_date}T{booking_time}:00"

                # Look up barber_id if stylist_name is provided
                barber_id = None
                if stylist_name:
                    barbers_url = f"http://{settings.api_host}:{settings.api_port}/api/v1/barbers/"
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        barbers_response = await client.get(barbers_url)
                        barbers_response.raise_for_status()
                        barbers = barbers_response.json()

                    barber = next(
                        (b for b in barbers if b["name"].lower() == stylist_name.lower()), None
                    )
                    if not barber:
                        error_msg = json.dumps(
                            {"error": f"Barber '{stylist_name}' not found"}, indent=2
                        )
                        return Command(
                            update={"messages": [ToolMessage(error_msg, tool_call_id=tool_call_id)]}
                        )
                    barber_id = barber["id"]
                    payload["barber_id"] = barber_id

                if notes:
                    payload["notes"] = notes

                if not payload:
                    error_msg = json.dumps(
                        {"error": "No fields provided for modification"}, indent=2
                    )
                    return Command(
                        update={"messages": [ToolMessage(error_msg, tool_call_id=tool_call_id)]}
                    )

                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.put(f"{base_url}{booking_id}", json=payload)
                    response.raise_for_status()
                    booking = response.json()

                # Extract updated values
                updated_date = booking["start_time"][:10]
                updated_time = booking["start_time"][11:16]
                updated_stylist = booking.get("barber", {}).get("name", stylist_name or "N/A")

                success_message = json.dumps(
                    {
                        "status": "modified",
                        "booking_id": booking["id"],
                        "date": updated_date,
                        "time": updated_time,
                        "stylist": updated_stylist,
                    },
                    indent=2,
                )

                # Build state updates based on what changed
                booking_info: BookingInfo = {
                    "booking_id": booking_id,
                    "booking_date": updated_date if date else "",
                    "booking_time": updated_time if time else "",
                    "barber_name": updated_stylist if stylist_name else "",
                    "barber_id": barber_id or "",
                    "booking_notes": notes or "",
                    "booking_status": booking.get("status", ""),
                    "customer_id": booking.get("customer_id", ""),
                    "service_id": booking.get("service_id", ""),
                }

                return Command(
                    update={
                        "booking_info": booking_info,
                        "messages": [ToolMessage(success_message, tool_call_id=tool_call_id)],
                    }
                )

            except httpx.HTTPStatusError as e:
                error_content = json.dumps(
                    {"error": f"Error modifying booking: API returned {e.response.status_code}"},
                    indent=2,
                )
                if e.response.status_code == 404:
                    error_content = json.dumps(
                        {"error": f"Booking {booking_id} not found"}, indent=2
                    )
                return Command(
                    update={"messages": [ToolMessage(error_content, tool_call_id=tool_call_id)]}
                )
            except httpx.RequestError as e:
                error_content = json.dumps(
                    {"error": f"Error connecting to API: {str(e)}"}, indent=2
                )
                return Command(
                    update={"messages": [ToolMessage(error_content, tool_call_id=tool_call_id)]}
                )
            except Exception as e:
                error_content = json.dumps({"error": f"Unexpected error: {str(e)}"}, indent=2)
                return Command(
                    update={"messages": [ToolMessage(error_content, tool_call_id=tool_call_id)]}
                )

        # Lookup bookings tool
        @tool(description=BOOKING_TOOL_DESCRIPTION_LOOKUP)
        async def lookup_bookings(
            customer_id: str,
            tool_call_id: Annotated[str, InjectedToolCallId],
        ) -> Command:
            """Look up bookings for a customer."""
            try:
                base_url = f"http://{settings.api_host}:{settings.api_port}/api/v1/bookings/"
                params = {"customer_id": customer_id}

                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(base_url, params=params)
                    response.raise_for_status()
                    bookings = response.json()

                result = json.dumps({"bookings": bookings, "count": len(bookings)}, indent=2)
                return Command(
                    update={"messages": [ToolMessage(result, tool_call_id=tool_call_id)]}
                )

            except httpx.HTTPStatusError as e:
                error_content = json.dumps(
                    {"error": f"API returned {e.response.status_code}"}, indent=2
                )
                return Command(
                    update={"messages": [ToolMessage(error_content, tool_call_id=tool_call_id)]}
                )
            except httpx.RequestError as e:
                error_content = json.dumps(
                    {"error": f"Error connecting to API: {str(e)}"}, indent=2
                )
                return Command(
                    update={"messages": [ToolMessage(error_content, tool_call_id=tool_call_id)]}
                )
            except Exception as e:
                error_content = json.dumps({"error": f"Unexpected error: {str(e)}"}, indent=2)
                return Command(
                    update={"messages": [ToolMessage(error_content, tool_call_id=tool_call_id)]}
                )

        self.tools = [create_booking, cancel_booking, modify_booking, lookup_bookings]

    def wrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]
    ) -> ModelCallResult:
        """Update the system prompt to include the service catalog system prompt."""
        request.system_prompt = (
            request.system_prompt + "\n\n" + self.system_prompt
            if request.system_prompt
            else self.system_prompt
        )
        return handler(request)

    async def awrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], Awaitable[ModelResponse]]
    ) -> ModelCallResult:
        """Update the system prompt to include the service catalog system prompt (async)."""
        request.system_prompt = (
            request.system_prompt + "\n\n" + self.system_prompt
            if request.system_prompt
            else self.system_prompt
        )
        return await handler(request)
