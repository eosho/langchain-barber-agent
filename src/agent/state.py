"""Custom state schema for the barbershop booking agent.

This module defines the extended agent state with booking-specific fields
that persist across conversation turns.
"""

from typing import NotRequired

from langchain.agents import AgentState


class BookingAgentState(AgentState):
    """Extended agent state with booking-specific fields.

    Inherits messages from AgentState and adds booking context fields.
    All fields are NotRequired to allow incremental state building.
    Tools can update state using Command(update={...}).
    """

    # Business context (shared, read-only)
    business_name: NotRequired[str]
    current_date: NotRequired[str]  # YYYY-MM-DD

    # Customer information
    customer_id: NotRequired[str]  # UUID
    customer_name: NotRequired[str]
    customer_email: NotRequired[str]
    customer_phone: NotRequired[str]

    # Service selection
    service_id: NotRequired[str]  # UUID
    service_name: NotRequired[str]
    service_price: NotRequired[float]
    service_duration: NotRequired[int]  # minutes

    # Booking details
    booking_id: NotRequired[str]  # UUID
    booking_date: NotRequired[str]  # YYYY-MM-DD
    booking_time: NotRequired[str]  # HH:MM
    barber_id: NotRequired[str]  # UUID
    barber_name: NotRequired[str]
    booking_notes: NotRequired[str]
    booking_status: NotRequired[str]  # scheduled, cancelled, completed

    # Availability
    available_slots: NotRequired[list[dict[str, str]]]
    checked_dates: NotRequired[list[str]]

    # Policy validation
    policy_checks: NotRequired[dict[str, bool]]
    cancellation_allowed: NotRequired[bool]

    # Conversation flow
    conversation_stage: NotRequired[str]  # greeting, collecting_info, confirming, completed
    next_action: NotRequired[str]

    # Human-in-the-Loop approval
    pending_action: NotRequired[str]  # create_booking, cancel_booking, modify_booking
    action_details: NotRequired[dict]  # Details of the pending action for approval
    approval_required: NotRequired[bool]  # Whether approval is needed
