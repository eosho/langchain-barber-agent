"""Business rules enforcement middleware for booking operations.

This middleware validates booking policies before tool execution to prevent
policy violations and provide clear feedback to users.
"""

from datetime import datetime, timedelta
from typing import Any

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langgraph.runtime import Runtime

from src.core.config import get_settings

settings = get_settings()


class BusinessRulesMiddleware(AgentMiddleware):
    """Enforce business rules and policies before tool execution."""

    @property
    def name(self) -> str:
        """Return the middleware name identifier."""
        return "business_rules"

    def before_tool_call(
        self, tool_name: str, tool_input: dict[str, Any], state: AgentState, runtime: Runtime
    ) -> dict[str, Any] | None:  # noqa: ARG002
        """Validate business rules before tool execution.

        Args:
            tool_name: Name of the tool being called
            tool_input: Arguments passed to the tool
            state: Current agent state
            runtime: Runtime context

        Returns:
            Error dict if validation fails, None if valid
        """
        # Validate booking creation
        if tool_name == "create_booking":
            return self._validate_booking_creation(tool_input)

        # Validate booking cancellation
        if tool_name == "cancel_booking":
            return self._validate_booking_cancellation(tool_input)

        # Validate booking updates
        if tool_name == "update_booking":
            return self._validate_booking_update(tool_input)

        return None

    def _validate_booking_creation(self, tool_input: dict[str, Any]) -> dict[str, Any] | None:
        """Validate booking creation against business rules.

        Args:
            tool_input: Booking parameters

        Returns:
            Error dict if validation fails, None if valid
        """
        try:
            # Parse booking date/time
            booking_date_str = tool_input.get("date")
            booking_time_str = tool_input.get("time")

            if not booking_date_str or not booking_time_str:
                return None  # Let tool handle missing parameters

            # Combine date and time
            booking_datetime = datetime.strptime(
                f"{booking_date_str} {booking_time_str}", "%Y-%m-%d %H:%M"
            )

            now = datetime.now()

            # Rule 1: Cannot book in the past
            if booking_datetime < now:
                return {
                    "error": "Cannot book appointments in the past",
                    "policy": "no_past_bookings",
                    "requested_time": booking_datetime.isoformat(),
                    "current_time": now.isoformat(),
                }

            # Rule 2: Same-day bookings require minimum notice
            hours_until_booking = (booking_datetime - now).total_seconds() / 3600
            is_same_day = booking_datetime.date() == now.date()

            if is_same_day:
                # Check cutoff time
                cutoff_time = now.replace(
                    hour=settings.same_day_booking_cutoff_hour, minute=0, second=0, microsecond=0
                )
                if now >= cutoff_time:
                    return {
                        "error": f"Same-day bookings must be made before {settings.same_day_booking_cutoff_hour}:00",
                        "policy": "same_day_cutoff",
                        "cutoff_time": cutoff_time.strftime("%I:%M %p"),
                        "suggestion": f"Please book for {(now + timedelta(days=1)).strftime('%Y-%m-%d')} or later",
                    }

                # Check minimum notice (2 hours)
                min_notice_hours = 2.0
                if hours_until_booking < min_notice_hours:
                    return {
                        "error": f"Same-day bookings require at least {min_notice_hours} hours notice",
                        "policy": "minimum_notice",
                        "hours_needed": min_notice_hours,
                        "hours_available": round(hours_until_booking, 1),
                        "suggestion": f"Please book for {(now + timedelta(hours=min_notice_hours)).strftime('%Y-%m-%d %H:%M')} or later",
                    }

            # Rule 3: Cannot book too far in advance
            max_advance_days = settings.booking_advance_days
            max_booking_date = now + timedelta(days=max_advance_days)

            if booking_datetime > max_booking_date:
                return {
                    "error": f"Cannot book more than {max_advance_days} days in advance",
                    "policy": "max_advance_booking",
                    "max_date": max_booking_date.strftime("%Y-%m-%d"),
                    "requested_date": booking_date_str,
                }

            # Rule 4: Validate business hours
            day_of_week = str(booking_datetime.weekday())
            business_hours = settings.business_hours.get(day_of_week)

            if business_hours:
                open_time = datetime.strptime(business_hours["open"], "%H:%M").time()
                close_time = datetime.strptime(business_hours["close"], "%H:%M").time()
                booking_time = booking_datetime.time()

                if not (open_time <= booking_time <= close_time):
                    return {
                        "error": f"Booking time must be within business hours ({business_hours['open']} - {business_hours['close']})",
                        "policy": "business_hours",
                        "requested_time": booking_time_str,
                        "business_hours": business_hours,
                    }

            print(
                f"[BusinessRules] ✓ Booking validation passed for {booking_date_str} {booking_time_str}"
            )
            return None

        except (ValueError, KeyError) as e:
            # Invalid date/time format - let tool handle it
            print(f"[BusinessRules] Validation error: {e}")
            return None

    def _validate_booking_cancellation(self, tool_input: dict[str, Any]) -> dict[str, Any] | None:
        """Validate booking cancellation against business rules.

        Args:
            tool_input: Cancellation parameters (booking_id)

        Returns:
            Error dict if validation fails, None if valid
        """
        # Note: We need the booking datetime to validate cancellation policy
        # In a real implementation, we'd fetch the booking from the database here
        # For now, we'll assume the tool will handle policy validation
        # or we need to add booking_datetime to the tool_input

        booking_datetime_str = tool_input.get("booking_datetime")
        if not booking_datetime_str:
            # Can't validate without booking time - let tool handle it
            return None

        try:
            booking_datetime = datetime.fromisoformat(booking_datetime_str)
            now = datetime.now()

            # Rule: Cancellations require minimum notice
            hours_until_booking = (booking_datetime - now).total_seconds() / 3600
            min_cancellation_hours = settings.cancellation_notice_hours

            if hours_until_booking < min_cancellation_hours:
                return {
                    "error": f"Cancellations require at least {min_cancellation_hours} hours notice",
                    "policy": "cancellation_notice",
                    "hours_required": min_cancellation_hours,
                    "hours_remaining": round(hours_until_booking, 1),
                    "booking_time": booking_datetime.strftime("%Y-%m-%d %H:%M"),
                }

            print(
                f"[BusinessRules] ✓ Cancellation validation passed ({hours_until_booking:.1f}h notice)"
            )
            return None

        except (ValueError, KeyError) as e:
            print(f"[BusinessRules] Validation error: {e}")
            return None

    def _validate_booking_update(self, tool_input: dict[str, Any]) -> dict[str, Any] | None:
        """Validate booking update against business rules.

        Args:
            tool_input: Update parameters

        Returns:
            Error dict if validation fails, None if valid
        """
        # If updating to a new date/time, validate like a new booking
        if "new_date" in tool_input or "new_time" in tool_input:
            validation_input = {
                "date": tool_input.get("new_date"),
                "time": tool_input.get("new_time"),
            }
            return self._validate_booking_creation(validation_input)

        return None
