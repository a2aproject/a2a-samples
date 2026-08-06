import logging
from a2a.client import A2AClient
from a2a.types import Task, Message, Part, SendMessageRequest, MessageSendParams, SendStreamingMessageRequest
import httpx
import asyncio
import uuid

logger = logging.getLogger(__name__)

class AgentConnector:
    """
    🔗 원격 A2A 에이전트에 연결하고, 작업 위임을 위한 통합 메서드를 제공합니다.

    Attributes:
        name (str): 원격 에이전트의 사람이 읽을 수 있는 식별자.
        client (A2AClient): 에이전트의 URL을 가리키는 HTTP 클라이언트.
    """

    def __init__(self, name: str, base_url: str):
        """
        특정 원격 에이전트용 커넥터를 초기화합니다.

        Args:
            name (str): 에이전트 식별자(예: "TellTimeAgent").
            base_url (str): HTTP 엔드포인트(예: "http://localhost:10000").
        """
        self.name = name
        self.httpx_client = httpx.AsyncClient(timeout=httpx.Timeout(120.0))
        self.client = A2AClient(url=base_url, httpx_client=self.httpx_client)

    async def send_task(
        self,
        message: str,
        session_id: str,
        task_id: str,
        user_id: str,
        task_callback: callable = None,  # 콜백은 선택적으로 받을 수 있게
    ):
        """
        텍스트 작업을 원격 A2A 에이전트에 스트리밍 방식으로 전송하고, 결과를 chunk 단위로 yield합니다.
        마지막 chunk의 텍스트를 저장해서 반환합니다.
        각 chunk의 구조와 값을 상세하게 로그로 남깁니다.
        """
        msg = Message(
            session_id=session_id,
            messageId=task_id,
            parts=[Part(type="text", text=message)],
            role="user",
            taskId=task_id,
            metadata={"user_id": user_id, "session_id": session_id}
        )
        params = MessageSendParams(message=msg)
        req = SendStreamingMessageRequest(
            id=task_id or str(uuid.uuid4()),
            params=params
        )
        try:
            async for response in self.client.send_message_streaming(req):
                event = response.root.result
                yield event
                if hasattr(event, 'final') and event.final:
                    break
        except asyncio.CancelledError:
            yield None
        except Exception as e:
            yield None