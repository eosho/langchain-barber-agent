"""Unified booking agent using create_agent with middleware pattern.

This module implements a single agent with all tools and middleware,
replacing the complex StateGraph supervisor pattern with a simpler
middleware-based approach.
"""

from datetime import datetime
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware, PIIMiddleware
from langgraph.checkpoint.memory import MemorySaver

from src.agent.llm.registry import get_llm
from src.agent.middleware import (
    AvailabilityMiddleware,
    BarberInfoMiddleware,
    BookingMiddleware,
    BusinessRulesMiddleware,
    ConversationSummaryMiddleware,
    CustomerLookupMiddleware,
    ServiceCatalogMiddleware,
    UsageTrackingMiddleware,
)
from src.agent.prompt import BOOKING_AGENT_SYSTEM_PROMPT
from src.agent.state import BookingAgentState


def create_booking_agent(business_name: str = "The Barbershop") -> Any:
    """Create unified booking agent with middleware.

    This creates a single agent using create_agent() with:
    - All tools from sub-agents
    - Middleware stack for context management
    - Unified system prompt

    Args:
        business_name: Name of the business for the prompt

    Returns:
        Compiled agent graph ready for invocation
    """
    # Get LLM
    llm = get_llm()

    # Format system prompt with current context
    current_date = datetime.now().strftime("%Y-%m-%d")
    formatted_prompt = BOOKING_AGENT_SYSTEM_PROMPT.format(
        business_name=business_name, current_date=current_date
    )

    # Create agent with middleware
    agent: Any = create_agent(
        model=llm,
        tools=[],
        system_prompt=formatted_prompt,
        state_schema=BookingAgentState,
        middleware=[
            AvailabilityMiddleware(),
            BarberInfoMiddleware(),
            BookingMiddleware(),
            BusinessRulesMiddleware(),
            ConversationSummaryMiddleware(max_messages=20),
            CustomerLookupMiddleware(),
            ServiceCatalogMiddleware(),
            PIIMiddleware("email", strategy="mask", apply_to_input=True),
            PIIMiddleware("credit_card", strategy="mask", apply_to_input=True),
            UsageTrackingMiddleware(),
            HumanInTheLoopMiddleware(
                interrupt_on={
                    "create_booking": {"allowed_decisions": ["approve", "reject"]},
                    "cancel_booking": {"allowed_decisions": ["approve", "reject"]},
                    "update_booking": {"allowed_decisions": ["approve", "reject"]},
                },
                description_prefix="Booking action pending approval",
            ),
        ],
        checkpointer=MemorySaver(),  # Required for HITL interrupts
    )

    return agent
