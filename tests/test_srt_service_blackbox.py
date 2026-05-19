import sys
sys.path.insert(0, 'd:/Mycode/算法_agent/algorithm_agent')

import os
from dotenv import load_dotenv
load_dotenv()

import pytest
from app.services.srt_service import SRTService
from app.schemas.correction_mode import CorrectionMode
from app.core.srt_parser import SRTParser
from app.core.exceptions import SRTParseError


class TestSRTServiceBlackBox:
    """SRTService 黑盒基线测试 - 给定错误字幕，验证纠错输出"""

    SAMPLE_SRT_WITH_ERRORS = """1
00:00:01,000 --> 00:00:03,000
下面讲一个欧根老根的问题

2
00:00:04,000 --> 00:00:06,000
动态鬼话是常用技巧

3
00:00:07,000 --> 00:00:09,000
这个分制法很重要

4
00:00:10,000 --> 00:00:12,000
可以用贪心算法解决

5
00:00:13,000 --> 00:00:15,000
深度优化搜索是图算法
"""

    SAMPLE_SRT_MULTI_ERRORS_SAME_LINE = """1
00:00:01,000 --> 00:00:03,000
动态鬼话和分制还有欧根老根

2
00:00:04,000 --> 00:00:06,000
归排和快排都是分治法
"""

    SAMPLE_SRT_CORRECT_TEXT = """1
00:00:01,000 --> 00:00:03,000
动态规划是常用算法

2
00:00:04,000 --> 00:00:06,000
分治法也很重要
"""

    SAMPLE_SRT_EMPTY_TEXT = """1
00:00:01,000 --> 00:00:03,000


2
00:00:04,000 --> 00:00:06,000
有内容的字幕
"""

    def test_rule_mode_corrects_known_errors(self):
        """
        覆盖点：
        - 400 参数错误（已知错误类型）
        - 正常路径：已知错误词应被纠正
        测试场景：给包含"欧根老根"、"动态鬼话"、"分制"的字幕 → 验证输出包含"O(n log n)"、"动态规划"、"分治"
        """
        service = SRTService()
        final_srt, success, mode_meta = service.process_srt(
            self.SAMPLE_SRT_WITH_ERRORS,
            correction_mode=CorrectionMode.RULE
        )
        assert success is True, "纠错过程应成功"
        assert "O(n log n)" in final_srt, "欧根老根 应被纠正为 O(n log n)"
        assert "动态规划" in final_srt, "动态鬼话 应被纠正为 动态规划"
        assert "分治" in final_srt, "分制 应被纠正为 分治"
        assert "贪心算法" in final_srt, "贪心算法 不应被修改（已是正确形式）"
        assert mode_meta["correction_mode"] == "rule"
        assert mode_meta["effective_mode"] == "rule"
        assert mode_meta["degraded"] is False

    def test_rule_mode_multiple_errors_same_line(self):
        """
        覆盖点：
        - 正常路径：同一行包含多个错误词
        测试场景：一行包含"动态鬼话"、"分制"、"欧根老根"等多个错误 → 全部被纠正
        """
        service = SRTService()
        final_srt, success, mode_meta = service.process_srt(
            self.SAMPLE_SRT_MULTI_ERRORS_SAME_LINE,
            correction_mode=CorrectionMode.RULE
        )
        assert success is True
        assert "动态规划" in final_srt, "动态鬼话 应被纠正"
        assert "分治" in final_srt, "分制/分制法 应被纠正"
        assert "O(n log n)" in final_srt, "欧根老根 应被纠正"
        assert "归并排序" in final_srt, "归排 是归并排序的缩写"
        assert "快速排序" in final_srt, "快排 是快速排序的缩写"

    def test_rule_mode_preserves_correct_text(self):
        """
        覆盖点：
        - 正常路径：正确文本不被修改
        测试场景：输入正确字幕 → 输出与输入一致（除格式外）
        """
        service = SRTService()
        final_srt, success, mode_meta = service.process_srt(
            self.SAMPLE_SRT_CORRECT_TEXT,
            correction_mode=CorrectionMode.RULE
        )
        assert success is True
        assert "动态规划" in final_srt
        assert "分治法" in final_srt

    def test_rule_mode_returns_valid_srt_format(self):
        """
        覆盖点：
        - 正常路径：输出SRT格式正确
        测试场景：纠错后输出仍保持有效SRT格式
        """
        service = SRTService()
        final_srt, success, _ = service.process_srt(
            self.SAMPLE_SRT_WITH_ERRORS,
            correction_mode=CorrectionMode.RULE
        )
        assert "00:00:01,000 --> 00:00:03,000" in final_srt
        assert "00:00:04,000 --> 00:00:06,000" in final_srt
        assert final_srt.count("-->") == 5, "应有5个时间戳"
        blocks = final_srt.strip().split("\n\n")
        assert len(blocks) == 5, "应有5个字幕块"
        for i, block in enumerate(blocks):
            assert block.strip() != "", f"字幕块{i}不应为空"

    def test_agent_mode_without_api_key_fallback(self):
        """
        覆盖点：
        - 正常路径：AGENT模式无Pipeline时自动降级到RULE模式
        测试场景：AGENT模式 → _pipeline为None + agent_available=False → 自动降级到RULE模式
        """
        service = SRTService()
        service._pipeline = None
        service.agent_available = False

        final_srt, success, mode_meta = service.process_srt(
            self.SAMPLE_SRT_WITH_ERRORS,
            correction_mode=CorrectionMode.AGENT
        )
        assert success is True, "降级后应仍能处理"
        assert "O(n log n)" in final_srt, "降级到规则模式后仍应纠错"
        assert mode_meta["effective_mode"] == "rule"
        assert mode_meta["degraded"] is True, "应标记为降级"

    def test_hybrid_mode_without_api_key_fallback(self):
        """
        覆盖点：
        - 正常路径：HYBRID模式无Pipeline时自动降级到RULE模式
        测试场景：HYBRID模式 → _pipeline为None + agent_available=False → 自动降级到RULE模式
        """
        service = SRTService()
        service._pipeline = None
        service.agent_available = False

        final_srt, success, mode_meta = service.process_srt(
            self.SAMPLE_SRT_WITH_ERRORS,
            correction_mode=CorrectionMode.HYBRID
        )
        assert success is True, "降级后应仍能处理"
        assert "O(n log n)" in final_srt, "降级到规则模式后仍应纠错"
        assert mode_meta["effective_mode"] == "rule"
        assert mode_meta["degraded"] is True, "应标记为降级"

    def test_invalid_srt_format_raises_error(self):
        """
        覆盖点：
        - 400 参数错误：无效的SRT格式
        测试场景：无效SRT格式 → 抛出SRTParseError
        """
        service = SRTService()
        with pytest.raises(SRTParseError):
            service.process_srt("这不是有效的SRT格式")

    def test_empty_srt_raises_error(self):
        """
        覆盖点：
        - 400 参数错误：空SRT内容
        """
        service = SRTService()
        with pytest.raises(SRTParseError):
            service.process_srt("")

    def test_preserves_original_timestamps(self):
        """
        覆盖点：
        - 正常路径：时间戳保持不变
        """
        service = SRTService()
        final_srt, success, _ = service.process_srt(
            self.SAMPLE_SRT_WITH_ERRORS,
            correction_mode=CorrectionMode.RULE
        )
        assert "00:00:01,000 --> 00:00:03,000" in final_srt
        assert "00:00:04,000 --> 00:00:06,000" in final_srt
        assert "00:00:07,000 --> 00:00:09,000" in final_srt
        assert "00:00:10,000 --> 00:00:12,000" in final_srt
        assert "00:00:13,000 --> 00:00:15,000" in final_srt

    def test_preserves_subtitle_order(self):
        """
        覆盖点：
        - 正常路径：字幕顺序保持不变
        """
        service = SRTService()
        final_srt, success, _ = service.process_srt(
            self.SAMPLE_SRT_WITH_ERRORS,
            correction_mode=CorrectionMode.RULE
        )
        o_index = final_srt.find("O(n log n)")
        dp_index = final_srt.find("动态规划")
        assert o_index < dp_index, "字幕1应在字幕2之前"

    def test_correction_mode_string_value(self):
        """
        覆盖点：
        - 正常路径：字符串模式的correction_mode参数
        """
        service = SRTService()
        final_srt, success, mode_meta = service.process_srt(
            self.SAMPLE_SRT_WITH_ERRORS,
            correction_mode="rule"
        )
        assert success is True
        assert mode_meta["correction_mode"] == "rule"

    def test_unsupported_correction_mode_raises_error(self):
        """
        覆盖点：
        - 400 参数错误：不支持的纠错模式
        """
        service = SRTService()
        with pytest.raises(ValueError, match="Unsupported correction mode"):
            service.process_srt(self.SAMPLE_SRT_WITH_ERRORS, correction_mode="invalid_mode")

    def test_unsupported_domain_raises_error(self):
        """
        覆盖点：
        - 400 参数错误：不支持的领域
        """
        service = SRTService()
        with pytest.raises(ValueError, match="Unsupported domain"):
            service.process_srt(self.SAMPLE_SRT_WITH_ERRORS, domain="unsupported_domain")

    def test_process_srt_returns_three_values(self):
        """
        覆盖点：
        - 正常路径：返回值结构正确
        """
        service = SRTService()
        result = service.process_srt(self.SAMPLE_SRT_WITH_ERRORS)
        assert isinstance(result, tuple)
        assert len(result) == 3
        final_srt, success, mode_meta = result
        assert isinstance(final_srt, str)
        assert isinstance(success, bool)
        assert isinstance(mode_meta, dict)
        assert "correction_mode" in mode_meta
        assert "effective_mode" in mode_meta
        assert "degraded" in mode_meta


class TestSRTParserBlackBox:
    """SRTParser 黑盒测试 - 验证SRT解析的正确性"""

    def test_parse_valid_srt(self):
        """
        覆盖点：
        - 正常路径：解析有效SRT内容
        """
        parser = SRTParser()
        srt_content = """1
00:00:01,000 --> 00:00:03,000
第一行字幕

2
00:00:04,000 --> 00:00:06,000
第二行字幕
"""
        result = parser.parse(srt_content)
        assert len(result.items) == 2
        assert result.items[0]["id"] == 1
        assert result.items[0]["text"] == "第一行字幕"
        assert result.items[1]["id"] == 2
        assert result.items[1]["text"] == "第二行字幕"

    def test_parse_srt_with_multiple_lines_per_block(self):
        """
        覆盖点：
        - 正常路径：多行字幕块解析
        """
        parser = SRTParser()
        srt_content = """1
00:00:01,000 --> 00:00:03,000
第一行第一句
第一行第二句

2
00:00:04,000 --> 00:00:06,000
第二行字幕
"""
        result = parser.parse(srt_content)
        assert len(result.items) == 2
        assert result.items[0]["text"] == "第一行第一句 第一行第二句"

    def test_parse_invalid_srt_empty(self):
        """
        覆盖点：
        - 400 参数错误：空内容
        """
        parser = SRTParser()
        with pytest.raises(SRTParseError):
            parser.parse("")

    def test_parse_invalid_srt_no_blocks(self):
        """
        覆盖点：
        - 400 参数错误：无效格式无字幕块
        """
        parser = SRTParser()
        with pytest.raises(SRTParseError):
            parser.parse("这不是字幕格式")

    def test_parse_srt_timeline(self):
        """
        覆盖点：
        - 正常路径：解析为时间线格式
        """
        parser = SRTParser()
        srt_content = """1
00:00:01,000 --> 00:00:03,000
字幕文本
"""
        result = parser.parse_to_timeline(srt_content)
        assert len(result) == 1
        assert result[0]["timestamp_start"] == "00:00:01,000"
        assert result[0]["timestamp_end"] == "00:00:03,000"


class TestConstraintCheckerBlackBox:
    """ConstraintChecker 黑盒测试 - 验证约束检查逻辑"""

    def test_validate_item_count_mismatch(self):
        """
        覆盖点：
        - 400 参数错误：纠错后字幕数量不一致
        """
        from app.core.constraint_checker import ConstraintChecker, ConstraintCheckError

        original_items = [
            {"id": 1, "text": "原始文本1", "_timestamp_start": "a", "_timestamp_end": "b"},
            {"id": 2, "text": "原始文本2", "_timestamp_start": "c", "_timestamp_end": "d"},
        ]
        checker = ConstraintChecker(original_items)

        corrected_items = [
            {"id": 1, "text": "纠正文本1"},
        ]

        with pytest.raises(ConstraintCheckError, match="字幕数量不一致"):
            checker.validate(corrected_items)

    def test_validate_missing_id(self):
        """
        覆盖点：
        - 400 参数错误：缺少id字段
        """
        from app.core.constraint_checker import ConstraintChecker, ConstraintCheckError

        original_items = [
            {"id": 1, "text": "原始文本1", "_timestamp_start": "a", "_timestamp_end": "b"},
        ]
        checker = ConstraintChecker(original_items)

        corrected_items = [
            {"text": "纠正文本1"},
        ]

        with pytest.raises(ConstraintCheckError, match="缺少 id 字段"):
            checker.validate(corrected_items)

    def test_validate_empty_text(self):
        """
        覆盖点：
        - 400 参数错误：文本为空
        """
        from app.core.constraint_checker import ConstraintChecker, ConstraintCheckError

        original_items = [
            {"id": 1, "text": "原始文本1", "_timestamp_start": "a", "_timestamp_end": "b"},
        ]
        checker = ConstraintChecker(original_items)

        corrected_items = [
            {"id": 1, "text": "   "},
        ]

        with pytest.raises(ConstraintCheckError, match="文本为空"):
            checker.validate(corrected_items)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])