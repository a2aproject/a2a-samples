from abc import abstractmethod
from typing import Any

from pydantic import BaseModel


class Memory(BaseModel):
    """Base class for memory."""
    @abstractmethod
    async def save(self, user_id: str, user_input: str, assistant_response: str) -> Any:
        pass

    @abstractmethod
    async def retrieve(self, query: str, user_id: str) -> list[dict]:
        pass
