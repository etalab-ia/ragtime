import ast
import json
import os
import time
from typing import Optional

import chainlit as cl
import engineio
import engineio.payload
from chainlit.input_widget import Switch
from chainlit.types import ThreadDict
from dotenv import load_dotenv
from supabase import create_client
from supabase_auth.errors import AuthApiError

from albert import AsyncAlbertClient
from rag_facile.core import get_config
from rag_facile.core.mediatech import get_collection_name
from rag_facile.pipelines import process_query
from rag_facile.tracing import update_trace_with_response


# Increase the number of packets allowed in a single payload to prevent "Too
# many packets in payload" errors. This is especially helpful during streaming
# or when WebSockets are falling back to polling.
engineio.payload.Payload.max_decode_packets = 200

load_dotenv()

# Load RAG configuration
rag_config = get_config()

# Configure OpenAI (API credentials still from env vars)
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")
# Model comes from config with env var override
model = os.getenv("OPENAI_MODEL") or rag_config.generation.model

client = AsyncAlbertClient(api_key=api_key, base_url=base_url)

# Supabase Auth configuration (optional)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# Note: Chainlit auto-detects DATABASE_URL and uses ChainlitDataLayer (asyncpg)
# for persistence. No decorator needed - just set DATABASE_URL in .env.


@cl.password_auth_callback
async def auth_callback(username: str, password: str) -> Optional[cl.User]:
    """Authenticate against Supabase Auth (GoTrue)."""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return None  # Auth disabled when Supabase not configured
    sb = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    try:
        response = sb.auth.sign_in_with_password(
            {"email": username, "password": password}
        )
    except AuthApiError:
        return None  # Invalid credentials or Supabase unreachable
    user = response.user
    if not user:
        return None
    # Use the stable Supabase UUID as identifier for reliable user tracking.
    # Email can change; the UUID is immutable and unique across all users.
    #
    # display_name priority: user_metadata["display_name"] > email > login username.
    # Set display_name in Supabase Studio → Auth → Users → Edit user metadata
    # to show a friendly name (e.g. full name) instead of the email address.
    user_meta = user.user_metadata or {}
    display_name = user_meta.get("display_name") or user.email or username
    return cl.User(
        identifier=str(user.id),
        display_name=display_name,
        metadata={
            "role": "user",
            "provider": "supabase",
            "email": user.email or username,
        },
    )


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict) -> None:
    """Restore conversation history when resuming a thread."""
    # Defense-in-depth: verify the thread belongs to the current user.
    # Chainlit's data layer does not enforce per-user filtering on get_thread(),
    # so we guard here until RLS policies are added.
    current_user = cl.user_session.get("user")
    if current_user and thread.get("userIdentifier") != current_user.identifier:
        await cl.Message(
            content="Unauthorized: this thread does not belong to you."
        ).send()
        return

    # Rebuild message history from the persisted thread
    message_history = [
        {"role": "system", "content": rag_config.generation.system_prompt}
    ]
    for step in thread.get("steps", []):
        if step.get("type") == "user_message":
            message_history.append({"role": "user", "content": step.get("content", "")})
        elif step.get("type") == "assistant_message":
            message_history.append(
                {"role": "assistant", "content": step.get("content", "")}
            )
    cl.user_session.set("message_history", message_history)

    # Restore active collections from config (no persistence for toggles yet)
    active_collections = list(rag_config.storage.collections)
    cl.user_session.set("active_collections", active_collections)

    # Show collection toggles
    widgets = []
    for col_id in rag_config.storage.collections:
        name = get_collection_name(col_id) or f"Collection {col_id}"
        widgets.append(Switch(id=f"col_{col_id}", label=f"📚 {name}", initial=True))
    if widgets:
        await cl.ChatSettings(widgets).send()


# Example dummy function
def get_current_weather(location, unit="fahrenheit"):
    """Get the current weather in a given location"""
    if "paris" in location.lower():
        return json.dumps({"location": "Paris", "temperature": "22", "unit": "celsius"})
    elif "london" in location.lower():
        return json.dumps(
            {"location": "London", "temperature": "18", "unit": "celsius"}
        )
    elif "new york" in location.lower():
        return json.dumps(
            {"location": "New York", "temperature": "72", "unit": "fahrenheit"}
        )
    else:
        return json.dumps({"location": location, "temperature": "unknown"})


tools = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    },
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["location"],
            },
        },
    }
]


@cl.on_chat_start
async def start_chat():
    # Use system prompt from config
    cl.user_session.set(
        "message_history",
        [{"role": "system", "content": rag_config.generation.system_prompt}],
    )

    # Initialize active collections from config
    active_collections = list(rag_config.storage.collections)
    cl.user_session.set("active_collections", active_collections)

    # Show collection toggles in the settings panel (gear icon in header)
    widgets = []
    for col_id in rag_config.storage.collections:
        name = get_collection_name(col_id) or f"Collection {col_id}"
        widgets.append(Switch(id=f"col_{col_id}", label=f"📚 {name}", initial=True))
    if widgets:
        await cl.ChatSettings(widgets).send()


@cl.on_settings_update
async def on_settings_update(settings: dict) -> None:
    """Update active collections when the user toggles settings."""
    active = [
        col_id
        for col_id in rag_config.storage.collections
        if settings.get(f"col_{col_id}", True)
    ]
    cl.user_session.set("active_collections", active)


@cl.step(type="tool")
async def call_tool(tool_call, message_history):
    function_name = tool_call.function.name
    arguments = ast.literal_eval(tool_call.function.arguments)

    if function_name == "get_current_weather":
        current_weather = get_current_weather(
            location=arguments.get("location"),
            unit=arguments.get("unit"),
        )

        message_history.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": current_weather,
            }
        )

        return current_weather
    else:
        return "Function not found"


@cl.on_message
async def main(message: cl.Message):
    message_history = cl.user_session.get("message_history")

    # Retrieve relevant context using active collections
    active_collections: list[int] = cl.user_session.get("active_collections") or []
    _query_start = time.monotonic()
    retrieved_context = process_query(
        message.content, collection_ids=active_collections
    )

    user_content = message.content
    if retrieved_context:
        user_content = (
            "Use the following context to answer the user's question:\n\n"
            f"{retrieved_context}\n\n"
            f"Question: {message.content}"
        )

    message_history.append({"role": "user", "content": user_content})

    msg = cl.Message(content="")

    # Send an empty message to start the stream UI
    await msg.send()

    # Common generation parameters from config
    gen_params = {
        "stream": rag_config.generation.streaming,
        "temperature": rag_config.generation.temperature,
        "max_tokens": rag_config.generation.max_tokens,
    }

    # TODO: OpenAI SDK can't infer correct return type when stream parameter is a variable
    # This causes ty to report no-matching-overload error. Need to either:
    # 1. Split into separate streaming/non-streaming code paths with literal True/False
    # 2. Wait for OpenAI SDK to improve overload inference with runtime booleans
    stream = await client.chat.completions.create(  # ty: ignore[no-matching-overload]
        model=model,
        messages=message_history,
        tools=tools,
        tool_choice="auto",
        **gen_params,
    )

    cur_tool_calls = []

    try:
        async for part in stream:
            if not part.choices:
                continue

            # Handle new tool calls
            if part.choices[0].delta.tool_calls:
                for tool_call_delta in part.choices[0].delta.tool_calls:
                    index = tool_call_delta.index

                    if index == len(cur_tool_calls):
                        cur_tool_calls.append(tool_call_delta)
                    else:
                        # We are updating an existing tool call
                        if tool_call_delta.id:
                            cur_tool_calls[index].id = tool_call_delta.id
                        if tool_call_delta.function.name:
                            cur_tool_calls[index].function.name = (
                                cur_tool_calls[index].function.name or ""
                            ) + tool_call_delta.function.name
                        if tool_call_delta.function.arguments:
                            cur_tool_calls[index].function.arguments = (
                                cur_tool_calls[index].function.arguments or ""
                            ) + tool_call_delta.function.arguments

            # Handle content
            if part.choices[0].delta.content:
                token = part.choices[0].delta.content
                await msg.stream_token(token)
    except json.JSONDecodeError:
        # Albert API occasionally sends malformed SSE events; continue
        # with whatever content was streamed so far.
        pass

    # We are done with the first stream

    if cur_tool_calls:
        # We have tool calls to execute
        message_history.append(
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                        },
                    }
                    for tool_call in cur_tool_calls
                ],
            }
        )

        # Execute tools
        for tool_call in cur_tool_calls:
            await call_tool(tool_call, message_history)

        # Now we need to get the final response from the model (uses config values)
        stream_post_tool = await client.chat.completions.create(
            model=model,
            messages=message_history,
            **gen_params,
        )

        # Type ignore: SDK can't infer stream type when stream parameter is variable
        async for part in stream_post_tool:  # type: ignore[union-attr]
            if not part.choices:
                continue
            if part.choices[0].delta.content:
                token = part.choices[0].delta.content
                await msg.stream_token(token)

    # Add assistant response to history for proper conversation continuity
    message_history.append({"role": "assistant", "content": msg.content})

    # Update trace with LLM response and latency
    update_trace_with_response(msg.content, _query_start)

    await msg.update()
