"""Barber-related tools for the barber sub-agent.

This module provides tools for retrieving barber information,
specialties, and schedules.
"""

import json
from typing import Any

import httpx
from langchain.tools import tool
from pydantic import BaseModel, Field

from src.core.config import get_settings

settings = get_settings()


class BarberDetailsInput(BaseModel):
    """Input schema for getting barber details.

    Attributes:
        barber_name: Name of the barber to look up.
    """

    barber_name: str = Field(
        description="Name of the barber (e.g., 'Tony', 'Mike')",
        min_length=2,
        max_length=100,
    )


class FindBarbersBySpecialtyInput(BaseModel):
    """Input schema for finding barbers by specialty.

    Attributes:
        specialty: The specialty or skill to search for.
    """

    specialty: str = Field(
        description="Specialty to search for (e.g., 'fades', 'beard trim', 'hair color')",
        min_length=2,
        max_length=100,
    )


class BarberScheduleInput(BaseModel):
    """Input schema for getting barber schedule.

    Attributes:
        barber_name: Name of the barber.
    """

    barber_name: str = Field(
        description="Name of the barber",
        min_length=2,
        max_length=100,
    )


@tool("list_barbers")
async def list_barbers() -> str:
    """Get a list of all active barbers with their specialties.

    Use this tool to show the customer all available barbers and what they specialize in.
    Returns barber names, specialties, and contact information.

    Returns:
        JSON string with list of barbers and their details.

    Example:
        >>> result = await list_barbers()
        >>> print(result)
        [{"name": "Tony", "specialties": ["Classic cuts", "Fades"], ...}]
    """
    try:
        base_url = f"http://{settings.api_host}:{settings.api_port}/api/v1/barbers/"
        async with httpx.AsyncClient() as client:
            response = await client.get(
                base_url,
                timeout=10.0,
            )
            response.raise_for_status()
            barbers = response.json()

        # Filter to active barbers only and format nicely
        active_barbers = [b for b in barbers if b.get("is_active", True)]

        result = []
        for barber in active_barbers:
            result.append(
                {
                    "id": barber["id"],
                    "name": barber["name"],
                    "specialties": barber.get("specialties", []),
                    "email": barber.get("email"),
                    "phone": barber.get("phone"),
                }
            )

        return json.dumps(result, indent=2)

    except httpx.HTTPError as e:
        return f"Error fetching barbers: {str(e)}"


@tool("get_barber_details", args_schema=BarberDetailsInput)
async def get_barber_details(barber_name: str) -> str:
    """Get detailed information about a specific barber.

    Use this when the customer asks about a particular barber by name.
    Returns the barber's specialties, contact info, and status.

    Args:
        barber_name: Name of the barber to look up (e.g., 'Tony', 'Mike').

    Returns:
        JSON string with barber details or error message.

    Example:
        >>> result = await get_barber_details(barber_name="Tony")
        >>> print(result)
        {"name": "Tony", "specialties": ["Classic cuts", "Fades"], ...}
    """
    try:
        base_url = f"http://{settings.api_host}:{settings.api_port}/api/v1/barbers/"
        async with httpx.AsyncClient() as client:
            response = await client.get(
                base_url,
                timeout=10.0,
            )
            response.raise_for_status()
            barbers = response.json()

        # Find barber by name (case-insensitive)
        barber_name_lower = barber_name.lower()
        matching_barber = None

        for barber in barbers:
            if barber["name"].lower() == barber_name_lower:
                matching_barber = barber
                break

        if not matching_barber:
            return json.dumps(
                {
                    "found": False,
                    "message": f"No barber found with name '{barber_name}'. Available barbers: {', '.join(b['name'] for b in barbers if b.get('is_active', True))}",
                },
                indent=2,
            )

        return json.dumps(
            {
                "found": True,
                "barber": {
                    "id": matching_barber["id"],
                    "name": matching_barber["name"],
                    "specialties": matching_barber.get("specialties", []),
                    "email": matching_barber.get("email"),
                    "phone": matching_barber.get("phone"),
                    "is_active": matching_barber.get("is_active", True),
                },
            },
            indent=2,
        )

    except httpx.HTTPError as e:
        return f"Error fetching barber details: {str(e)}"


@tool("find_barbers_by_specialty", args_schema=FindBarbersBySpecialtyInput)
async def find_barbers_by_specialty(specialty: str) -> str:
    """Find barbers who specialize in a particular service or skill.

    Use this when a customer wants a barber with specific expertise
    (e.g., 'fades', 'beard trim', 'hair color', 'classic cuts').

    Args:
        specialty: The specialty or skill to search for.

    Returns:
        JSON string with matching barbers or message if none found.

    Example:
        >>> result = await find_barbers_by_specialty(specialty="fades")
        >>> print(result)
        [{"name": "Tony", "specialties": ["Classic cuts", "Fades"]}, ...]
    """
    try:
        base_url = f"http://{settings.api_host}:{settings.api_port}/api/v1/barbers/"
        async with httpx.AsyncClient() as client:
            response = await client.get(
                base_url,
                timeout=10.0,
            )
            response.raise_for_status()
            barbers = response.json()

        # Search for barbers with matching specialty (case-insensitive, partial match)
        specialty_lower = specialty.lower()
        matching_barbers = []

        for barber in barbers:
            if not barber.get("is_active", True):
                continue

            barber_specialties = barber.get("specialties", [])
            for barber_specialty in barber_specialties:
                if (
                    specialty_lower in barber_specialty.lower()
                    or barber_specialty.lower() in specialty_lower
                ):
                    matching_barbers.append(
                        {
                            "id": barber["id"],
                            "name": barber["name"],
                            "specialties": barber_specialties,
                        }
                    )
                    break

        if not matching_barbers:
            all_specialties = set()
            for barber in barbers:
                if barber.get("is_active", True):
                    all_specialties.update(barber.get("specialties", []))

            return json.dumps(
                {
                    "found": False,
                    "message": f"No barbers found specializing in '{specialty}'.",
                    "available_specialties": sorted(all_specialties),
                },
                indent=2,
            )

        return json.dumps(
            {"found": True, "matching_barbers": matching_barbers, "count": len(matching_barbers)},
            indent=2,
        )

    except httpx.HTTPError as e:
        return f"Error searching barbers: {str(e)}"


@tool("get_barber_schedule", args_schema=BarberScheduleInput)
async def get_barber_schedule(barber_name: str) -> str:
    """Get a barber's weekly schedule showing their working days and hours.

    Use this when a customer wants to know when a specific barber works.
    Shows which days the barber is available and their hours.

    Args:
        barber_name: Name of the barber.

    Returns:
        JSON string with the barber's weekly schedule.

    Example:
        >>> result = await get_barber_schedule(barber_name="Tony")
        >>> print(result)
        {"barber": "Tony", "schedule": [{"day": "Monday", "hours": "09:00-18:00"}, ...]}
    """
    try:
        # First, get the barber to find their ID
        base_url = f"http://{settings.api_host}:{settings.api_port}/api/v1/barbers/"
        async with httpx.AsyncClient() as client:
            response = await client.get(
                base_url,
                timeout=10.0,
            )
            response.raise_for_status()
            barbers = response.json()

        # Find barber by name
        barber_name_lower = barber_name.lower()
        matching_barber = None

        for barber in barbers:
            if barber["name"].lower() == barber_name_lower:
                matching_barber = barber
                break

        if not matching_barber:
            return json.dumps(
                {
                    "found": False,
                    "message": f"No barber found with name '{barber_name}'",
                },
                indent=2,
            )

        # Get the barber's availability/schedule
        # Note: This requires the barber availability endpoint to be implemented
        # For now, return a placeholder message
        return json.dumps(
            {
                "found": True,
                "barber": matching_barber["name"],
                "barber_id": matching_barber["id"],
                "message": "Schedule information available through availability check. Use the availability agent to check specific dates and times.",
            },
            indent=2,
        )

    except httpx.HTTPError as e:
        return f"Error fetching barber schedule: {str(e)}"


def get_barber_tools() -> list[Any]:
    """Get all barber-related tools for LLM binding.

    Returns:
        List of LangChain tools for barber operations.

    Example:
        >>> tools = get_barber_tools()
        >>> llm_with_tools = llm.bind_tools(tools)
    """
    return [
        list_barbers,
        get_barber_details,
        find_barbers_by_specialty,
        get_barber_schedule,
    ]
