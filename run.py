"""Interactive CLI for the barbershop booking agent.

Run this script to interactively test the agent or graph implementation.
Make sure the API is running before starting this script.

Usage:
    python run.py                    # Default: use agent
    python run.py --mode agent       # Use agent.py (create_agent with middleware)
    python run.py --mode graph       # Use graph.py (manual StateGraph with agent/tool nodes)
"""

import argparse
import asyncio
import uuid
from datetime import datetime
from pathlib import Path

import yaml
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command


def load_business_config() -> dict:
    """Load business configuration from seed_data.yaml.

    Returns:
        Business configuration dictionary.
    """
    seed_file = Path(__file__).parent / "seed_data.yaml"
    if seed_file.exists():
        with open(seed_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data.get("business", {})
    return {}


async def main():
    """Run interactive agent session with checkpointing."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Barbershop Booking Agent CLI")
    parser.add_argument(
        "--mode",
        choices=["agent", "graph"],
        default="agent",
        help="Choose implementation: 'agent' (create_agent with middleware) or 'graph' (manual StateGraph)",
    )
    args = parser.parse_args()

    print("🪒 Barbershop Booking Agent")
    print("=" * 50)
    print(f"📦 Mode: {args.mode.upper()}")
    print("Type 'quit' or 'exit' to end the session\n")

    # Load business configuration from seed data
    business_config = load_business_config()
    business_name = business_config.get("name", "The Barbershop")

    print(f"🏪 Business: {business_name}")

    # Create agent or graph based on mode
    if args.mode == "agent":
        from src.agent.agent import create_booking_agent

        agent = create_booking_agent()
        print("✅ Using: create_booking_agent() with middleware")
    else:
        from src.agent.graph import create_booking_graph

        agent = create_booking_graph()
        print("✅ Using: create_booking_graph() with StateGraph")

    # Create a unique thread ID for this conversation session
    thread_id = str(uuid.uuid4())
    config = RunnableConfig(configurable={"thread_id": thread_id})

    print(f"📝 Session ID: {thread_id}\n")

    while True:
        try:
            # Get user input
            user_input = input("\n👤 You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["quit", "exit", "bye"]:
                print("\n👋 Thanks for chatting! Goodbye!")
                break

            # Create user message
            user_message = HumanMessage(content=user_input)

            # Initialize state with new message
            initial_state: dict = {
                "messages": [user_message],
                "business_name": business_name,
                "current_date": datetime.now().strftime("%Y-%m-%d"),
            }

            print("\n🤔 Agent thinking...\n")

            # Invoke agent/graph with checkpoint config
            result = await agent.ainvoke(initial_state, config=config)  # type: ignore

            # Check for interrupts (Human-in-the-Loop)
            if "__interrupt__" in result:
                interrupts = result["__interrupt__"]
                if interrupts:
                    interrupt = interrupts[0]
                    print("\n" + "=" * 50)
                    print("HUMAN APPROVAL REQUIRED")
                    print("=" * 50)

                    # Extract action request details
                    value = interrupt.value if hasattr(interrupt, "value") else interrupt

                    # Handle different interrupt value structures
                    action_requests = []
                    if isinstance(value, dict):
                        action_requests = value.get("action_requests", [])
                    elif isinstance(value, list):
                        action_requests = value

                    for req in action_requests:
                        # Extract tool name from different possible locations
                        tool_name = (
                            req.get("tool")
                            or req.get("action")
                            or req.get("name")
                            or req.get("tool_call", {}).get("name")
                            or "unknown"
                        )

                        description = req.get("description", "Booking action pending approval")

                        print(f"\nAction: {tool_name}")
                        print(f"Description: {description}")

                        # Try to get tool input from different possible locations
                        tool_input = (
                            req.get("tool_input")
                            or req.get("args")
                            or req.get("tool_call", {}).get("args")
                        )

                        if tool_input:
                            print("Parameters:")
                            for key, val in tool_input.items():
                                print(f"   - {key}: {val}")

                    # Get user decision
                    decision = input("\nDecision ([a]pprove/[r]eject): ").strip().lower()

                    # Build resume payload based on decision
                    if decision.startswith("a"):
                        resume_payload = {"decisions": [{"type": "approve"}]}
                        print("\nApproved - resuming execution...")
                    elif decision.startswith("r"):
                        resume_payload = {"decisions": [{"type": "reject"}]}
                        print("\nRejected - cancelling action...")
                    else:
                        resume_payload = {"decisions": [{"type": "reject"}]}
                        print("\nUnrecognized decision - defaulting to reject...")

                    # Resume with decision
                    result = await agent.ainvoke(Command(resume=resume_payload), config=config)

            final_response = result

            # Print all messages to see tool calls and intermediate steps
            print("\n" + "=" * 50)
            print("💭 CONVERSATION TRACE:")
            print("=" * 50)
            for i, msg in enumerate(final_response["messages"]):
                print(f"\n[Message {i+1}]")
                msg.pretty_print()

            # print("\n" + "=" * 50)
            # print("🤖 FINAL RESPONSE:")
            # print("=" * 50)
            # final_response["messages"][-1].pretty_print()

        except KeyboardInterrupt:
            print("\n\n👋 Session interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print(f"   Type: {type(e).__name__}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
