"""LangGraph implementation of the barbershop booking agent.

This module provides a graph with agent and tool nodes using middleware.
The graph uses:
- Agent node: Runs LLM with middleware pipeline
- Tool node: Executes tool calls automatically
- Approval node: Human-in-the-loop for booking operations
- Conditional routing: agent → tools/approval → agent or END

Example:
    >>> from src.agent.graph import create_booking_graph
    >>> graph = create_booking_graph()
    >>> response = await graph.ainvoke({"messages": [{"role": "user", "content": "Book a haircut"}]})
"""

from datetime import datetime
from typing import Any, Literal

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt

from src.agent.llm.registry import get_llm
from src.agent.prompt import BOOKING_AGENT_SYSTEM_PROMPT
from src.agent.state import BookingAgentState
from src.agent.tools import (
    get_availability_tools,
    get_barber_tools,
    get_booking_tools,
    get_customer_tools,
    get_service_tools,
)


def create_booking_graph() -> CompiledStateGraph:
    """Create a LangGraph-based booking agent with tool execution.

    This implementation uses:
    - Agent node: LLM with tools and middleware
    - Tool node: Automatic execution of tool calls
    - Conditional routing: agent → tools → agent or END

    Returns:
        Compiled LangGraph instance ready for execution.

    Example:
        >>> graph = create_booking_graph()
        >>> result = await graph.ainvoke({
        ...     "messages": [{"role": "user", "content": "I need a haircut"}]
        ... })
    """
    # Get LLM
    llm = get_llm()

    # Collect all tools
    tools = [
        *get_customer_tools(),
        *get_service_tools(),
        *get_barber_tools(),
        *get_availability_tools(),
        *get_booking_tools(),
    ]

    # Bind tools to LLM
    llm_with_tools = llm.bind_tools(tools)
    tool_node = ToolNode(tools)

    # Booking operations that require approval
    BOOKING_OPERATIONS = {"create_booking", "cancel_booking", "modify_booking"}

    def should_continue(state: BookingAgentState) -> Literal["tools", "approval", "__end__"]:
        """Decide whether to call tools, request approval, or end.

        Args:
            state: Current agent state.

        Returns:
            "tools" to execute tools, "approval" for HITL, or "__end__" to return to user.
        """
        messages = state.get("messages", [])
        if not messages:
            return "__end__"

        last_message = messages[-1]

        # Check if we have tool calls
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            # Check if any tool call requires approval
            for tool_call in last_message.tool_calls:
                if tool_call["name"] in BOOKING_OPERATIONS:
                    return "approval"
            return "tools"

        return "__end__"

    def approval_node(state: BookingAgentState) -> dict:
        """Request human approval for booking operations.

        Args:
            state: Current agent state with pending tool calls.

        Returns:
            State update with approval decision and action details.
        """
        messages = state.get("messages", [])
        if not messages:
            return {"approval_required": False}

        last_message = messages[-1]
        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            return {"approval_required": False}

        # Collect all booking operation tool calls
        booking_tool_calls = [
            tool_call
            for tool_call in last_message.tool_calls
            if tool_call["name"] in BOOKING_OPERATIONS
        ]

        if not booking_tool_calls:
            return {"approval_required": False}

        # Build action_requests for run.py interrupt handler
        action_requests = []
        for tool_call in booking_tool_calls:
            action_name = tool_call["name"]
            action_args = tool_call["args"]

            # Format description based on action type
            if action_name == "create_booking":
                description = (
                    f"Create booking for customer {action_args.get('customer_id', 'N/A')}... "
                    f"on {action_args.get('date', 'N/A')} at {action_args.get('time', 'N/A')} "
                    f"with {action_args.get('stylist_name', 'N/A')}"
                )
            elif action_name == "cancel_booking":
                description = f"Cancel booking {action_args.get('booking_id', 'N/A')}..."
            elif action_name == "modify_booking":
                description = f"Modify booking {action_args.get('booking_id', 'N/A')}..."
            else:
                description = f"Execute {action_name}"

            action_requests.append(
                {
                    "tool": action_name,
                    "description": description,
                    "tool_call": tool_call,
                    "tool_input": action_args,
                }
            )

        # Request approval from human (interrupt execution)
        approval_response = interrupt({"action_requests": action_requests})

        # Expected format: {"decisions": [{"type": "approve"/"reject"}]}
        decisions = approval_response.get("decisions", []) if approval_response else []

        if decisions and decisions[0].get("type") == "approve":
            return {}
        else:
            # Approval denied - inject rejection messages for each booking tool call
            rejection_messages = [
                ToolMessage(
                    content=f"Action cancelled by user: {tool_call['name']}",
                    tool_call_id=tool_call["id"],
                )
                for tool_call in booking_tool_calls
            ]
            return {
                "messages": rejection_messages,
            }

    def route_after_approval(state: BookingAgentState) -> Literal["tools", "agent"]:
        """Route after approval decision.

        Args:
            state: Current agent state.

        Returns:
            "tools" if approved, "agent" if denied.
        """
        messages = state.get("messages", [])
        if not messages:
            return "agent"

        # Check if last message is a rejection ToolMessage
        last_message = messages[-1]
        if isinstance(last_message, ToolMessage) and "cancelled by user" in last_message.content:
            return "agent"

        return "tools"

    async def call_agent(
        state: BookingAgentState, business_name: str = "The shop"
    ) -> dict[str, list[Any]]:
        """Call the agent with current state.

        Args:
            state: Current state with messages.
            business_name: Name of the business.

        Returns:
            Updated state from agent.
        """
        messages = state["messages"]

        # Format system prompt with current context
        current_date = datetime.now().strftime("%Y-%m-%d")
        formatted_prompt = BOOKING_AGENT_SYSTEM_PROMPT.format(
            business_name=business_name, current_date=current_date
        )

        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=formatted_prompt)] + messages

        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    # Build the graph & nodes
    workflow = StateGraph(BookingAgentState)
    workflow.add_node("agent", call_agent)
    workflow.add_node("tools", tool_node)
    workflow.add_node("approval", approval_node)
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "approval": "approval",
            END: END,
        },
    )
    workflow.add_conditional_edges(
        "approval",
        route_after_approval,
        {
            "tools": "tools",
            "agent": "agent",
        },
    )
    workflow.add_edge("tools", "agent")

    graph = workflow.compile(checkpointer=MemorySaver())
    return graph
