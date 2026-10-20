from enum import Enum


class ProgressionMode(str, Enum):
    FREE = "FREE"
    SEQUENTIAL = "SEQUENTIAL"


class CompletionMode(str, Enum):
    SELF_LEARNING = "SELF_LEARNING"
    ADMIN_REVIEW = "ADMIN_REVIEW"
