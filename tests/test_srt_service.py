import sys
sys.path.insert(0, 'd:/Mycode/算法_agent/algorithm_agent')

import pytest
from app.services.srt_service import SRTService
from app.schemas.correction_mode import CorrectionMode
import app.services.srt_service as srt_service_module


SAMPLE_SRT = """1
00:00:01,000 --> 00:00:03,000
下面讲一个欧根老根的问题

2
00:00:04,000 --> 00:00:06,000
动态鬼话是常用技巧
"""


def test_process_srt_rule_mode():
    service = SRTService()
    final_srt, success, mode_meta = service.process_srt(
        SAMPLE_SRT,
        correction_mode=CorrectionMode.RULE
    )
    assert success is True
    assert "O(n log n)" in final_srt
    assert "动态规划" in final_srt
    assert mode_meta["correction_mode"] == "rule"
    assert mode_meta["effective_mode"] == "rule"
    assert mode_meta["degraded"] is False


def test_process_srt_agent_mode_missing_key():
    service = SRTService()
    service.agent_available = False
    service._pipeline = None

    final_srt, success, mode_meta = service.process_srt(
        SAMPLE_SRT,
        correction_mode=CorrectionMode.AGENT
    )
    assert success is True
    assert "O(n log n)" in final_srt
    assert mode_meta["correction_mode"] == "agent"
    assert mode_meta["effective_mode"] == "rule"
    assert mode_meta["degraded"] is True


def test_process_srt_agent_mode_degraded():
    service = SRTService()
    service.agent_available = True

    def raise_agent_error(_):
        raise RuntimeError("mock llm error")

    service._correct_by_agent_sync = raise_agent_error
    final_srt, success, mode_meta = service.process_srt(
        SAMPLE_SRT,
        correction_mode=CorrectionMode.AGENT
    )
    assert success is True
    assert "O(n log n)" in final_srt
    assert "动态规划" in final_srt
    assert mode_meta["correction_mode"] == "agent"
    assert mode_meta["effective_mode"] == "rule"
    assert mode_meta["degraded"] is True


def test_process_srt_hybrid_mode_degraded():
    service = SRTService()
    service.agent_available = True

    def raise_hybrid_error(_):
        raise RuntimeError("mock hybrid error")

    service._correct_by_hybrid_sync = raise_hybrid_error
    final_srt, success, mode_meta = service.process_srt(
        SAMPLE_SRT,
        correction_mode=CorrectionMode.HYBRID
    )
    assert success is True
    assert "O(n log n)" in final_srt
    assert "动态规划" in final_srt
    assert mode_meta["correction_mode"] == "hybrid"
    assert mode_meta["effective_mode"] == "rule"
    assert mode_meta["degraded"] is True


def test_create_agent_pipeline_uses_dual_clients(monkeypatch):
    term_client = object()
    correction_client = object()

    monkeypatch.setattr(
        srt_service_module.LLMClientFactory,
        "create_clients",
        lambda: (term_client, correction_client),
    )

    service = SRTService()
    pipeline = service._create_agent_pipeline()

    assert pipeline.term_agent.llm_client is term_client
    assert pipeline.correction_agent.llm_client is correction_client
    assert pipeline.term_agent.min_confidence == SRTService.TERM_AGENT_MIN_CONFIDENCE


def test_ensure_correction_pipeline_uses_dual_clients(monkeypatch):
    term_client = object()
    correction_client = object()

    monkeypatch.setattr(
        srt_service_module.LLMClientFactory,
        "create_clients",
        lambda: (term_client, correction_client),
    )

    service = SRTService()
    service.agent_available = True

    pipeline = service._ensure_correction_pipeline()

    assert pipeline.term_agent.llm_client is term_client
    assert pipeline.correction_agent.llm_client is correction_client
    assert pipeline.use_evidence is True


if __name__ == "__main__":
    test_process_srt_rule_mode()
    test_process_srt_agent_mode_missing_key()
    test_process_srt_agent_mode_degraded()
    test_process_srt_hybrid_mode_degraded()
