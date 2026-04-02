from enum import Enum


class ActivityType(str, Enum):
    EMAIL = "EMAIL"
    CALL = "CALL"
    MEETING = "MEETING"


class ActivityDirection(str, Enum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
