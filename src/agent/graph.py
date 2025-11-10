"""LangGraph implementation of the barbershop booking agent.

This module provides a graph with agent and tool nodes using middleware.
The graph uses:
- Agent node: Runs LLM with middleware pipeline
- Tool node: Executes tool calls automatically
- Conditional routing: agent → tools → agent or END

Example:
    >>> from src.agent.graph import create_booking_graph
    >>> graph = create_booking_graph()
    >>> response = await graph.ainvoke({"messages": [{"role": "user", "content": "Book a haircut"}]})
"""

from pathlib import Path
from typing import Any, Literal

from langchain_core.messages import AIMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode

from src.agent.llm.registry import get_llm
from src.agent.prompt import BOOKING_AGENT_SYSTEM_PROMPT
from src.agent.state import BookingAgentState
from src.agent.tools import (
    get_availability_tools,
    get_barber_tools,
    get_booking_tools,
    get_customer_tools,
    get_policy_tools,
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
        *get_policy_tools(),
        *get_booking_tools(),
    ]

    # Bind tools to LLM
    llm_with_tools = llm.bind_tools(tools)

    # Create tool node for automatic tool execution
    tool_node = ToolNode(tools)

    def should_continue(state: BookingAgentState) -> Literal["tools", "__end__"]:
        """Decide whether to call tools or end.

        Args:
            state: Current agent state.

        Returns:
            "tools" to execute tools, or "__end__" to return to user.
        """
        messages = state.get("messages", [])
        if not messages:
            return "__end__"

        last_message = messages[-1]

        # If last message has tool calls, execute them
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tools"

        # Check for interrupt (HITL)
        if "__interrupt__" in state:
            return "__end__"

        # Otherwise, return to user
        return "__end__"

    async def call_agent(state: BookingAgentState) -> dict[str, list[Any]]:
        """Call the agent with current state.

        Args:
            state: Current state with messages.

        Returns:
            Updated state from agent.
        """
        messages = state["messages"]

        # Prepend system message if not present
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=BOOKING_AGENT_SYSTEM_PROMPT)] + messages

        # Call LLM with tools
        response = await llm_with_tools.ainvoke(messages)

        # Return updated state
        return {"messages": [response]}

    # Build the graph
    workflow = StateGraph(BookingAgentState)

    # Add nodes
    workflow.add_node("agent", call_agent)
    workflow.add_node("tools", tool_node)

    # Set entry point
    workflow.set_entry_point("agent")

    # Add conditional edges from agent
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            END: END,
        },
    )

    # After tool execution, always return to agent
    workflow.add_edge("tools", "agent")

    # Compile the graph with checkpointer for HITL
    graph = workflow.compile(checkpointer=MemorySaver())

    # Generate Mermaid PNG
    mermaid_png = graph.get_graph().draw_mermaid_png()

    # Save to file
    output_path = Path(__file__).parent.parent.parent / "graph.png"
    with open(output_path, "wb") as f:
        f.write(mermaid_png)

    return graph
