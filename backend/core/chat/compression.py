from ..llm.provider import LLMProvider, Message

SUMMARY_PROMPT = (
    "Summarize the conversation so far in a concise paragraph. "
    "Preserve key facts, decisions, and context the user would need. "
    "Write in the same language the user has been using."
)


async def compress_history(
    messages: list[Message],
    llm: LLMProvider,
    keep_recent: int = 10,
) -> list[Message]:
    """Compress older messages into a summary, keeping recent ones intact.

    Returns a new message list: [system, summary_msg, ...recent_messages].
    """
    system_msgs = [m for m in messages if m.role == "system"]
    non_system = [m for m in messages if m.role != "system"]

    if len(non_system) <= keep_recent:
        return messages

    to_compress = non_system[:-keep_recent]
    to_keep = non_system[-keep_recent:]

    conversation_text = "\n".join(
        f"{m.role}: {m.content}" for m in to_compress if m.content
    )

    summary_response = await llm.generate(
        messages=[
            Message(role="system", content=SUMMARY_PROMPT),
            Message(role="user", content=conversation_text),
        ],
        max_tokens=500,
        temperature=0.3,
    )

    summary_msg = Message(
        role="system",
        content=f"[Conversation summary]: {summary_response.content}",
    )

    return system_msgs + [summary_msg] + to_keep
