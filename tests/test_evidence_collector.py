import sys
sys.path.insert(0, 'd:/Mycode/算法_agent/algorithm_agent')

from app.agents.evidence_collector import EvidenceCollector


def test_evidence_collector_asr_mapping_channel():
    collector = EvidenceCollector(domain="algorithm")
    candidates = collector.collect("这个题目可以用动态鬼话和分制法")
    assert "动态鬼话" in candidates
    assert candidates["动态鬼话"].correct == "动态规划"
    assert candidates["动态鬼话"].source in {"dict", "asr_mapping", "rag"}
    assert "分制法" in candidates
    assert candidates["分制法"].correct == "分治法"


def test_evidence_collector_empty_text():
    collector = EvidenceCollector(domain="algorithm")
    assert collector.collect("") == {}


def test_evidence_collector_uses_updated_thresholds():
    collector = EvidenceCollector(domain="algorithm")
    assert collector.pinyin_threshold == 0.75
    assert collector.CONFIDENCE_WEIGHTS["rag"] == 0.85
    assert collector.CONFIDENCE_WEIGHTS["pinyin"] == 0.70
