from typing import Dict
import logging
from app.agents.agent_a import AgentA
from app.agents.evidence_collector import EvidenceCollector
from app.core.exceptions import AgentExecutionError
from app.schemas.candidate import EvidenceReport
from app.schemas.domain import Domain

logger = logging.getLogger(__name__)


PROMPT_ENHANCED_AGENT_A = """你是一个精确的字幕纠错裁判。

【背景知识】
以下是从专业算法领域词典中预检索到的候选纠错列表（按置信度排序）：

{candidate_list}

【字幕原文】
{original_text}

【你的任务】
1. 结合上述候选纠错列表，判断每个候选是否应该采纳
2. 忽略置信度过低（< 0.5）或明显错误的候选
3. 如果候选列表遗漏了明显错误（如常见的音近错误），可以补充
4. 只返回确认需要替换的词对

【输出格式】JSON:
{{"需要替换的词1": "正确词1", "需要替换的词2": "正确词2"}}

如果没有需要替换的，返回空字典 {{}}。
"""


class EnhancedAgentA(AgentA):
    def __init__(
        self,
        llm_client=None,
        model_name: str = "deepseek-chat",
        domain: str = Domain.ALGORITHM.value,
        min_confidence: float = 0.35,
    ):
        super().__init__(llm_client=llm_client, model_name=model_name)
        self.domain = domain
        self.min_confidence = min_confidence
        self._collector = EvidenceCollector(domain=domain)

    async def analyze_with_evidence(self, caption_text: str) -> EvidenceReport:
        candidates = self._collector.collect(caption_text)
        return EvidenceReport(
            candidates=candidates,
            original_text=caption_text,
            domain=self.domain,
        )

    async def analyze(self, caption_text: str) -> Dict[str, str]:
        if not caption_text or not caption_text.strip():
            return {}

        evidence = await self.analyze_with_evidence(caption_text)
        if not evidence.candidates:
            return {}

        if self.llm_client is None:
            logger.warning("LLM client is None, using rule-based fallback")
            return self._evidence_rule_based_fallback(evidence)

        logger.info("Calling LLM for analysis...")

        prompt = PROMPT_ENHANCED_AGENT_A.format(
            candidate_list=evidence.to_prompt_text(),
            original_text=caption_text,
        )

        try:
            response = await self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是一个精确的字幕纠错裁判。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            result = self._parse_json_response(response.choices[0].message.content)
            if not result:
                logger.warning("EnhancedAgentA JSON解析结果为空，使用规则纠错")
                return self._evidence_rule_based_fallback(evidence)
            return self._filter_by_confidence(result, evidence)
        except Exception as e:
            logger.warning(f"EnhancedAgentA 执行异常: {str(e)}，使用规则纠错")
            return self._evidence_rule_based_fallback(evidence)

    def _evidence_rule_based_fallback(self, evidence: EvidenceReport) -> Dict[str, str]:
        return {
            wrong: candidate.correct
            for wrong, candidate in evidence.candidates.items()
            if candidate.confidence >= 0.90
        }

    def _filter_by_confidence(
        self,
        llm_result: Dict[str, str],
        evidence: EvidenceReport,
    ) -> Dict[str, str]:
        return {
            wrong: correct
            for wrong, correct in llm_result.items()
            if wrong in evidence.candidates
            and evidence.candidates[wrong].confidence >= self.min_confidence
        }
