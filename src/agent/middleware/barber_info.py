"""Barber information middleware for agents."""

from __future__ import annotations

import json
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


class BarberInfo(TypedDict):
    """Barber information structure."""

    barber_id: str
    """Barber ID (UUID)."""

    name: str
    """Barber full name."""

    email: str
    """Barber email address."""

    phone: str
    """Barber phone number."""

    specialties: list[str]
    """List of barber specialties."""

    is_active: bool
    """Whether the barber is currently active."""


class BarberInfoState(AgentState):
    """State schema for barber information middleware."""

    selected_barber: Annotated[NotRequired[BarberInfo], OmitFromInput]
    """Currently selected barber information."""


BARBER_INFO_TOOL_DESCRIPTION = """Access barber information and specialties.

Use these tools when:
- Customer asks about barbers or stylists
- Customer mentions a barber by name
- Customer asks about barber specialties (fade, beard trim, etc.)

Tools available:
- list_barbers: Get all active barbers
- get_barber_by_name: Look up specific barber
- find_barbers_by_specialty: Search by specialty

Barber information is automatically stored in state for booking operations.

Note: To check available time slots, use the check_availability tool from the availability middleware."""


BARBER_INFO_SYSTEM_PROMPT = """## Barber Information Tools

You have access to multiple tools for retrieving barber information:

- `list_barbers`: Returns all active barbers with their details and specialties
- `get_barber_by_name`: Look up a specific barber by their name
- `find_barbers_by_specialty`: Find barbers who specialize in specific services

When a barber is referenced during booking, the barber information is automatically stored
in the state for use in subsequent tool calls.

To check available time slots for appointments, use the `check_availability` tool
from the availability middleware instead."""


def _format_barbers(barbers: list[dict], found: bool, count: int) -> str:
    """Format barbers data for LLM consumption.

    Args:
        barbers: List of barber dictionaries from API.
        found: Whether any barbers were found.
        count: Total number of barbers found.

    Returns:
        Formatted barbers information string.
    """
    formatted_barbers = [
        {
            "id": b.get("id"),
            "name": b.get("name"),
            "email": b.get("email"),
            "phone": b.get("phone"),
            "specialties": b.get("specialties", []),
            "is_active": b.get("is_active", True),
        }
        for b in barbers
    ]

    return json.dumps(
        {
            "found": found,
            "count": count,
            "barbers": formatted_barbers,
        },
        indent=2,
    )


class BarberInfoMiddleware(AgentMiddleware):
    """Middleware that provides barber information tools with state management.

    This middleware adds tools for looking up barbers and their specialties.
    Barber information is stored in state for booking operations.

    For checking available time slots, use the AvailabilityMiddleware instead,
    which provides the check_availability tool.

    Example:
        ```python
        from langchain.agents.middleware.barber_info import BarberInfoMiddleware
        from langchain.agents import create_agent

        agent = create_agent(
            "openai:gpt-4o",
            middleware=[BarberInfoMiddleware()]
        )

        result = await agent.invoke({
            "messages": [HumanMessage("Which barbers specialize in fades?")]
        })

        print(result["selected_barber"]["name"])  # Barber name
        print(result["selected_barber"]["specialties"])  # List of specialties
        ```

    Args:
        system_prompt: Custom system prompt to guide the agent on using the tools.
        tool_description: Custom description for the barber info tools.
    """

    state_schema = BarberInfoState

    def __init__(
        self,
        *,
        system_prompt: str = BARBER_INFO_SYSTEM_PROMPT,
        tool_description: str = BARBER_INFO_TOOL_DESCRIPTION,
    ) -> None:
        """Initialize the BarberInfoMiddleware with optional custom prompts.

        Args:
            system_prompt: Custom system prompt to guide the agent on using the tools.
            tool_description: Custom description for the barber info tools.
        """
        super().__init__()
        self.system_prompt = system_prompt
        self.tool_description = tool_description

        @tool(description="List all active barbers with their details and specialties.")
        async def list_barbers(
            tool_call_id: Annotated[str, InjectedToolCallId],
        ) -> Command:
            """List all active barbers."""
            try:
                base_url = f"http://{settings.api_host}:{settings.api_port}/api/v1/barbers/"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(base_url)
                    response.raise_for_status()
                    barbers = response.json()

                # Filter to active barbers only
                active_barbers = [b for b in barbers if b.get("is_active", True)]
                formatted = _format_barbers(
                    active_barbers, len(active_barbers) > 0, len(active_barbers)
                )

                return Command(
                    update={"messages": [ToolMessage(formatted, tool_call_id=tool_call_id)]}
                )

            except httpx.HTTPStatusError as e:
                error_msg = f"Error fetching barbers: {e.response.status_code}"
                return Command(
                    update={"messages": [ToolMessage(error_msg, tool_call_id=tool_call_id)]}
                )
            except httpx.RequestError as e:
                error_msg = f"Network error while fetching barbers: {str(e)}"
                return Command(
                    update={"messages": [ToolMessage(error_msg, tool_call_id=tool_call_id)]}
                )
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                return Command(
                    update={"messages": [ToolMessage(error_msg, tool_call_id=tool_call_id)]}
                )

        @tool(description="Look up a specific barber by their name.")
        async def get_barber_by_name(
            barber_name: str,
            tool_call_id: Annotated[str, InjectedToolCallId],
        ) -> Command:
            """Get barber details by name."""
            try:
                base_url = f"http://{settings.api_host}:{settings.api_port}/api/v1/barbers/"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(base_url)
                    response.raise_for_status()
                    barbers = response.json()

                # Search for barber by name (case-insensitive partial match)
                search_term = barber_name.lower()
                matching_barbers = [
                    b
                    for b in barbers
                    if search_term in b.get("name", "").lower() and b.get("is_active", True)
                ]

                formatted = _format_barbers(
                    matching_barbers, len(matching_barbers) > 0, len(matching_barbers)
                )

                # If exactly one barber matches, store in state
                update_dict: dict = {
                    "messages": [ToolMessage(formatted, tool_call_id=tool_call_id)]
                }

                if len(matching_barbers) == 1:
                    barber = matching_barbers[0]
                    barber_info: BarberInfo = {
                        "barber_id": barber.get("id"),
                        "name": barber.get("name"),
                        "email": barber.get("email"),
                        "phone": barber.get("phone"),
                        "specialties": barber.get("specialties", []),
                        "is_active": barber.get("is_active", True),
                    }
                    update_dict["selected_barber"] = barber_info

                return Command(update=update_dict)

            except httpx.HTTPStatusError as e:
                error_msg = f"Error fetching barber details: {e.response.status_code}"
                return Command(
                    update={"messages": [ToolMessage(error_msg, tool_call_id=tool_call_id)]}
                )
            except httpx.RequestError as e:
                error_msg = f"Network error while fetching barber details: {str(e)}"
                return Command(
                    update={"messages": [ToolMessage(error_msg, tool_call_id=tool_call_id)]}
                )
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                return Command(
                    update={"messages": [ToolMessage(error_msg, tool_call_id=tool_call_id)]}
                )

        @tool(
            description="Find barbers who specialize in specific services (e.g., fade, beard trim)."
        )
        async def find_barbers_by_specialty(
            specialty: str,
            tool_call_id: Annotated[str, InjectedToolCallId],
        ) -> Command:
            """Find barbers by specialty."""
            try:
                base_url = f"http://{settings.api_host}:{settings.api_port}/api/v1/barbers/"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(base_url)
                    response.raise_for_status()
                    barbers = response.json()

                # Filter barbers by specialty (case-insensitive partial match)
                search_term = specialty.lower()
                matching_barbers = [
                    b
                    for b in barbers
                    if b.get("is_active", True)
                    and any(search_term in s.lower() for s in b.get("specialties", []))
                ]

                formatted = _format_barbers(
                    matching_barbers, len(matching_barbers) > 0, len(matching_barbers)
                )

                return Command(
                    update={"messages": [ToolMessage(formatted, tool_call_id=tool_call_id)]}
                )

            except httpx.HTTPStatusError as e:
                error_msg = f"Error searching barbers by specialty: {e.response.status_code}"
                return Command(
                    update={"messages": [ToolMessage(error_msg, tool_call_id=tool_call_id)]}
                )
            except httpx.RequestError as e:
                error_msg = f"Network error while searching barbers: {str(e)}"
                return Command(
                    update={"messages": [ToolMessage(error_msg, tool_call_id=tool_call_id)]}
                )
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                return Command(
                    update={"messages": [ToolMessage(error_msg, tool_call_id=tool_call_id)]}
                )

        self.tools = [list_barbers, get_barber_by_name, find_barbers_by_specialty]

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
