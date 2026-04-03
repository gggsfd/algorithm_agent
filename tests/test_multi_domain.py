import sys
sys.path.insert(0, 'd:/Mycode/算法_agent/algorithm_agent')

from scripts.import_terms import list_supported_domains
from app.rag.retrieval import get_default_engine
from app.services.srt_service import SRTService


def test_supported_domains():
    domains = list_supported_domains()
    assert "algorithm" in domains
    assert "medical" in domains
    assert "legal" in domains
    assert "finance" in domains


def test_algorithm_domain_correction():
    engine = get_default_engine(domain="algorithm")
    result = engine.get_correction_dict("分制法和动态鬼话")
    assert result.get("分制法") == "分治法"
    assert result.get("动态鬼话") == "动态规划"


def test_medical_domain_correction():
    engine = get_default_engine(domain="medical")
    result = engine.get_correction_dict("星肌梗死需要啊司匹林")
    assert result.get("星肌梗死") == "心肌梗死"
    assert result.get("啊司匹林") == "阿司匹林"


def test_legal_domain_correction():
    engine = get_default_engine(domain="legal")
    result = engine.get_correction_dict("职责产权和聚证责任问题")
    assert result.get("职责产权") == "知识产权"
    assert result.get("聚证责任") == "举证责任"


def test_srt_service_domain_apply():
    service = SRTService()
    corrected = service._apply_corrections("资惨负债表和净力润", domain="finance")
    assert "资产负债表" in corrected
    assert "净利润" in corrected
