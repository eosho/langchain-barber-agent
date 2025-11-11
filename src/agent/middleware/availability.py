"""Availability checking middleware for agents."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Annotated

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

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


class AvailabilitySlot(TypedDict):
    """Time slot information structure."""

    time: str
    """Time slot start time (HH:MM format)."""

    duration: str
    """Time slot duration range (e.g., '14:00 - 14:30')."""

    available: bool
    """Whether the slot is available for booking."""


class AvailabilityInfo(TypedDict):
    """Availability information structure."""

    date: str
    """Date of availability check (YYYY-MM-DD format)."""

    available_slots: list[AvailabilitySlot]
    """List of available time slots."""

    total_available: int
    """Total number of available slots."""


class AvailabilityState(AgentState):
    """State schema for availability checking middleware."""

    availability_info: Annotated[NotRequired[AvailabilityInfo], OmitFromInput]
    """Latest availability check results."""


AVAILABILITY_TOOL_DESCRIPTION = """Check available appointment time slots for booking.

Use this tool when:
- Customer asks "what times are available?"
- Need to check availability for a specific date and service
- Customer mentions a preferred stylist for the appointment
- Planning to create a booking

Required parameters:
- date: Date in YYYY-MM-DD format
- service_id: ID of the service from service catalog

Optional parameters:
- preferred_stylist: Name of preferred barber/stylist

The availability information is automatically stored in state for booking operations."""


AVAILABILITY_SYSTEM_PROMPT = """## `check_availability`

You have access to the `check_availability` tool to find available appointment time slots.
Use this tool when customers ask about available times or before creating a booking.

The tool requires:
- date: Date in YYYY-MM-DD format (must be today or future date)
- service_id: Service ID from the service catalog
- preferred_stylist: (optional) Name of preferred barber

Availability results are automatically stored in state for use in booking creation."""


def _format_availability(availability_data: dict) -> str:
    """Format availability data for LLM consumption.

    Args:
        availability_data: Availability dictionary with slots information.

    Returns:
        Formatted availability information string.
    """
    return json.dumps(availability_data, indent=2)


class AvailabilityMiddleware(AgentMiddleware):
    """Middleware that provides appointment availability checking with state management.

    This middleware adds a `check_availability` tool that allows agents to check available
    time slots for appointments. Availability information is stored in state for booking operations.

    Example:
        ```python
        from langchain.agents.middleware.availability import AvailabilityMiddleware
        from langchain.agents import create_agent

        agent = create_agent(
            "openai:gpt-4o",
            middleware=[AvailabilityMiddleware()]
        )

        result = await agent.invoke({
            "messages": [HumanMessage("What times are available tomorrow for a haircut?")]
        })

        print(result["availability_info"]["date"])  # Date checked
        print(result["availability_info"]["total_available"])  # Number of slots
        ```

    Args:
        system_prompt: Custom system prompt to guide the agent on using the tool.
        tool_description: Custom description for the check_availability tool.
    """

    state_schema = AvailabilityState

    def __init__(
        self,
        *,
        system_prompt: str = AVAILABILITY_SYSTEM_PROMPT,
        tool_description: str = AVAILABILITY_TOOL_DESCRIPTION,
    ) -> None:
        """Initialize the AvailabilityMiddleware with optional custom prompts.

        Args:
            system_prompt: Custom system prompt to guide the agent on using the tool.
            tool_description: Custom description for the check_availability tool.
        """
        super().__init__()
        self.system_prompt = system_prompt
        self.tool_description = tool_description

        @tool(description=self.tool_description)
        async def check_availability(
            date: str,
            service_id: str,
            preferred_stylist: str,
            tool_call_id: Annotated[str, InjectedToolCallId],
        ) -> Command:
            """Check available appointment time slots."""
            try:
                # Validate date format
                try:
                    check_date = datetime.strptime(date, "%Y-%m-%d").date()
                except ValueError:
                    error_msg = "Error: Invalid date format. Please use YYYY-MM-DD format."
                    return Command(
                        update={"messages": [ToolMessage(error_msg, tool_call_id=tool_call_id)]}
                    )

                # Validate date is not in the past
                today = datetime.now().date()
                if check_date < today:
                    error_msg = (
                        f"Error: Date {date} is in the past. Please choose today or a future date."
                    )
                    return Command(
                        update={"messages": [ToolMessage(error_msg, tool_call_id=tool_call_id)]}
                    )

                # Build API request
                api_url = (
                    f"http://{settings.api_host}:{settings.api_port}/api/v1/bookings/availability/"
                )
                payload: dict = {
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
                    message = f"No available time slots for {check_date.strftime('%A, %B %d, %Y')}"
                    return Command(
                        update={"messages": [ToolMessage(message, tool_call_id=tool_call_id)]}
                    )

                # Format response
                slot_list: list[AvailabilitySlot] = []
                for slot in slots:
                    slot_info: AvailabilitySlot = {
                        "time": slot["start_time"],
                        "duration": f"{slot['start_time']} - {slot['end_time']}",
                        "available": slot["available"],
                    }
                    slot_list.append(slot_info)

                availability_info: AvailabilityInfo = {
                    "date": date,
                    "available_slots": slot_list,
                    "total_available": len([s for s in slot_list if s["available"]]),
                }

                formatted = _format_availability(availability_info)  # type: ignore[arg-type]

                return Command(
                    update={
                        "availability_info": availability_info,
                        "messages": [ToolMessage(formatted, tool_call_id=tool_call_id)],
                    }
                )

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    error_msg = f"Error: Service with ID {service_id} not found"
                else:
                    error_msg = (
                        f"Error checking availability: API returned {e.response.status_code}"
                    )
                return Command(
                    update={"messages": [ToolMessage(error_msg, tool_call_id=tool_call_id)]}
                )
            except httpx.RequestError as e:
                error_msg = f"Error connecting to API: {str(e)}"
                return Command(
                    update={"messages": [ToolMessage(error_msg, tool_call_id=tool_call_id)]}
                )
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                return Command(
                    update={"messages": [ToolMessage(error_msg, tool_call_id=tool_call_id)]}
                )

        self.tools = [check_availability]

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
