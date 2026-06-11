import json
from pathlib import Path


class ThresholdAdaptor:
    def __init__(
        self,
        initial_threshold: float = 0.65,
        min_threshold: float = 0.35,
        max_threshold: float = 0.90,
        alpha: float = 0.1,
        state_path: str = "./data/feedback/threshold_state.json",
    ):
        self.threshold = initial_threshold
        self.min_threshold = min_threshold
        self.max_threshold = max_threshold
        self.alpha = alpha
        self.state_path = state_path
        self.acceptance_ema = 0.5
        self.load_state()

    def adapt(self, outcomes: list[bool]) -> float:
        if not outcomes:
            return self.threshold
        acceptance_rate = sum(1 for item in outcomes if item) / len(outcomes)
        self.acceptance_ema = self.alpha * acceptance_rate + (1 - self.alpha) * self.acceptance_ema
        if self.acceptance_ema < 0.45:
            self.threshold = min(self.max_threshold, self.threshold + 0.02)
        elif self.acceptance_ema > 0.75:
            self.threshold = max(self.min_threshold, self.threshold - 0.02)
        self.save_state()
        return self.threshold

    def save_state(self):
        path = Path(self.state_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"threshold": self.threshold, "acceptance_ema": self.acceptance_ema}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_state(self):
        path = Path(self.state_path)
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return
        self.threshold = float(data.get("threshold", self.threshold))
        self.acceptance_ema = float(data.get("acceptance_ema", self.acceptance_ema))
