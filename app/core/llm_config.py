import os
from typing import Optional, Tuple
from openai import AsyncOpenAI


LLM_PROVIDERS = {
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "models": {
            "agent_a": "deepseek-chat",
            "agent_b": "deepseek-chat",
        }
    },
    "siliconflow": {
        "name": "硅基流动",
        "base_url": "https://api.siliconflow.cn/v1",
        "models": {
            "agent_a": "Qwen/Qwen2.5-7B-Instruct",
            "agent_b": "Qwen/Qwen2.5-7B-Instruct",
        }
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "models": {
            "agent_a": "gpt-4o-mini",
            "agent_b": "gpt-4o",
        }
    },
}


class LLMConfig:
    provider: str = "deepseek"
    agent_a_api_key: str = ""
    agent_b_api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    agent_a_model: str = ""
    agent_b_model: str = ""

    @classmethod
    def from_env(cls):
        provider = os.getenv("LLM_PROVIDER", "deepseek")

        if provider == "deepseek":
            base_url = "https://api.deepseek.com"
            default_api_key = os.getenv("DEEPSEEK_API_KEY", "")
        elif provider == "siliconflow":
            base_url = "https://api.siliconflow.cn/v1"
            default_api_key = os.getenv("SILICONFLOW_API_KEY", "")
        elif provider == "openai":
            base_url = "https://api.openai.com/v1"
            default_api_key = os.getenv("OPENAI_API_KEY", "")
        else:
            raise ValueError(f"未知的 LLM 提供商: {provider}")

        config = cls()
        config.provider = provider
        config.base_url = base_url

        config.agent_a_api_key = os.getenv("AGENT_A_API_KEY") or default_api_key
        config.agent_b_api_key = os.getenv("AGENT_B_API_KEY") or default_api_key

        provider_config = LLM_PROVIDERS.get(provider, {})
        config.agent_a_model = os.getenv("AGENT_A_MODEL") or provider_config.get("models", {}).get("agent_a", "deepseek-chat")
        config.agent_b_model = os.getenv("AGENT_B_MODEL") or provider_config.get("models", {}).get("agent_b", "deepseek-chat")

        return config


class LLMClientFactory:

    @staticmethod
    def create_client(provider: Optional[str] = None, api_key: Optional[str] = None, base_url: Optional[str] = None) -> AsyncOpenAI:
        if provider and not api_key:
            config = LLMConfig.from_env()
            return AsyncOpenAI(api_key=config.agent_a_api_key, base_url=config.base_url)

        if api_key and base_url:
            return AsyncOpenAI(api_key=api_key, base_url=base_url)

        if api_key:
            return AsyncOpenAI(api_key=api_key)

        return AsyncOpenAI()

    @staticmethod
    def create_agent_a_client() -> AsyncOpenAI:
        config = LLMConfig.from_env()
        return AsyncOpenAI(api_key=config.agent_a_api_key, base_url=config.base_url)

    @staticmethod
    def create_agent_b_client() -> AsyncOpenAI:
        config = LLMConfig.from_env()
        return AsyncOpenAI(api_key=config.agent_b_api_key, base_url=config.base_url)

    @staticmethod
    def create_clients() -> Tuple[AsyncOpenAI, AsyncOpenAI]:
        config = LLMConfig.from_env()
        client_a = AsyncOpenAI(api_key=config.agent_a_api_key, base_url=config.base_url)
        client_b = AsyncOpenAI(api_key=config.agent_b_api_key, base_url=config.base_url)
        return client_a, client_b


def get_default_client() -> AsyncOpenAI:
    config = LLMConfig.from_env()
    return AsyncOpenAI(api_key=config.agent_a_api_key, base_url=config.base_url)


def get_agent_clients() -> Tuple[AsyncOpenAI, AsyncOpenAI]:
    config = LLMConfig.from_env()
    return LLMClientFactory.create_clients()
