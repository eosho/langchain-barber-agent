"""Booking context middleware for the booking agent.

This middleware injects booking-specific context before model calls
and extracts structured data after tool execution.
"""

from datetime import datetime
from typing import Any

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langgraph.runtime import Runtime


class BookingContextMiddleware(AgentMiddleware):
    """Inject and manage booking context throughout the conversation."""

    @property
    def name(self) -> str:
        return "booking_context"

    def before_model(
        self, state: AgentState, runtime: Runtime
    ) -> dict[str, Any] | None:  # noqa: ARG002
        """Inject booking context before model calls.

        This middleware:
        1. Adds current date context
        2. Tracks conversation stage
        3. Maintains booking state across turns

        Args:
            state: Current agent state
            runtime: Runtime context

        Returns:
            State updates or None
        """
        updates: dict[str, Any] = {}

        # Add current date if not present
        if "current_date" not in state:
            updates["current_date"] = datetime.now().strftime("%Y-%m-%d")

        # Initialize conversation stage if not present
        if "conversation_stage" not in state:
            updates["conversation_stage"] = "greeting"

        # Add business context if not present
        if "business_name" not in state:
            updates["business_name"] = "The Barbershop"

        # Log context injection (optional, can be removed in production)
        customer_id = state.get("customer_id")
        service_id = state.get("service_id")

        if customer_id or service_id:
            print(f"[BookingContext] Customer: {customer_id}, Service: {service_id}")

        return updates if updates else None


# Create singleton instance
booking_context_middleware = BookingContextMiddleware()
