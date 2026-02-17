import ast
import json
import os

import chainlit as cl
import engineio
import engineio.payload
from pipelines import process_file, process_query
from dotenv import load_dotenv

from albert import AsyncAlbertClient
from rag_core import get_config
from rag_core.mediatech import get_collection_name


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


async def send_collection_badges() -> None:
    """Send collection toggle badges as action buttons."""
    configured = rag_config.storage.collections
    if not configured:
        return

    active: list[int] = cl.user_session.get("active_collections") or []

    actions = []
    for col_id in configured:
        name = get_collection_name(col_id) or f"Collection {col_id}"
        is_active = col_id in active
        label = f"{'✓' if is_active else '✗'} {name}"
        actions.append(
            cl.Action(
                name="toggle_collection",
                payload={"id": col_id},
                label=label,
                description=f"Click to {'disable' if is_active else 'enable'} {name}",
            )
        )

    await cl.Message(
        content="📚 **Active collections** — click to toggle:",
        actions=actions,
    ).send()


@cl.action_callback("toggle_collection")
async def on_toggle_collection(action: cl.Action) -> None:
    """Toggle a collection on or off for RAG retrieval."""
    col_id = action.payload["id"]
    active: list[int] = cl.user_session.get("active_collections") or []

    if col_id in active:
        active.remove(col_id)
    else:
        active.append(col_id)

    cl.user_session.set("active_collections", active)

    name = get_collection_name(col_id) or f"Collection {col_id}"
    state = "enabled" if col_id in active else "disabled"
    await cl.Message(content=f"📚 **{name}** {state}").send()
    await send_collection_badges()


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

    # Show collection badges if any configured
    await send_collection_badges()


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

    # Handle attachments — ingest into Albert collection for RAG retrieval
    if message.elements:
        for element in message.elements:
            if element.path:
                try:
                    status = process_file(element.path, element.name)
                    await cl.Message(content=status).send()
                except Exception as e:
                    await cl.Message(
                        content=f"Error indexing '{element.name}': {e!s}"
                    ).send()

    # Retrieve relevant context using active collections
    active_collections: list[int] = cl.user_session.get("active_collections") or []
    query_kwargs: dict[str, object] = {}
    if active_collections:
        query_kwargs["collection_ids"] = active_collections
    retrieved_context = process_query(message.content, **query_kwargs)

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

    await msg.update()
