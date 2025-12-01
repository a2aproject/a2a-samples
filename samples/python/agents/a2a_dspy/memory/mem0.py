from dotenv import load_dotenv
from typing import List, Dict
import traceback
import os

from mem0 import MemoryClient
from braintrust import current_span, traced

from memory.base import Memory

load_dotenv()

mem0 = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))

class Mem0Memory(Memory):
    @traced
    def retrieve(self, query: str, user_id: str) -> List[Dict]:
        """Retrieve relevant context from Mem0"""
        try:
            memories = mem0.search(query=query,  user_id=user_id)
            memory_list = memories
            serialized_memories = ' '.join([mem["memory"] for mem in memory_list])
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
            print(f"Error retrieving memories: {e} at {traceback.format_exc()}")
            return [{"role": "user", "content": query}]
    @traced
    def save(self, user_id: str, user_input: str, assistant_response: str):
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
            result = mem0.add(interaction, user_id=user_id)
            current_span().log(metadata={"memory_saved": result, "user_id": user_id})
            print(f"Memory saved successfully: {len(result.get('results', []))} memories added")
        except Exception as e:
            print(f"Error saving interaction: {e}")
    