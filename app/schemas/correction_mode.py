from enum import Enum


class CorrectionMode(str, Enum):
    RULE = "rule"
    AGENT = "agent"
    HYBRID = "hybrid"
