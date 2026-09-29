"""Date arithmetic for recurring bills, plans, subscriptions and reminders."""

import calendar
from datetime import date, datetime, timedelta

from app.models.enums import Frequency, RepeatRule

_MONTHS = {
    Frequency.MONTHLY: 1,
    Frequency.QUARTERLY: 3,
    Frequency.HALF_YEARLY: 6,
    Frequency.YEARLY: 12,
    RepeatRule.MONTHLY: 1,
    RepeatRule.YEARLY: 12,
}
_DAYS = {Frequency.WEEKLY: 7, RepeatRule.WEEKLY: 7, RepeatRule.DAILY: 1}


def add_months(value: date, months: int) -> date:
    """Clamp to the month's last day, so Jan 31 + 1 month is Feb 28/29."""
    month_index = value.month - 1 + months
    year, month = value.year + month_index // 12, month_index % 12 + 1
    return value.replace(year=year, month=month, day=min(value.day, calendar.monthrange(year, month)[1]))


def advance(value: date | datetime, rule: Frequency | RepeatRule) -> date | datetime | None:
    """Next occurrence after `value`, or None for one-off rules."""
    if rule in _DAYS:
        return value + timedelta(days=_DAYS[rule])
    if rule in _MONTHS:
        return add_months(value, _MONTHS[rule])
    return None
