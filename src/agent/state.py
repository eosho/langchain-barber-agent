"""Custom state schema for the barbershop booking agent.

This module defines the extended agent state with booking-specific fields
that persist across conversation turns.
"""

from typing import NotRequired

from langchain.agents import AgentState


class BookingAgentState(AgentState):
    """Extended agent state with booking-specific fields."""

    # Business context
    business_name: NotRequired[str]
    current_date: NotRequired[str]  # Current date in YYYY-MM-DD format for context

    # Customer information
    customer_id: NotRequired[str]  # UUID string
    customer_name: NotRequired[str]
    customer_email: NotRequired[str]
    customer_phone: NotRequired[str]

    # Service selection
    service_id: NotRequired[str]  # UUID string
    service_name: NotRequired[str]
    service_price: NotRequired[float]
    service_duration: NotRequired[int]

    # Booking details
    booking_id: NotRequired[str]  # UUID string
    booking_date: NotRequired[str]
    booking_time: NotRequired[str]
    stylist_name: NotRequired[str]
    booking_notes: NotRequired[str]
    booking_status: NotRequired[str]

    # Availability
    available_slots: NotRequired[list[dict[str, str]]]
    checked_dates: NotRequired[list[str]]

    # Policy validation
    policy_checks: NotRequired[dict[str, bool]]
    cancellation_allowed: NotRequired[bool]

    # Conversation flow
    conversation_stage: NotRequired[str]
    next_action: NotRequired[str]
