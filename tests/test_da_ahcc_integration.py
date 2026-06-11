import sys

sys.path.insert(0, "d:/Mycode/算法_agent/algorithm_agent")

from app.agents.correction_agent import CorrectionAgent
from app.agents.evidence_collector import EvidenceCollector
from app.agents.pipeline import CorrectionPipeline
from app.agents.term_agent import TermAgent
from app.ahcc.feedback_store import FeedbackStore
from app.ahcc.threshold_adaptor import ThresholdAdaptor
from app.domain_adapter.evidence_builder import DynamicEvidenceBuilder
from app.rag.retrieval import get_default_engine, register_engine
from app.rag.vector_store import VectorStore


def test_vector_store_load_dynamic_terms_registers_shared_engine(tmp_path):
    domain = "dynamic_test_da"
    store = VectorStore(persist_dir=str(tmp_path), domain=domain)
    store.load_dynamic_terms(
        terms={"自适应堆": {"category": "data_structure", "importance": 5}},
        asr_mapping={"字适应堆": "自适应堆"},
    )
    register_engine(domain, store)

    engine = get_default_engine(domain)

    assert engine.vector_store is store
    assert store.find_asr_errors("这里讲字适应堆") == {"字适应堆": "自适应堆"}


def test_evidence_collector_uses_injected_confidence_weights(tmp_path):
    domain = "dynamic_test_weights"
    store = VectorStore(persist_dir=str(tmp_path), domain=domain)
    store.load_dynamic_terms(
        terms={"自适应堆": {"category": "data_structure", "importance": 5}},
        asr_mapping={"字适应堆": "自适应堆"},
    )
    register_engine(domain, store)

    collector = EvidenceCollector(
        domain=domain,
        confidence_weights={"dict": 0.5, "asr_mapping": 0.42, "rag": 0.3, "pinyin": 0.2},
    )
    candidates = collector.collect("我们使用字适应堆")

    assert candidates["字适应堆"].confidence == 0.42


def test_feedback_store_and_threshold_state_are_persistent(tmp_path):
    feedback = FeedbackStore(base_path=str(tmp_path / "feedback"))
    feedback.append("dict", 0.8, 0.7, True)

    assert feedback.load_history("dict") == [(0.8, True)]
    assert feedback.get_total_count("dict") == 1

    state_path = tmp_path / "threshold_state.json"
    adaptor = ThresholdAdaptor(state_path=str(state_path))
    adaptor.adapt([False, False, True])
    restored = ThresholdAdaptor(state_path=str(state_path))

    assert restored.threshold == adaptor.threshold
    assert restored.acceptance_ema == adaptor.acceptance_ema


def test_dynamic_evidence_builder_outputs_compatible_keys():
    evidence = DynamicEvidenceBuilder().build(
        terms=[{"term": "动态数组", "category": "data_structure", "importance": 4}],
        asr_map={"动态组数": "动态数组"},
    )

    assert evidence["asr_map"] == evidence["asr_mapping"]
    assert "动态数组" in evidence["dict"]
    assert "动态数组" in evidence["rag"]


def test_pipeline_accepts_custom_evidence_collector():
    term_agent = TermAgent(llm_client=None, min_confidence=0.4)
    correction_agent = CorrectionAgent(llm_client=None, validate=False)
    collector = EvidenceCollector(confidence_weights={"dict": 1.0, "asr_mapping": 0.95, "rag": 0.85, "pinyin": 0.7})

    pipeline = CorrectionPipeline(
        term_agent=term_agent,
        correction_agent=correction_agent,
        use_evidence=True,
        evidence_collector=collector,
    )
    pipeline.set_min_confidence(0.55)

    assert pipeline._collector is collector
    assert term_agent.min_confidence == 0.55
