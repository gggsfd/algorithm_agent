from dataclasses import dataclass, asdict
from typing import Dict, Literal, Optional


@dataclass
class CandidateCorrection:
    correct: str
    source: Literal[
        "dict",
        "rag",
        "pinyin",
        "asr_mapping",
        "candidate_dict",
        "candidate_asr_mapping",
        "candidate_pinyin",
    ]
    confidence: float
    method: str

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_prompt_fragment(self) -> str:
        return (
            f"[置信度:{self.confidence:.2f}] "
            f"「{self.correct}」（来源:{self.source}, {self.method}）"
        )


@dataclass
class EvidenceReport:
    candidates: Dict[str, CandidateCorrection]
    original_text: str
    domain: str
    item_id: Optional[int] = None

    def to_prompt_text(self) -> str:
        lines = ["【候选纠错列表】"]
        sorted_candidates = sorted(
            self.candidates.items(),
            key=lambda x: x[1].confidence,
            reverse=True
        )
        for i, (wrong, candidate) in enumerate(sorted_candidates, 1):
            lines.append(f"  {i}. 「{wrong}」→ {candidate.to_prompt_fragment()}")
        if not self.candidates:
            lines.append("  （无候选纠错）")
        return "\n".join(lines)
