import os
import json
import logging
from typing import List
import httpx
from a2a.types import AgentCard

logger = logging.getLogger(__name__)

class DiscoveryClient:
    """
    🔍 레지스트리 파일에 저장된 URL 목록을 읽고,
    각 URL의 /.well-known/agent.json 엔드포인트를 조회하여
    AgentCard(에이전트 메타데이터)를 가져오는 역할을 합니다.

    Attributes:
        registry_file (str): base URL(문자열) 목록이 담긴 JSON 파일 경로
        base_urls (List[str]): 로드된 에이전트 base URL 목록
    """

    def __init__(self, registry_file: str = None):
        """
        DiscoveryClient를 초기화합니다.

        Args:
            registry_file (str, optional): 레지스트리 JSON 파일 경로. None이면
            현재 utilities 폴더의 'agent_registry.json'을 기본값으로 사용합니다.
        """
        if registry_file:
            self.registry_file = registry_file
        else:
            self.registry_file = os.path.join(
                os.path.dirname(__file__),
                'agent_registry.json'
            )
        self.base_urls = self._load_registry()

    def _load_registry(self) -> List[str]:
        """
        레지스트리 JSON 파일을 읽어 URL 목록으로 파싱합니다.

        Returns:
            List[str]: 에이전트 base URL 목록
        """
        try:
            with open(self.registry_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"레지스트리 파일을 찾을 수 없습니다: {self.registry_file}")
        except json.JSONDecodeError:
            return []

    async def list_agent_cards(self) -> List[AgentCard]:
        """
        등록된 각 URL의 discovery endpoint를 비동기로 조회하여
        AgentCard 객체로 파싱합니다.

        Returns:
            List[AgentCard]: 정상적으로 가져온 AgentCard 리스트
        """
        cards: List[AgentCard] = []
        async with httpx.AsyncClient() as client:
            for base in self.base_urls:
                url = base.rstrip("/") + "/.well-known/agent.json"
                try:
                    response = await client.get(url, timeout=5.0)
                    response.raise_for_status()
                    card = AgentCard.model_validate(response.json())
                    cards.append(card)
                except Exception as e:
                    logger.warning(f"Failed to discover agent at {url}: {e}")
        return cards