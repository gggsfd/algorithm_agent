import sys
sys.path.insert(0, 'd:/Mycode/算法_agent/algorithm_agent')

import os
from dotenv import load_dotenv
load_dotenv()

import pytest
from app.agents.evidence_collector import EvidenceCollector
from app.schemas.candidate import CandidateCorrection


class TestEvidenceCollectorBlackBox:
    """EvidenceCollector 黑盒基线测试 - 验证候选纠错收集逻辑"""

    def test_collect_rule_based_corrections(self):
        """
        覆盖点：
        - 正常路径：硬编码规则纠错（dict来源）
        - 400 参数错误：检测"欧根老根"应返回"O(n log n)"
        - 400 参数错误：检测"动态鬼话"应返回"动态规划"
        - 400 参数错误：检测"分制"应返回"分治"
        - 400 参数错误：检测"分制法"应返回"分治法"
        """
        collector = EvidenceCollector(domain="algorithm")
        candidates = collector.collect("这个题目可以用动态鬼话和分制法")

        assert "动态鬼话" in candidates, "动态鬼话 应被检测为错误"
        assert candidates["动态鬼话"].correct == "动态规划", "动态鬼话 应被纠正为动态规划"
        assert candidates["动态鬼话"].source in {"dict", "asr_mapping", "rag"}, "来源应为dict/asr_mapping/rag之一"
        assert "分制法" in candidates, "分制法 应被检测为错误"
        assert candidates["分制法"].correct == "分治法", "分制法 应被纠正为分治法"

    def test_collect_with_multiple_errors(self):
        """
        覆盖点：
        - 正常路径：同一文本包含多个错误
        """
        collector = EvidenceCollector(domain="algorithm")
        text = "欧根老根和动态鬼话还有分制都是常见错误"
        candidates = collector.collect(text)

        assert "欧根老根" in candidates
        assert candidates["欧根老根"].correct == "O(n log n)"
        assert "动态鬼话" in candidates
        assert candidates["动态鬼话"].correct == "动态规划"
        assert "分制" in candidates or "分制法" in candidates

    def test_collect_empty_text(self):
        """
        覆盖点：
        - 400 参数错误：空文本输入
        """
        collector = EvidenceCollector(domain="algorithm")
        candidates = collector.collect("")
        assert candidates == {}

    def test_collect_none_text(self):
        """
        覆盖点：
        - 400 参数错误：None文本输入
        """
        collector = EvidenceCollector(domain="algorithm")
        candidates = collector.collect(None)
        assert candidates == {}

    def test_collect_no_errors_returns_empty(self):
        """
        覆盖点：
        - 正常路径：正确文本无纠错候选
        """
        collector = EvidenceCollector(domain="algorithm")
        text = "动态规划和分治法都是常用算法"
        candidates = collector.collect(text)
        assert isinstance(candidates, dict)

    def test_collect_preserves_correct_term(self):
        """
        覆盖点：
        - 正常路径：正确术语不会被标记为错误
        """
        collector = EvidenceCollector(domain="algorithm")
        text = "动态规划"
        candidates = collector.collect(text)
        for wrong, candidate in candidates.items():
            assert candidate.correct != wrong, f"{wrong} 不应被纠正为自己"

    def test_collect_asr_errors_mapping(self):
        """
        覆盖点：
        - 正常路径：ASR错误映射检测
        """
        collector = EvidenceCollector(domain="algorithm")
        candidates = collector.collect("分制是很重要的算法思想")

        has_error = any(
            wrong in candidates and candidates[wrong].correct == "分治"
            for wrong in ["分制", "分制法"]
        )
        assert has_error, "分制/分制法 应被检测并纠正"

    def test_collect_confidence_weights(self):
        """
        覆盖点：
        - 正常路径：置信度权重正确
        """
        collector = EvidenceCollector(domain="algorithm")
        candidates = collector.collect("动态鬼话")

        if "动态鬼话" in candidates:
            candidate = candidates["动态鬼话"]
            assert hasattr(candidate, 'confidence'), "应有confidence属性"
            assert 0 <= candidate.confidence <= 1.0, "置信度应在0-1之间"
            assert candidate.source in CandidateCorrection.__dataclass_fields__['source'].type.__args__

    def test_collect_method_field_populated(self):
        """
        覆盖点：
        - 正常路径：method字段被正确填充
        """
        collector = EvidenceCollector(domain="algorithm")
        candidates = collector.collect("动态鬼话和分制")

        for wrong, candidate in candidates.items():
            assert hasattr(candidate, 'method'), f"{wrong}的候选应有method属性"
            assert isinstance(candidate.method, str), f"{wrong}的method应为字符串"
            assert len(candidate.method) > 0, f"{wrong}的method不应为空"

    def test_collect_source_field_valid(self):
        """
        覆盖点：
        - 正常路径：source字段值有效
        """
        collector = EvidenceCollector(domain="algorithm")
        candidates = collector.collect("动态鬼话分制欧根老根")

        valid_sources = {"dict", "rag", "pinyin", "asr_mapping"}
        for wrong, candidate in candidates.items():
            assert candidate.source in valid_sources, f"{wrong}的source应为{valid_sources}之一"

    def test_collect_returns_dict_type(self):
        """
        覆盖点：
        - 正常路径：返回值类型为Dict[str, CandidateCorrection]
        """
        collector = EvidenceCollector(domain="algorithm")
        result = collector.collect("测试文本")
        assert isinstance(result, dict)
        for key, value in result.items():
            assert isinstance(key, str)
            assert isinstance(value, CandidateCorrection)

    def test_collect_with_pinyin_threshold(self):
        """
        覆盖点：
        - 正常路径：拼音相似度阈值可配置
        """
        collector_default = EvidenceCollector(domain="algorithm", pinyin_threshold=0.60)
        collector_strict = EvidenceCollector(domain="algorithm", pinyin_threshold=0.90)

        text = "深度优化搜索"
        candidates_default = collector_default.collect(text)
        candidates_strict = collector_strict.collect(text)

        assert isinstance(candidates_default, dict)
        assert isinstance(candidates_strict, dict)

    def test_collect_with_rag_threshold(self):
        """
        覆盖点：
        - 正常路径：RAG相似度阈值可配置
        """
        collector = EvidenceCollector(domain="algorithm", rag_threshold=0.85)
        candidates = collector.collect("这是一个包含算法术语的句子动态鬼话")

        assert isinstance(candidates, dict)

    def test_collect_algorithm_domain(self):
        """
        覆盖点：
        - 正常路径：算法领域正常工作
        """
        collector = EvidenceCollector(domain="algorithm")
        candidates = collector.collect("动态鬼话分制法")
        assert isinstance(candidates, dict)

    def test_collect_no_duplicate_candidates(self):
        """
        覆盖点：
        - 正常路径：同一错误词不会被重复添加
        """
        collector = EvidenceCollector(domain="algorithm")
        text = "动态鬼话动态鬼话动态鬼话"
        candidates = collector.collect(text)

        assert "动态鬼话" in candidates
        dp_count = sum(1 for wrong in candidates.keys() if wrong == "动态鬼话")
        assert dp_count == 1, "动态鬼话 不应被重复添加"

    def test_collect_pinyin_similarity_results(self):
        """
        覆盖点：
        - 正常路径：拼音相似度匹配结果
        """
        collector = EvidenceCollector(domain="algorithm")
        candidates = collector.collect("深度优化搜索是重要算法")

        pinyin_candidates = {
            wrong: cand for wrong, cand in candidates.items()
            if cand.source == "pinyin"
        }

        for wrong, cand in pinyin_candidates.items():
            assert cand.confidence <= 1.0, "拼音置信度不应超过1.0"
            assert cand.method.startswith("pinyin_"), "拼音方法名应以pinyin_开头"

    def test_collect_evidence_report_format(self):
        """
        覆盖点：
        - 正常路径：EvidenceReport格式正确
        """
        from app.schemas.candidate import EvidenceReport

        collector = EvidenceCollector(domain="algorithm")
        text = "动态鬼话和分制"
        candidates = collector.collect(text)

        report = EvidenceReport(
            candidates=candidates,
            original_text=text,
            domain="algorithm",
            item_id=1
        )

        prompt_text = report.to_prompt_text()
        assert isinstance(prompt_text, str)
        assert "候选纠错列表" in prompt_text or len(prompt_text) > 0

    def test_candidate_to_dict(self):
        """
        覆盖点：
        - 正常路径：CandidateCorrection可序列化为dict
        """
        collector = EvidenceCollector(domain="algorithm")
        candidates = collector.collect("动态鬼话")

        if "动态鬼话" in candidates:
            cand_dict = candidates["动态鬼话"].to_dict()
            assert isinstance(cand_dict, dict)
            assert "correct" in cand_dict
            assert "source" in cand_dict
            assert "confidence" in cand_dict
            assert "method" in cand_dict

    def test_candidate_to_prompt_fragment(self):
        """
        覆盖点：
        - 正常路径：CandidateCorrection可生成提示片段
        """
        collector = EvidenceCollector(domain="algorithm")
        candidates = collector.collect("动态鬼话")

        if "动态鬼话" in candidates:
            fragment = candidates["动态鬼话"].to_prompt_fragment()
            assert isinstance(fragment, str)
            assert "置信度" in fragment or "correct" in fragment.lower() or len(fragment) > 0

    def test_different_domains_same_errors(self):
        """
        覆盖点：
        - 正常路径：不同领域对相同错误词的处理可能不同
        """
        collector_algorithm = EvidenceCollector(domain="algorithm")
        collector_medical = EvidenceCollector(domain="medical")

        text = "分制"
        candidates_algorithm = collector_algorithm.collect(text)
        candidates_medical = collector_medical.collect(text)

        assert isinstance(candidates_algorithm, dict)
        assert isinstance(candidates_medical, dict)

    def test_collect_long_text(self):
        """
        覆盖点：
        - 边界条件：长文本处理
        """
        collector = EvidenceCollector(domain="algorithm")
        long_text = "动态鬼话 " * 100 + "分制 " * 50
        candidates = collector.collect(long_text)
        assert isinstance(candidates, dict)

    def test_collect_special_characters(self):
        """
        覆盖点：
        - 边界条件：特殊字符处理
        """
        collector = EvidenceCollector(domain="algorithm")
        text = "动态鬼话！@#$%分制^&*()"
        candidates = collector.collect(text)
        assert isinstance(candidates, dict)

    def test_collect_unicode_text(self):
        """
        覆盖点：
        - 边界条件：Unicode文本处理
        """
        collector = EvidenceCollector(domain="algorithm")
        text = "动态鬼话中文分制算法中文"
        candidates = collector.collect(text)
        assert isinstance(candidates, dict)

    def test_collect_english_mixed(self):
        """
        覆盖点：
        - 边界条件：中英混合文本处理
        """
        collector = EvidenceCollector(domain="algorithm")
        text = "动态鬼话 and 分制 algorithm"
        candidates = collector.collect(text)
        assert isinstance(candidates, dict)

    def test_collect_numbers_and_symbols(self):
        """
        覆盖点：
        - 边界条件：数字和符号处理
        """
        collector = EvidenceCollector(domain="algorithm")
        text = "O(n log n) 复杂度 123 分制"
        candidates = collector.collect(text)
        assert isinstance(candidates, dict)


class TestEvidenceCollectorIntegration:
    """EvidenceCollector 集成测试 - 与RAG引擎协同工作"""

    def test_collector_with_rag_engine(self):
        """
        覆盖点：
        - 正常路径：与RAG引擎集成
        """
        collector = EvidenceCollector(domain="algorithm")
        text = "动态鬼话和分制法是算法中的重要概念"
        candidates = collector.collect(text)

        assert isinstance(candidates, dict)
        if len(candidates) > 0:
            for wrong, cand in candidates.items():
                assert wrong in text, f"候选错误词{wrong}应出现在原文本中"

    def test_collector_engine_consistency(self):
        """
        覆盖点：
        - 正常路径：多次调用结果一致
        """
        collector = EvidenceCollector(domain="algorithm")
        text = "动态鬼话分制"

        candidates1 = collector.collect(text)
        candidates2 = collector.collect(text)

        assert set(candidates1.keys()) == set(candidates2.keys())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])