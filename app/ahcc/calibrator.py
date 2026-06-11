import json
import math
from pathlib import Path

from app.ahcc.feedback_store import FeedbackStore


class HierarchicalCalibrator:
    def __init__(self, feedback_store: FeedbackStore | None = None, params_path: str = "./data/feedback/platt_params.json"):
        self.params = {
            "dict": (1.0, 0.0),
            "asr_mapping": (1.2, -0.1),
            "rag": (1.5, -0.3),
            "pinyin": (2.0, -0.5),
        }
        self.store = feedback_store or FeedbackStore()
        self.params_path = params_path
        self._refit_threshold = 50
        self.load_params(params_path)
        self._restore_from_store()

    def calibrate(self, source: str, raw_score: float) -> float:
        a, b = self.params.get(source, (1.0, 0.0))
        calibrated = 1.0 / (1.0 + math.exp(-(a * raw_score + b)))
        return min(max(calibrated, 0.0), 1.0)

    def update(self, source: str, raw_score: float, calibrated_score: float, accepted: bool):
        self.store.append(source, raw_score, calibrated_score, accepted)
        total = self.store.get_total_count(source)
        if total >= self._refit_threshold and total % 10 == 0:
            self._refit(source)

    def _restore_from_store(self):
        for source in list(self.params):
            history = self.store.load_history(source, limit=200)
            if len(history) >= self._refit_threshold:
                self._refit_from_history(source, history)

    def _refit(self, source: str):
        history = self.store.load_history(source, limit=200)
        if len(history) >= self._refit_threshold:
            self._refit_from_history(source, history)

    def _refit_from_history(self, source: str, history: list[tuple[float, bool]]):
        try:
            import numpy as np
            from scipy.optimize import minimize
        except ImportError:
            return

        scores = np.array([score for score, _ in history])
        labels = np.array([1.0 if outcome else 0.0 for _, outcome in history])

        def nll(params):
            a, b = params
            probs = 1.0 / (1.0 + np.exp(-(a * scores + b)))
            probs = np.clip(probs, 1e-10, 1 - 1e-10)
            return -np.mean(labels * np.log(probs) + (1 - labels) * np.log(1 - probs))

        result = minimize(nll, x0=[1.0, 0.0], method="L-BFGS-B")
        self.params[source] = (float(result.x[0]), float(result.x[1]))
        self.save_params(self.params_path)

    def save_params(self, path: str | None = None):
        target = Path(path or self.params_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = {source: [a, b] for source, (a, b) in self.params.items()}
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_params(self, path: str | None = None):
        target = Path(path or self.params_path)
        if not target.exists():
            return
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return
        for source, values in data.items():
            if source in self.params and isinstance(values, list) and len(values) == 2:
                self.params[source] = (float(values[0]), float(values[1]))
