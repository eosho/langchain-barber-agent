"""Customer lookup middleware for agents."""

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


class CustomerInfo(TypedDict):
    """Customer information structure."""

    customer_id: str
    """Customer ID (UUID)."""

    name: str
    """Customer full name."""

    email: str
    """Customer email address."""

    phone: str
    """Customer phone number."""

    preferences: dict
    """Customer preferences and settings."""


class CustomerLookupState(AgentState):
    """State schema for customer lookup middleware."""

    customer_info: Annotated[NotRequired[CustomerInfo], OmitFromInput]
    """Currently looked-up customer information."""


CUSTOMER_LOOKUP_TOOL_DESCRIPTION = """Look up customer information by email, phone, or customer ID.

Use this when you need to find a customer's details or verify their identity.
Returns customer profile including name, contact info, and preferences.

This tool will automatically update the agent's state with the customer information
for use in subsequent operations like booking appointments."""


CUSTOMER_LOOKUP_SYSTEM_PROMPT = """## `lookup_customer`

You have access to the `lookup_customer` tool to search for customer information.
Use this tool when you need to identify a customer before performing operations like booking appointments.

When a customer is successfully found, their information is automatically stored in the state
for use in subsequent tool calls."""


def _format_customer(customer: dict) -> str:
    """Format customer data for LLM consumption.

    Args:
        customer: Customer data dictionary from API.

    Returns:
        Formatted customer information string.
    """
    return json.dumps(
        {
            "customer_id": customer.get("id"),
            "name": customer.get("name"),
            "email": customer.get("email"),
            "phone": customer.get("phone"),
            "preferences": customer.get("preferences", {}),
        },
        indent=2,
    )


class CustomerLookupMiddleware(AgentMiddleware):
    """Middleware that provides customer lookup capabilities with state management.

    This middleware adds a `lookup_customer` tool that allows agents to search for
    customer information by email, phone, or customer ID. When a customer is found,
    their information is automatically stored in the agent's state for use in
    subsequent operations.

    Example:
        ```python
        from langchain.agents.middleware.customer_lookup import CustomerLookupMiddleware
        from langchain.agents import create_agent

        agent = create_agent(
            "openai:gpt-4o",
            middleware=[CustomerLookupMiddleware()]
        )

        # Agent now has access to lookup_customer tool and customer state tracking
        result = await agent.invoke({
            "messages": [HumanMessage("Find customer with email john@example.com")]
        })

        print(result["customer_info"]["name"])  # Customer name from lookup
        print(result["customer_info"]["customer_id"])  # Customer ID for bookings
        ```

    Args:
        system_prompt: Custom system prompt to guide the agent on using the tool.
            If not provided, uses the default `CUSTOMER_LOOKUP_SYSTEM_PROMPT`.
        tool_description: Custom description for the lookup_customer tool.
            If not provided, uses the default `CUSTOMER_LOOKUP_TOOL_DESCRIPTION`.
    """

    state_schema = CustomerLookupState

    def __init__(
        self,
        *,
        system_prompt: str = CUSTOMER_LOOKUP_SYSTEM_PROMPT,
        tool_description: str = CUSTOMER_LOOKUP_TOOL_DESCRIPTION,
    ) -> None:
        """Initialize the CustomerLookupMiddleware with optional custom prompts.

        Args:
            system_prompt: Custom system prompt to guide the agent on using the tool.
            tool_description: Custom description for the lookup_customer tool.
        """
        super().__init__()
        self.system_prompt = system_prompt
        self.tool_description = tool_description

        # Dynamically create the lookup_customer tool with the custom description
        @tool(description=self.tool_description)
        async def lookup_customer(
            email: str,
            phone: str,
            customer_id: str,
            tool_call_id: Annotated[str, InjectedToolCallId],
        ) -> Command:
            """Look up customer information and update state."""
            try:
                base_url = f"http://{settings.api_host}:{settings.api_port}/api/v1/customers/"

                # Direct lookup by customer_id
                if customer_id:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        response = await client.get(f"{base_url}{customer_id}/")
                        response.raise_for_status()
                        customer = response.json()

                    customer_info: CustomerInfo = {
                        "customer_id": customer.get("id"),
                        "name": customer.get("name"),
                        "email": customer.get("email"),
                        "phone": customer.get("phone"),
                        "preferences": customer.get("preferences", {}),
                    }

                    formatted = _format_customer(customer)
                    return Command(
                        update={
                            "customer_info": customer_info,
                            "messages": [ToolMessage(formatted, tool_call_id=tool_call_id)],
                        }
                    )

                # Lookup by email or phone
                if email or phone:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        params = {}
                        if email:
                            params["email"] = email
                        elif phone:
                            params["phone"] = phone

                        response = await client.get(base_url, params=params)
                        response.raise_for_status()
                        customers = response.json()

                    if not customers:
                        error_msg = "No customer found with the provided contact information."
                        return Command(
                            update={"messages": [ToolMessage(error_msg, tool_call_id=tool_call_id)]}
                        )

                    # Return first matching customer and update state
                    customer = customers[0]
                    customer_info = {
                        "customer_id": customer.get("id"),
                        "name": customer.get("name"),
                        "email": customer.get("email"),
                        "phone": customer.get("phone"),
                        "preferences": customer.get("preferences", {}),
                    }

                    formatted = _format_customer(customer)
                    return Command(
                        update={
                            "customer_info": customer_info,
                            "messages": [ToolMessage(formatted, tool_call_id=tool_call_id)],
                        }
                    )

                error_msg = (
                    "Please provide either email, phone, or customer_id to lookup a customer."
                )
                return Command(
                    update={"messages": [ToolMessage(error_msg, tool_call_id=tool_call_id)]}
                )

            except httpx.HTTPStatusError as e:
                error_msg = (
                    "Customer not found."
                    if e.response.status_code == 404
                    else f"Error looking up customer: {e.response.text}"
                )
                return Command(
                    update={"messages": [ToolMessage(error_msg, tool_call_id=tool_call_id)]}
                )
            except httpx.RequestError as e:
                error_msg = f"Network error while looking up customer: {str(e)}"
                return Command(
                    update={"messages": [ToolMessage(error_msg, tool_call_id=tool_call_id)]}
                )
            except Exception as e:
                error_msg = f"Unexpected error during customer lookup: {str(e)}"
                return Command(
                    update={"messages": [ToolMessage(error_msg, tool_call_id=tool_call_id)]}
                )

        self.tools = [lookup_customer]

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
