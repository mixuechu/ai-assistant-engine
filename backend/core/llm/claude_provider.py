import json
import anthropic
from typing import Any, AsyncGenerator, Optional

from .provider import LLMProvider, LLMResponse, Message, StreamChunk, ToolDefinition


class ClaudeProvider(LLMProvider):

    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        *,
        api_key: Optional[str] = None,
        vertex_project_id: Optional[str] = None,
        vertex_region: Optional[str] = None,
    ):
        if vertex_project_id:
            from anthropic import AsyncAnthropicVertex
            self.client = AsyncAnthropicVertex(
                project_id=vertex_project_id,
                region=vertex_region or "us-east5",
            )
        elif api_key:
            self.client = anthropic.AsyncAnthropic(api_key=api_key)
        else:
            raise ValueError(
                "ClaudeProvider requires either api_key or vertex_project_id"
            )
        self.model = model

    def _convert_messages(
        self, messages: list[Message]
    ) -> tuple[Optional[str], list[dict[str, Any]]]:
        system_prompt = None
        api_messages: list[dict[str, Any]] = []

        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
                continue

            if msg.role == "tool":
                api_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.tool_call_id,
                        "content": msg.content,
                    }],
                })
                continue

            if msg.role == "assistant" and msg.tool_calls:
                content: list[dict[str, Any]] = []
                if msg.content:
                    content.append({"type": "text", "text": msg.content})
                for tc in msg.tool_calls:
                    content.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["name"],
                        "input": tc.get("arguments", {}),
                    })
                api_messages.append({"role": "assistant", "content": content})
                continue

            api_messages.append({"role": msg.role, "content": msg.content})

        return system_prompt, api_messages

    def _convert_tools(self, tools: list[ToolDefinition]) -> list[dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.parameters,
            }
            for t in tools
        ]

    async def generate(
        self,
        messages: list[Message],
        tools: Optional[list[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        system_prompt, api_messages = self._convert_messages(messages)
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": api_messages,
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if tools:
            kwargs["tools"] = self._convert_tools(tools)

        response = await self.client.messages.create(**kwargs)

        content_text = ""
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                content_text += block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "arguments": block.input,
                })

        return LLMResponse(
            content=content_text,
            tool_calls=tool_calls,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            model=response.model,
            stop_reason=response.stop_reason,
        )

    async def generate_stream(
        self,
        messages: list[Message],
        tools: Optional[list[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[StreamChunk, None]:
        system_prompt, api_messages = self._convert_messages(messages)
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": api_messages,
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if tools:
            kwargs["tools"] = self._convert_tools(tools)

        current_tool_call: Optional[dict[str, Any]] = None
        tool_input_json = ""

        async with self.client.messages.stream(**kwargs) as stream:
            async for event in stream:
                if event.type == "content_block_start":
                    block = event.content_block
                    if block.type == "tool_use":
                        current_tool_call = {"id": block.id, "name": block.name}
                        tool_input_json = ""

                elif event.type == "content_block_delta":
                    delta = event.delta
                    if delta.type == "text_delta":
                        yield StreamChunk(type="text", content=delta.text)
                    elif delta.type == "input_json_delta":
                        tool_input_json += delta.partial_json

                elif event.type == "content_block_stop":
                    if current_tool_call is not None:
                        try:
                            current_tool_call["arguments"] = json.loads(
                                tool_input_json
                            ) if tool_input_json else {}
                        except json.JSONDecodeError:
                            current_tool_call["arguments"] = {}
                        yield StreamChunk(
                            type="tool_call", tool_call=current_tool_call
                        )
                        current_tool_call = None

                elif event.type == "message_stop":
                    yield StreamChunk(type="done")

    def count_tokens(self, text: str) -> int:
        return len(text) // 4
