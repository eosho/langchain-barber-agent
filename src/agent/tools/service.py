"""Service-related tools for browsing the service catalog.

This module provides tools for searching and retrieving service information,
including pricing, durations, and categories.
"""

import json
from typing import Any

import httpx
from langchain.tools import tool
from pydantic import BaseModel, Field

from src.core.config import get_settings

settings = get_settings()


class BrowseServicesInput(BaseModel):
    """Input schema for browsing services.

    Attributes:
        service_name: Optional service name or category to search for.
    """

    service_name: str | None = Field(
        default=None,
        description="Service name or category to search for (e.g., 'haircut', 'fade', 'beard'). Leave empty to list all services.",
        max_length=100,
    )


class GetServiceDetailsInput(BaseModel):
    """Input schema for getting service details.

    Attributes:
        service_id: UUID of the service to retrieve.
    """

    service_id: str = Field(
        description="Service ID (UUID) to retrieve details for",
        min_length=36,
        max_length=36,
    )


@tool("browse_services", args_schema=BrowseServicesInput)
async def browse_services(service_name: str | None = None) -> str:
    """Browse available services with pricing and duration information.

    Use this tool when:
    - Customer mentions a service type (haircut, fade, beard trim, etc.)
    - Customer asks "what services do you have?"
    - Need to show pricing and duration for services

    Args:
        service_name: Optional name or category to filter by. If None, returns all services.

    Returns:
        JSON string with matching services including id, name, category, price, and duration.

    Example:
        >>> result = await browse_services(service_name="haircut")
        >>> print(result)
        {"services": [{"id": "uuid", "name": "Classic Haircut", "price": 25.0, ...}], ...}
    """
    try:
        base_url = f"http://{settings.api_host}:{settings.api_port}/api/v1/services/"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(base_url)
            response.raise_for_status()
            services = response.json()

        # Filter to active services only
        active_services = [s for s in services if s.get("is_active", True)]

        # Filter by service_name if provided (case-insensitive search)
        if service_name:
            search_term = service_name.lower()
            matching_services = [
                s
                for s in active_services
                if search_term in s["name"].lower()
                or search_term in s.get("category", "").lower()
                or search_term in s.get("description", "").lower()
            ]
        else:
            matching_services = active_services

        if not matching_services:
            # Get available categories from all services
            categories = sorted({s.get("category", "General") for s in active_services})
            return json.dumps(
                {
                    "found": False,
                    "message": f"No services found matching '{service_name}'.",
                    "available_categories": categories,
                    "suggestion": "Try browsing by category or ask to see all services.",
                },
                indent=2,
            )

        # Format services for easy reading
        result = []
        for service in matching_services:
            result.append(
                {
                    "id": service["id"],
                    "name": service["name"],
                    "category": service.get("category", "General"),
                    "price": f"${service['price']:.2f}",
                    "duration_minutes": service["duration_minutes"],
                    "duration_display": f"{service['duration_minutes']} min",
                    "description": service.get("description", ""),
                }
            )

        return json.dumps(
            {
                "found": True,
                "count": len(result),
                "services": result,
                "message": f"Found {len(result)} service(s)",
            },
            indent=2,
        )

    except httpx.HTTPStatusError as e:
        return f"Error fetching services: API returned {e.response.status_code}"
    except httpx.HTTPError as e:
        return f"Error fetching services: {str(e)}"


@tool("get_service_details", args_schema=GetServiceDetailsInput)
async def get_service_details(service_id: str) -> str:
    """Get detailed information for a specific service by ID.

    Use this when you have a service UUID and need complete details.

    Args:
        service_id: Service UUID to look up.

    Returns:
        JSON string with complete service details.

    Example:
        >>> result = await get_service_details(service_id="19f70bd8-8f19-4739-8a7d-c83baefc7054")
        >>> print(result)
        {"id": "uuid", "name": "Classic Haircut", "price": 25.0, ...}
    """
    try:
        base_url = f"http://{settings.api_host}:{settings.api_port}/api/v1/services/{service_id}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(base_url)
            response.raise_for_status()
            service = response.json()

        # Format service details
        result = {
            "id": service["id"],
            "name": service["name"],
            "category": service.get("category", "General"),
            "price": f"${service['price']:.2f}",
            "price_amount": service["price"],
            "duration_minutes": service["duration_minutes"],
            "duration_display": f"{service['duration_minutes']} min",
            "description": service.get("description", ""),
            "is_active": service.get("is_active", True),
        }

        return json.dumps(result, indent=2)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return json.dumps(
                {
                    "found": False,
                    "message": f"Service with ID {service_id} not found.",
                },
                indent=2,
            )
        return f"Error fetching service: API returned {e.response.status_code}"
    except httpx.HTTPError as e:
        return f"Error fetching service: {str(e)}"


def get_service_tools() -> list[Any]:
    """Get all service-related tools for LLM binding.

    Returns:
        List of LangChain tools for service browsing operations.

    Example:
        >>> tools = get_service_tools()
        >>> llm_with_tools = llm.bind_tools(tools)
    """
    return [
        browse_services,
        get_service_details,
    ]
