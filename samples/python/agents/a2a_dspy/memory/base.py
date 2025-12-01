from abc import ABC, abstractmethod
from typing import Any


class Memory(ABC):
    """Base class for memory."""
    @abstractmethod
    async def save(self, user_id: str, user_input: str, assistant_response: str) -> Any:
        pass

    @abstractmethod
    async def retrieve(self, query: str, user_id: str) -> list[dict]:
        pass
