from typing import List, Dict, Tuple, Optional
from openai import AsyncOpenAI
from app.agents.agent_a import AgentA
from app.agents.agent_b import AgentB
from app.core.constraint_checker import ConstraintChecker
from app.core.exceptions import AgentExecutionError, ConstraintCheckError
from app.core.llm_config import LLMConfig


class AgentPipeline:

    def __init__(self, llm_client=None, llm_config: Optional[LLMConfig] = None):
        self.config = llm_config or LLMConfig.from_env()

        if llm_client:
            self.agent_a = AgentA(llm_client, model_name=self.config.agent_a_model)
            self.agent_b = AgentB(llm_client, model_name=self.config.agent_b_model)
        else:
            client_a = AsyncOpenAI(
                api_key=self.config.agent_a_api_key,
                base_url=self.config.base_url
            )
            client_b = AsyncOpenAI(
                api_key=self.config.agent_b_api_key,
                base_url=self.config.base_url
            )
            self.agent_a = AgentA(client_a, model_name=self.config.agent_a_model)
            self.agent_b = AgentB(client_b, model_name=self.config.agent_b_model)

    async def process_chunk(self, subtitle_items: List[Dict]) -> Tuple[List[Dict], bool]:
        if not subtitle_items:
            return [], True

        original_text = " ".join([item.get("text", "") for item in subtitle_items])

        replacement_dict = await self.agent_a.analyze(original_text)

        if not replacement_dict:
            return [{"id": item["id"], "text": item["text"]} for item in subtitle_items], True

        corrected_items = await self.agent_b.correct(subtitle_items, replacement_dict)

        return corrected_items, True

    def process_chunk_sync(self, subtitle_items: List[Dict]) -> Tuple[List[Dict], bool]:
        if not subtitle_items:
            return [], True

        replacement_dict = self.agent_a._rule_based_fallback(
            " ".join([item.get("text", "") for item in subtitle_items])
        )

        if not replacement_dict:
            return [{"id": item["id"], "text": item["text"]} for item in subtitle_items], True

        corrected_items = self.agent_b._rule_based_correction(subtitle_items, replacement_dict)

        return corrected_items, True

    async def correct_subtitles(self, subtitle_items: List[Dict]) -> Tuple[List[Dict], bool]:
        return await self.process_chunk(subtitle_items)

    def correct_subtitles_sync(self, subtitle_items: List[Dict]) -> Tuple[List[Dict], bool]:
        return self.process_chunk_sync(subtitle_items)
