from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseAgent(ABC):
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """统一执行接口"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent 名称，只读属性"""
        pass

    @name.setter
    def name(self, value: str) -> None:
        raise AttributeError("name 属性是只读的")