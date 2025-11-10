"""Customer lookup tool for the customer sub-agent.

Moved from src/agent/tools/customers.py to be co-located with the customer node.
"""

import json
from typing import Any

import httpx
from langchain.tools import tool
from pydantic import BaseModel, Field

from src.core.config import get_settings

settings = get_settings()


class LookupCustomerInput(BaseModel):
    """Input schema for looking up a customer."""

    email: str | None = Field(
        default=None,
        description="Customer email address for lookup",
        max_length=255,
    )
    phone: str | None = Field(
        default=None,
        description="Customer phone number for lookup",
        max_length=20,
    )
    customer_id: str | None = Field(
        default=None,
        description="Customer ID (UUID) for direct lookup",
        min_length=1,
    )


@tool("lookup_customer", args_schema=LookupCustomerInput)
async def lookup_customer(
    email: str | None = None,
    phone: str | None = None,
    customer_id: str | None = None,
) -> str:
    """Look up customer information by email, phone, or customer ID.

    Use this when you need to find a customer's details or verify their identity.
    Returns customer profile including name, contact info, and preferences.
    """
    try:
        base_url = f"http://{settings.api_host}:{settings.api_port}/api/v1/customers/"

        # Direct lookup by customer_id
        if customer_id:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{base_url}{customer_id}/")
                response.raise_for_status()
                customer = response.json()

            return _format_customer(customer)

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
                return "No customer found with the provided contact information."

            # Return first matching customer
            customer = customers[0]
            return _format_customer(customer)

        return "Please provide either email, phone, or customer_id to lookup a customer."

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return "Customer not found."
        return f"Error looking up customer: {e.response.text}"
    except httpx.RequestError as e:
        return f"Network error while looking up customer: {str(e)}"
    except Exception as e:
        return f"Unexpected error during customer lookup: {str(e)}"


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


def get_customer_tools() -> list[Any]:
    """Get all customer-related tools.

    Returns:
        List of customer tools for LLM binding.
    """
    return [lookup_customer]
