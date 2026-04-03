from enum import Enum
from typing import Dict


class Domain(str, Enum):
    ALGORITHM = "algorithm"
    MEDICAL = "medical"
    LEGAL = "legal"
    FINANCE = "finance"


DOMAIN_LABELS: Dict[str, str] = {
    Domain.ALGORITHM.value: "计算机算法",
    Domain.MEDICAL.value: "医学",
    Domain.LEGAL.value: "法律",
    Domain.FINANCE.value: "金融",
}


def is_supported_domain(domain: str) -> bool:
    return domain in DOMAIN_LABELS
