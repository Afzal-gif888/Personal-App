"""Short-term memory: the current conversation window and this run's working state.

It is rebuilt for every run from what the backend sends (the backend owns conversation storage)
and is never persisted by the Agent Core.
"""

from typing import Any

from app.schemas.memory import ConversationTurn

MAX_TURN_CHARS = 4000


class ShortTermMemory:
    def __init__(self, max_messages: int = 12, max_chars: int = 24_000) -> None:
        self.max_messages = max_messages
        self.max_chars = max_chars

    def window(self, history: list[ConversationTurn]) -> list[ConversationTurn]:
        """The most recent turns that fit the message and character budgets, oldest first."""
        turns = [t for t in history if t.role in ("user", "assistant") and t.content.strip()]
        kept: list[ConversationTurn] = []
        total = 0
        for turn in reversed(turns[-self.max_messages :] if self.max_messages else []):
            text = turn.content if len(turn.content) <= MAX_TURN_CHARS else turn.content[:MAX_TURN_CHARS] + " …"
            if total + len(text) > self.max_chars:
                break
            kept.append(ConversationTurn(role=turn.role, content=text))
            total += len(text)
        kept.reverse()
        # The Messages format needs strict user/assistant alternation starting with a user turn.
        merged: list[ConversationTurn] = []
        for turn in kept:
            if merged and merged[-1].role == turn.role:
                merged[-1] = ConversationTurn(role=turn.role, content=merged[-1].content + "\n\n" + turn.content)
            else:
                merged.append(turn)
        while merged and merged[0].role != "user":
            merged.pop(0)
        if merged and merged[-1].role == "user":
            # The new request becomes the next user turn; a dangling user turn would break alternation.
            merged.pop()
        return merged

    def to_messages(self, history: list[ConversationTurn]) -> list[dict[str, Any]]:
        return [{"role": t.role, "content": t.content} for t in self.window(history)]
