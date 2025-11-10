"""Chainlit chat application for the barbershop booking agent.

This module provides a conversational UI for customers to interact with
the AI booking agent through a web-based chat interface.

Example:
    Run the Chainlit app:
    $ chainlit run src/ui/chat_app.py
"""

import os

import chainlit as cl

from src.agent.agent import create_booking_agent
from src.core.config import get_settings

# Disable Chainlit's data layer (it tries to use DATABASE_URL which is for our app)
os.environ["CHAINLIT_DATABASE_URL"] = ""

settings = get_settings()


@cl.on_chat_start
async def on_chat_start() -> None:
    """Initialize chat session when a new user connects.

    This function runs once when a user opens the chat interface.
    It creates the agent and stores it in the user session.
    """
    # Create agent for this session (now uses middleware pattern)
    agent = create_booking_agent()

    # Generate a unique thread_id for this session
    thread_id = cl.user_session.get("id")

    # Store agent and thread_id in user session
    cl.user_session.set("agent", agent)
    cl.user_session.set("thread_id", thread_id)
    cl.user_session.set("message_history", [])

    # Send welcome message
    await cl.Message(
        content=f"""👋 Welcome to **{settings.business_name}**!

I'm Sam, your booking assistant. I'm here to help you:
- 📅 Book appointments for haircuts, trims, and more
- ⏰ Check available time slots
- 🔄 Reschedule or cancel existing bookings
- ℹ️ Answer questions about our services and hours

What can I help you with today?""",
        author="Sam",
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """Handle incoming messages from the user.

    This function processes each user message, sends it to the agent,
    and streams the response back to the chat interface.

    Args:
        message: The incoming message from the user.
    """
    # Get agent, thread_id, and history from session
    agent = cl.user_session.get("agent")
    thread_id = cl.user_session.get("thread_id")
    message_history = cl.user_session.get("message_history", [])

    if not agent or not thread_id:
        await cl.Message(
            content="❌ Session expired. Please refresh the page to start a new conversation.",
            author="System",
        ).send()
        return

    # Ensure message_history is a list
    if message_history is None:
        message_history = []

    # Add user message to history
    message_history.append({"role": "user", "content": message.content})

    try:
        # Show thinking indicator
        async with cl.Step(name="Processing", type="tool") as step:
            step.output = "Thinking..."

            # Invoke agent with thread_id config for checkpointing
            result = await agent.ainvoke(
                {"messages": message_history},
                config={"configurable": {"thread_id": thread_id}},
            )

            # Extract assistant response
            assistant_message = result["messages"][-1]
            response_content = (
                assistant_message.content
                if hasattr(assistant_message, "content")
                else str(assistant_message)
            )

            # Update history with full conversation
            message_history = result["messages"]
            cl.user_session.set("message_history", message_history)

            step.output = "Response ready"

        # Send response
        await cl.Message(content=response_content, author="Sam").send()

    except Exception as e:
        error_message = (
            "I apologize, but I encountered an error processing your request. "
            "Could you please try rephrasing that?"
        )

        if settings.debug:
            error_message += f"\n\n**Debug info:** {str(e)}"

        await cl.Message(content=error_message, author="Sam").send()


@cl.on_chat_end
async def on_chat_end() -> None:
    """Clean up when chat session ends.

    This function runs when a user closes the chat or disconnects.
    """
    # Session data is automatically cleared by Chainlit
    pass


@cl.on_settings_update
async def on_settings_update(settings_dict: dict) -> None:
    """Handle settings updates from the user.

    This function is called when a user updates their preferences
    in the settings panel.

    Args:
        settings_dict: Dictionary of updated settings.
    """
    # Could be used to customize agent behavior per user
    pass


# Optional: Add custom actions
@cl.action_callback("reschedule_booking")
async def on_reschedule_action(action: cl.Action) -> None:  # noqa: ARG001
    """Handle quick reschedule action.

    Args:
        action: The action triggered by the user.
    """
    await cl.Message(
        content="I can help you reschedule. What's your booking ID or phone number?", author="Sam"
    ).send()


@cl.action_callback("cancel_booking")
async def on_cancel_action(action: cl.Action) -> None:  # noqa: ARG001
    """Handle quick cancel action.

    Args:
        action: The action triggered by the user.
    """
    await cl.Message(
        content="I can help you cancel. What's your booking ID or phone number?", author="Sam"
    ).send()


if __name__ == "__main__":
    # This allows running the app directly with: python src/ui/chat_app.py
    from chainlit.cli import run_chainlit

    run_chainlit(__file__)
