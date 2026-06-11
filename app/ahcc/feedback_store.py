import json
from pathlib import Path


class FeedbackStore:
    def __init__(self, base_path: str = "./data/feedback"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def append(
        self,
        source: str,
        raw_score: float,
        calibrated_score: float,
        outcome: bool,
        correction_id: str | None = None,
    ):
        record = {
            "source": source,
            "raw_score": raw_score,
            "calibrated_score": calibrated_score,
            "outcome": outcome,
            "id": correction_id or "",
        }
        with (self.base_path / f"{source}.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def load_history(self, source: str, limit: int = 200) -> list[tuple[float, bool]]:
        path = self.base_path / f"{source}.jsonl"
        if not path.exists():
            return []
        records = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                records.append((float(row["raw_score"]), bool(row["outcome"])))
        return records[-limit:]

    def get_total_count(self, source: str) -> int:
        path = self.base_path / f"{source}.jsonl"
        if not path.exists():
            return 0
        with path.open("r", encoding="utf-8") as f:
            return sum(1 for _ in f)
