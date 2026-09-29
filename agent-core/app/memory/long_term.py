"""Long-term memory: a small, whitelisted set of stable user preferences.

Rules:
* Only keys in `MemoryKey` can be stored; each value is validated.
* Nothing is inferred from arbitrary conversation text. A fact is written only when the agent calls
  the `remember_preference` tool (subject to the approval policy), i.e. the user stated it.
* The durable copy lives in the backend's user preferences, written through the backend API.
"""

import re
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.backend.client import BackendClient
from app.backend.schemas import Preferences
from app.schemas.memory import MemoryFact, MemoryKey

_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

# Memory key -> backend preferences field (camelCase on the wire).
_BACKEND_FIELD = {
    MemoryKey.PREFERRED_STUDY_START: "preferredStudyStart",
    MemoryKey.PREFERRED_STUDY_END: "preferredStudyEnd",
    MemoryKey.DEFAULT_REMINDER_TIME: "defaultReminderTime",
    MemoryKey.DAILY_STUDY_GOAL_MINUTES: "dailyStudyGoalMinutes",
    MemoryKey.TIMEZONE: "timezone",
}


class MemoryValidationError(ValueError):
    pass


def validate_fact(key: MemoryKey, value: Any) -> Any:
    if key in (MemoryKey.PREFERRED_STUDY_START, MemoryKey.PREFERRED_STUDY_END, MemoryKey.DEFAULT_REMINDER_TIME):
        if not isinstance(value, str) or not _HHMM.match(value):
            raise MemoryValidationError(f"{key.value} must be a time like 18:30")
        return value
    if key == MemoryKey.DAILY_STUDY_GOAL_MINUTES:
        try:
            minutes = int(value)
        except (TypeError, ValueError):
            raise MemoryValidationError("daily_study_goal_minutes must be a number of minutes")
        if not 0 <= minutes <= 24 * 60:
            raise MemoryValidationError("daily_study_goal_minutes must be between 0 and 1440")
        return minutes
    if key == MemoryKey.TIMEZONE:
        try:
            ZoneInfo(str(value))
        except (ZoneInfoNotFoundError, ValueError):
            raise MemoryValidationError(f"Unknown timezone: {value}")
        return str(value)
    raise MemoryValidationError(f"{key} cannot be remembered")


def facts_from_preferences(prefs: Preferences) -> list[MemoryFact]:
    values = {
        MemoryKey.PREFERRED_STUDY_START: prefs.preferred_study_start,
        MemoryKey.PREFERRED_STUDY_END: prefs.preferred_study_end,
        MemoryKey.DEFAULT_REMINDER_TIME: prefs.default_reminder_time,
        MemoryKey.DAILY_STUDY_GOAL_MINUTES: prefs.daily_study_goal_minutes,
        MemoryKey.TIMEZONE: prefs.timezone,
    }
    return [MemoryFact(key=k, value=v, source="backend_preferences") for k, v in values.items() if v not in (None, "")]


class LongTermMemory:
    async def remember(self, backend: BackendClient, key: MemoryKey, value: Any) -> MemoryFact:
        clean = validate_fact(key, value)
        await backend.update_preferences({_BACKEND_FIELD[key]: clean})
        return MemoryFact(key=key, value=clean)
