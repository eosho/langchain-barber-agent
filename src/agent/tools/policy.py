"""Policy validation tools for the policy sub-agent.

This module provides tools for validating business policies such as
cancellation windows, advance booking limits, and business hours.
"""

import json
from datetime import datetime, timedelta
from typing import Any

from langchain.tools import tool
from pydantic import BaseModel, Field, field_validator

from src.core.config import get_settings

settings = get_settings()


class CancellationPolicyInput(BaseModel):
    """Input schema for checking cancellation policy.

    Attributes:
        booking_date: Date of the booking in YYYY-MM-DD format.
        booking_time: Time of the booking in HH:MM format (24-hour).
    """

    booking_date: str = Field(
        description="Date of the booking in YYYY-MM-DD format",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    booking_time: str = Field(
        description="Time of the booking in HH:MM format (24-hour)",
        pattern=r"^([01]\d|2[0-3]):([0-5]\d)$",
    )

    @field_validator("booking_date")
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

    @field_validator("booking_time")
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


class BookingAdvanceInput(BaseModel):
    """Input schema for checking booking advance window.

    Attributes:
        booking_date: Date to validate in YYYY-MM-DD format.
    """

    booking_date: str = Field(
        description="Date to validate in YYYY-MM-DD format",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )

    @field_validator("booking_date")
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


class SameDayBookingInput(BaseModel):
    """Input schema for checking same-day booking policy.

    Attributes:
        booking_date: Date of the booking in YYYY-MM-DD format.
        booking_time: Time of the booking in HH:MM format (24-hour).
    """

    booking_date: str = Field(
        description="Date of the booking in YYYY-MM-DD format",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    booking_time: str = Field(
        description="Time of the booking in HH:MM format (24-hour)",
        pattern=r"^([01]\d|2[0-3]):([0-5]\d)$",
    )

    @field_validator("booking_date")
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

    @field_validator("booking_time")
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


class BusinessHoursInput(BaseModel):
    """Input schema for checking business hours.

    Attributes:
        booking_date: Date of the booking in YYYY-MM-DD format.
        booking_time: Time of the booking in HH:MM format (24-hour).
    """

    booking_date: str = Field(
        description="Date of the booking in YYYY-MM-DD format",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    booking_time: str = Field(
        description="Time of the booking in HH:MM format (24-hour)",
        pattern=r"^([01]\d|2[0-3]):([0-5]\d)$",
    )

    @field_validator("booking_date")
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

    @field_validator("booking_time")
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


@tool("check_cancellation_policy", args_schema=CancellationPolicyInput)
async def check_cancellation_policy(
    booking_date: str,
    booking_time: str,
) -> str:
    """Check if cancellation is allowed based on the cancellation notice period policy.

    Use this to verify if a customer can cancel their booking based on how much advance
    notice is required. Returns whether cancellation is allowed and hours until appointment.
    Most businesses require 24-48 hours notice for cancellations.

    Args:
        booking_date: Date of the booking in YYYY-MM-DD format.
        booking_time: Time of the booking in HH:MM format (24-hour).

    Returns:
        JSON string with cancellation policy validation result.

    Example:
        >>> result = await check_cancellation_policy(
        ...     booking_date="2025-11-15",
        ...     booking_time="14:00"
        ... )
        >>> print(result)
        {"allowed": true, "hours_until_booking": 72.5}
    """
    try:
        # Parse booking datetime
        booking_datetime = datetime.strptime(f"{booking_date} {booking_time}", "%Y-%m-%d %H:%M")
        now = datetime.now()

        # Check if booking is in the past
        if booking_datetime < now:
            return json.dumps(
                {
                    "allowed": False,
                    "reason": "Cannot cancel a past appointment",
                },
                indent=2,
            )

        # Check cancellation notice period
        hours_until_booking = (booking_datetime - now).total_seconds() / 3600
        required_hours = settings.cancellation_notice_hours

        if hours_until_booking < required_hours:
            return json.dumps(
                {
                    "allowed": False,
                    "reason": f"Must cancel at least {required_hours} hours in advance",
                    "hours_until_booking": round(hours_until_booking, 1),
                },
                indent=2,
            )

        return json.dumps(
            {
                "allowed": True,
                "hours_until_booking": round(hours_until_booking, 1),
            },
            indent=2,
        )

    except ValueError:
        return "Error: Invalid date or time format"


@tool("check_booking_advance", args_schema=BookingAdvanceInput)
async def check_booking_advance(booking_date: str) -> str:
    """Check if booking date is within the allowed advance booking window.

    Use this to verify if a booking date is not too far in the future. Each business
    has a maximum number of days in advance that bookings can be made (typically 30-90 days).
    Helps prevent customers from booking too far ahead.

    Args:
        booking_date: Date to validate in YYYY-MM-DD format.

    Returns:
        JSON string with booking advance validation result.

    Example:
        >>> result = await check_booking_advance(booking_date="2025-11-15")
        >>> print(result)
        {"allowed": true, "days_in_advance": 15}
    """
    try:
        check_date = datetime.strptime(booking_date, "%Y-%m-%d").date()
        today = datetime.now().date()

        # Check if date is in the past
        if check_date < today:
            return json.dumps(
                {
                    "allowed": False,
                    "reason": "Cannot book appointments in the past",
                },
                indent=2,
            )

        # Check if too far in advance
        max_date = today + timedelta(days=settings.booking_advance_days)
        if check_date > max_date:
            return json.dumps(
                {
                    "allowed": False,
                    "reason": f"Can only book up to {settings.booking_advance_days} days in advance",
                    "max_date": max_date.strftime("%Y-%m-%d"),
                },
                indent=2,
            )

        return json.dumps(
            {
                "allowed": True,
                "days_in_advance": (check_date - today).days,
            },
            indent=2,
        )

    except ValueError:
        return "Error: Invalid date format. Use YYYY-MM-DD"


@tool("check_same_day_booking", args_schema=SameDayBookingInput)
async def check_same_day_booking(
    booking_date: str,
    booking_time: str,  # noqa: ARG001
) -> str:
    """Check if same-day booking is allowed based on the daily cutoff time.

    Use this to verify if a customer can book an appointment for today. Many businesses
    have a cutoff time (e.g., no same-day bookings after 2 PM) to allow time for
    preparation and scheduling.

    Args:
        booking_date: Date of the booking in YYYY-MM-DD format.
        booking_time: Time of the booking in HH:MM format (24-hour).

    Returns:
        JSON string with same-day booking policy validation result.

    Example:
        >>> result = await check_same_day_booking(
        ...     booking_date="2025-11-15",
        ...     booking_time="10:00"
        ... )
        >>> print(result)
        {"is_same_day": false, "allowed": true}
    """
    try:
        check_date = datetime.strptime(booking_date, "%Y-%m-%d").date()
        today = datetime.now().date()

        # Not a same-day booking
        if check_date != today:
            return json.dumps(
                {
                    "is_same_day": False,
                    "allowed": True,
                },
                indent=2,
            )

        # Check if past cutoff time
        current_hour = datetime.now().hour
        cutoff_hour = settings.same_day_booking_cutoff_hour

        if current_hour >= cutoff_hour:
            return json.dumps(
                {
                    "is_same_day": True,
                    "allowed": False,
                    "reason": f"Same-day bookings not accepted after {cutoff_hour}:00",
                },
                indent=2,
            )

        return json.dumps(
            {
                "is_same_day": True,
                "allowed": True,
            },
            indent=2,
        )

    except ValueError:
        return "Error: Invalid date or time format"


@tool("check_business_hours", args_schema=BusinessHoursInput)
async def check_business_hours(
    booking_date: str,
    booking_time: str,
) -> str:
    """Check if booking time falls within business operating hours.

    Use this to verify if a requested appointment time is during the hours when the
    business is open. Different days may have different operating hours (e.g., closed
    on Sundays, shorter hours on weekends).

    Args:
        booking_date: Date of the booking in YYYY-MM-DD format.
        booking_time: Time of the booking in HH:MM format (24-hour).

    Returns:
        JSON string with business hours validation result.

    Example:
        >>> result = await check_business_hours(
        ...     booking_date="2025-11-15",
        ...     booking_time="14:00"
        ... )
        >>> print(result)
        {"allowed": true, "business_hours": "09:00 - 18:00"}
    """
    try:
        check_date = datetime.strptime(booking_date, "%Y-%m-%d").date()
        check_time = datetime.strptime(booking_time, "%H:%M").time()

        # Get business hours for the day
        day_of_week = str(check_date.weekday())
        business_hours = settings.business_hours.get(day_of_week)

        if not business_hours:
            return json.dumps(
                {
                    "allowed": False,
                    "reason": f"Business is closed on {check_date.strftime('%A')}",
                },
                indent=2,
            )

        # Parse business hours
        open_time = datetime.strptime(business_hours["open"], "%H:%M").time()
        close_time = datetime.strptime(business_hours["close"], "%H:%M").time()

        # Check if time is within hours
        if check_time < open_time or check_time >= close_time:
            return json.dumps(
                {
                    "allowed": False,
                    "reason": f"Business hours: {business_hours['open']} - {business_hours['close']}",
                    "requested_time": booking_time,
                },
                indent=2,
            )

        return json.dumps(
            {
                "allowed": True,
                "business_hours": f"{business_hours['open']} - {business_hours['close']}",
            },
            indent=2,
        )

    except ValueError:
        return "Error: Invalid date or time format"


def get_policy_tools() -> list[Any]:
    """Get all policy-related tools for LLM binding.

    Returns:
        List of LangChain tools for policy validation operations.

    Example:
        >>> tools = get_policy_tools()
        >>> for tool in tools:
        ...     print(f"Tool: {tool.name}")
        Tool: check_cancellation_policy
        Tool: check_booking_advance
        Tool: check_same_day_booking
        Tool: check_business_hours
    """
    return [
        check_cancellation_policy,
        check_booking_advance,
        check_same_day_booking,
        check_business_hours,
    ]
