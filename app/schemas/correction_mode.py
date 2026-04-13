from enum import Enum


class CorrectionMode(str, Enum):
    RULE = "rule"
    AGENT = "agent"
    AUTO = "auto"
    HYBRID = "hybrid"
    HYBRID_AUTO = "hybrid_auto"
