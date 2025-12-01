from pydantic import BaseModel
from abc import abstractmethod
from typing import List, Dict

class Memory(BaseModel):
    @abstractmethod
    def save(self, user_id: str, user_input: str, assistant_response: str):
        pass

    @abstractmethod
    def retrieve(self, query: str, user_id: str) -> List[Dict]:
        pass
