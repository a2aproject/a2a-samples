import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_get_agent_card():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/.well-known/agent.json")
    assert response.status_code == 200
    assert response.json()["name"] == "Real Estate Agent"

@pytest.mark.asyncio
async def test_unauthorized_task_request():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/a2a/tasks", json={})
    assert response.status_code == 401