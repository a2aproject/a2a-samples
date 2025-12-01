from dotenv import load_dotenv
from typing import List, Dict
import traceback
import asyncio
import os

from mem0 import AsyncMemoryClient
from braintrust import current_span, traced

from memory.base import Memory

load_dotenv()

mem0 = AsyncMemoryClient(api_key=os.getenv("MEM0_API_KEY"))

class Mem0Memory(Memory):
    @traced
    async def retrieve(self, query: str, user_id: str) -> List[Dict]:
        """Retrieve relevant context from Mem0"""
        try:
            memories = await mem0.search(query=query, user_id=user_id)
            serialized_memories = ' '.join([mem["memory"] for mem in memories])
            context = [
                {
                    "role": "system", 
                    "content": f"Relevant information: {serialized_memories}"
                },
                {
                    "role": "user",
                    "content": query
                }
            ]
            current_span().log(metadata={"memory_retrieved": context, "query": query, "user_id": user_id})
            return context
        except Exception as e:
            current_span().log(metadata={"error": e, "traceback": traceback.format_exc()})
            return [{"role": "user", "content": query}]

    @traced
    async def save(self, user_id: str, user_input: str, assistant_response: str):
        """Save the interaction to Mem0"""
        try:
            interaction = [
                {
                "role": "user",
                "content": user_input
                },
                {
                    "role": "assistant",
                    "content": assistant_response
                }
            ]
            result = await mem0.add(interaction, user_id=user_id)
            current_span().log(metadata={"memory_saved": result, "user_id": user_id})
        except Exception as e:
            current_span().log(metadata={"error": e})
