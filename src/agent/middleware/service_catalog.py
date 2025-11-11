"""Service catalog middleware for agents."""

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


class ServiceInfo(TypedDict):
    """Service information structure."""

    service_id: str
    """Service ID (UUID)."""

    name: str
    """Service name."""

    category: str
    """Service category."""

    price: str
    """Service price as formatted string."""

    duration_minutes: int
    """Service duration in minutes."""

    description: str
    """Service description."""


class ServiceCatalogState(AgentState):
    """State schema for service catalog middleware."""

    selected_service: Annotated[NotRequired[ServiceInfo], OmitFromInput]
    """Currently selected service information."""


SERVICE_CATALOG_TOOL_DESCRIPTION = """Browse available services with pricing and duration information.

Use this tool when:
- Customer mentions a service type (haircut, fade, beard trim, etc.)
- Customer asks "what services do you have?"
- Need to show pricing and duration for services

This tool will automatically update the agent's state with the selected service information
for use in booking operations."""


SERVICE_CATALOG_SYSTEM_PROMPT = """## `browse_services`

You have access to the `browse_services` tool to search the service catalog.
Use this tool when customers inquire about available services, pricing, or service details.

When a service is referenced during booking, the service information is automatically stored in the state
for use in subsequent tool calls."""


def _format_services(services: list[dict], found: bool, count: int) -> str:
    """Format services data for LLM consumption.

    Args:
        services: List of service dictionaries from API.
        found: Whether any services were found.
        count: Total number of services found.

    Returns:
        Formatted services information string.
    """
    formatted_services = [
        {
            "id": s.get("id"),
            "name": s.get("name"),
            "category": s.get("category"),
            "price": f"${s.get('price', 0):.2f}",
            "duration": f"{s.get('duration_minutes', 0)} minutes",
            "description": s.get("description", ""),
        }
        for s in services
    ]

    return json.dumps(
        {
            "found": found,
            "count": count,
            "services": formatted_services,
        },
        indent=2,
    )


class ServiceCatalogMiddleware(AgentMiddleware):
    """Middleware that provides service catalog browsing with state management.

    This middleware adds a `browse_services` tool that allows agents to search for
    services by name or category. Service information is stored in state for booking operations.

    Example:
        ```python
        from langchain.agents.middleware.service_catalog import ServiceCatalogMiddleware
        from langchain.agents import create_agent

        agent = create_agent(
            "openai:gpt-4o",
            middleware=[ServiceCatalogMiddleware()]
        )

        result = await agent.invoke({
            "messages": [HumanMessage("What haircut services do you offer?")]
        })

        print(result["selected_service"]["name"])  # Service name
        print(result["selected_service"]["price"])  # Service price
        ```

    Args:
        system_prompt: Custom system prompt to guide the agent on using the tool.
        tool_description: Custom description for the browse_services tool.
    """

    state_schema = ServiceCatalogState

    def __init__(
        self,
        *,
        system_prompt: str = SERVICE_CATALOG_SYSTEM_PROMPT,
        tool_description: str = SERVICE_CATALOG_TOOL_DESCRIPTION,
    ) -> None:
        """Initialize the ServiceCatalogMiddleware with optional custom prompts.

        Args:
            system_prompt: Custom system prompt to guide the agent on using the tool.
            tool_description: Custom description for the browse_services tool.
        """
        super().__init__()
        self.system_prompt = system_prompt
        self.tool_description = tool_description

        @tool(description=self.tool_description)
        async def browse_services(
            service_name: str,
            tool_call_id: Annotated[str, InjectedToolCallId],
        ) -> Command:
            """Browse available services and update state."""
            try:
                base_url = f"http://{settings.api_host}:{settings.api_port}/api/v1/services/"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(base_url)
                    response.raise_for_status()
                    services = response.json()

                # Filter to active services only
                active_services = [s for s in services if s.get("is_active", True)]

                # Filter by service_name if provided
                if service_name:
                    search_term = service_name.lower()
                    matching_services = [
                        s
                        for s in active_services
                        if search_term in s.get("name", "").lower()
                        or search_term in s.get("category", "").lower()
                        or search_term in s.get("description", "").lower()
                    ]
                else:
                    matching_services = active_services

                formatted = _format_services(
                    matching_services, len(matching_services) > 0, len(matching_services)
                )

                # If exactly one service matches, store it in state
                update_dict: dict = {
                    "messages": [ToolMessage(formatted, tool_call_id=tool_call_id)]
                }

                if len(matching_services) == 1:
                    service = matching_services[0]
                    service_info: ServiceInfo = {
                        "service_id": service.get("id"),
                        "name": service.get("name"),
                        "category": service.get("category"),
                        "price": f"${service.get('price', 0):.2f}",
                        "duration_minutes": service.get("duration_minutes", 0),
                        "description": service.get("description", ""),
                    }
                    update_dict["selected_service"] = service_info

                return Command(update=update_dict)

            except httpx.HTTPStatusError as e:
                error_msg = f"Error fetching services: {e.response.status_code}"
                return Command(
                    update={"messages": [ToolMessage(error_msg, tool_call_id=tool_call_id)]}
                )
            except httpx.RequestError as e:
                error_msg = f"Network error while fetching services: {str(e)}"
                return Command(
                    update={"messages": [ToolMessage(error_msg, tool_call_id=tool_call_id)]}
                )
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                return Command(
                    update={"messages": [ToolMessage(error_msg, tool_call_id=tool_call_id)]}
                )

        self.tools = [browse_services]

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
