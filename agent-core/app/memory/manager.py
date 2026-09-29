"""MemoryManager: assembles what the agent should remember for one run."""

from dataclasses import dataclass, field
from typing import Any

from app.backend.client import BackendClient
from app.memory.long_term import LongTermMemory, facts_from_preferences
from app.memory.short_term import ShortTermMemory
from app.schemas.memory import ConversationTurn, MemoryFact


@dataclass
class MemorySnapshot:
    history_messages: list[dict[str, Any]] = field(default_factory=list)
    facts: list[MemoryFact] = field(default_factory=list)
    currency: str = "INR"

    def facts_as_dict(self) -> dict[str, Any]:
        return {f.key.value: f.value for f in self.facts}


class MemoryManager:
    def __init__(self, short_term: ShortTermMemory, long_term: LongTermMemory) -> None:
        self.short_term = short_term
        self.long_term = long_term

    async def load(
        self, backend: BackendClient, *, conversation_id: str | None, history: list[ConversationTurn] | None
    ) -> MemorySnapshot:
        if history is None and conversation_id:
            # The backend owns conversation storage; fetch it rather than keeping our own copy.
            stored = await backend.get_conversation_messages(conversation_id)
            history = [ConversationTurn(role=m.role, content=m.content) for m in stored]
        prefs = await backend.get_preferences()
        return MemorySnapshot(
            history_messages=self.short_term.to_messages(history or []),
            facts=facts_from_preferences(prefs),
            currency=prefs.currency,
        )
