"""Domain enums. Values are lowercase snake_case strings on the wire and in the database."""

from enum import StrEnum


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskCategory(StrEnum):
    ACADEMIC = "academic"
    PERSONAL = "personal"
    FINANCIAL = "financial"
    CAREER = "career"
    GENERAL = "general"


class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class StudyPlanStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class StudySessionStatus(StrEnum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    MISSED = "missed"
    CANCELLED = "cancelled"


class EventType(StrEnum):
    CLASS = "class"
    MEETING = "meeting"
    PROJECT_MEETING = "project_meeting"
    TEAM_MEETING = "team_meeting"
    INTERVIEW = "interview"
    APPOINTMENT = "appointment"
    EXAM = "exam"
    DEADLINE = "deadline"
    PERSONAL = "personal"
    GENERAL = "general"
    OTHER = "other"


MEETING_EVENT_TYPES = (EventType.MEETING, EventType.PROJECT_MEETING, EventType.TEAM_MEETING, EventType.INTERVIEW)


class ReminderStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    SNOOZED = "snoozed"
    CANCELLED = "cancelled"


class RepeatRule(StrEnum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class Frequency(StrEnum):
    ONE_TIME = "one_time"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    HALF_YEARLY = "half_yearly"
    YEARLY = "yearly"


class BillCategory(StrEnum):
    ELECTRICITY = "electricity"
    UTILITIES = "utilities"
    INTERNET = "internet"
    PHONE = "phone"
    RENT = "rent"
    HOSTEL = "hostel"
    COLLEGE_FEES = "college_fees"
    EDUCATION = "education"
    SUBSCRIPTION = "subscription"
    ENTERTAINMENT = "entertainment"
    INSURANCE = "insurance"
    OTHER = "other"


class BillStatus(StrEnum):
    UPCOMING = "upcoming"
    DUE = "due"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentPlanStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ExpenseCategory(StrEnum):
    FOOD = "food"
    TRAVEL = "travel"
    EDUCATION = "education"
    SHOPPING = "shopping"
    BILLS = "bills"
    ENTERTAINMENT = "entertainment"
    HEALTH = "health"
    OTHER = "other"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class GoalCategory(StrEnum):
    ACADEMIC = "academic"
    FINANCIAL = "financial"
    CAREER = "career"
    PERSONAL = "personal"
    GENERAL = "general"


class GoalStatus(StrEnum):
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class DocumentStatus(StrEnum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    DELETED = "deleted"


class DocumentIndexStatus(StrEnum):
    """Whether a document's text is in the vector index (document search)."""

    PENDING = "pending"  # waiting to be indexed
    INDEXING = "indexing"
    INDEXED = "indexed"
    FAILED = "failed"  # can be retried
    UNSUPPORTED = "unsupported"  # no extractable text (images, scanned PDFs, office files)


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class AgentRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ToolCallStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    SKIPPED = "skipped"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class NotificationType(StrEnum):
    TASK_DEADLINE = "task_deadline"
    MEETING = "meeting"
    EVENT = "event"
    REMINDER = "reminder"
    BILL = "bill"
    PAYMENT = "payment"
    STUDY_SESSION = "study_session"
    AGENT_ACTION = "agent_action"
    APPROVAL = "approval"
    SYSTEM = "system"


class NotificationStatus(StrEnum):
    SCHEDULED = "scheduled"
    SENT = "sent"
    READ = "read"
    FAILED = "failed"
    CANCELLED = "cancelled"
