import ast
import json
import os

import chainlit as cl
import engineio
import engineio.payload
from context_loader import process_file
from dotenv import load_dotenv

from albert import AsyncAlbertClient
from rag_core import get_config


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


@cl.on_chat_start
def start_chat():
    # Use system prompt from config
    cl.user_session.set(
        "message_history",
        [{"role": "system", "content": rag_config.generation.system_prompt}],
    )


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

    # Handle attachments using context_loader factory
    file_content = ""
    if message.elements:
        for element in message.elements:
            if element.path:
                try:
                    file_content += process_file(element.path, element.name)
                except Exception as e:
                    file_content += f"\n\nError reading '{element.name}': {e!s}\n"

    user_message = message.content
    if file_content:
        user_message += file_content

    message_history.append({"role": "user", "content": user_message})

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

    await msg.update()
