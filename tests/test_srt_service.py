import sys
sys.path.insert(0, 'd:/Mycode/算法_agent/algorithm_agent')

import pytest
from app.services.srt_service import SRTService
from app.schemas.correction_mode import CorrectionMode


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
    service.pipeline = None

    with pytest.raises(ValueError, match="missing api key"):
        service.process_srt(SAMPLE_SRT, correction_mode=CorrectionMode.AGENT)


def test_process_srt_auto_mode_degraded():
    service = SRTService()
    service.agent_available = True

    def raise_agent_error(_):
        raise RuntimeError("mock llm error")

    service._correct_by_agent_sync = raise_agent_error
    final_srt, success, mode_meta = service.process_srt(
        SAMPLE_SRT,
        correction_mode=CorrectionMode.AUTO
    )
    assert success is True
    assert "O(n log n)" in final_srt
    assert "动态规划" in final_srt
    assert mode_meta["correction_mode"] == "auto"
    assert mode_meta["effective_mode"] == "rule"
    assert mode_meta["degraded"] is True


def test_process_srt_hybrid_auto_mode_degraded():
    service = SRTService()
    service.agent_available = True

    def raise_hybrid_error(_):
        raise RuntimeError("mock hybrid error")

    service._correct_by_hybrid_sync = raise_hybrid_error
    final_srt, success, mode_meta = service.process_srt(
        SAMPLE_SRT,
        correction_mode=CorrectionMode.HYBRID_AUTO
    )
    assert success is True
    assert "O(n log n)" in final_srt
    assert "动态规划" in final_srt
    assert mode_meta["correction_mode"] == "hybrid_auto"
    assert mode_meta["effective_mode"] == "rule"
    assert mode_meta["degraded"] is True


if __name__ == "__main__":
    test_process_srt_rule_mode()
    test_process_srt_agent_mode_missing_key()
    test_process_srt_auto_mode_degraded()
    test_process_srt_hybrid_auto_mode_degraded()
