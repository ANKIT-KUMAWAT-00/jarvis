"""
Integration tests for JARVIS FastAPI REST Endpoints.
"""

import pytest
from starlette.testclient import TestClient
from backend.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_api_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["agent_name"] == "JARVIS"
    assert "available_tools" in data
    assert "available_skills" in data
    assert "system_info" in data


def test_api_skills(client):
    response = client.get("/api/skills")
    assert response.status_code == 200
    skills = response.json()
    assert len(skills) >= 5
    skill_names = [s["name"] for s in skills]
    assert "coding" in skill_names
    assert "filesystem" in skill_names


def test_api_chat(client):
    response = client.post("/api/chat", json={"prompt": "Hello JARVIS"})
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "SUCCESS"
    assert "Sir" in data["response"]


def test_api_remember_and_get_memories(client):
    # Store memory
    res_rem = client.post("/api/remember", json={"fact": "Prefers automated regression testing", "category": "preference"})
    assert res_rem.status_code == 200
    assert res_rem.json()["status"] == "persisted"

    # Retrieve memory
    res_get = client.get("/api/memory?category=preference")
    assert res_get.status_code == 200
    memories = res_get.json()
    assert any("automated regression testing" in m["content"] for m in memories)


def test_api_task_lifecycle(client):
    # Create task
    res_create = client.post("/api/tasks", json={"title": "Run security scan", "description": "Audit boundaries"})
    assert res_create.status_code == 200
    task_data = res_create.json()
    assert task_data["task_id"].startswith("#J-")

    # List tasks
    res_list = client.get("/api/tasks")
    assert res_list.status_code == 200
    tasks = res_list.json()
    assert any(t["task_id"] == task_data["task_id"] for t in tasks)


def test_api_interrupt(client):
    response = client.post("/api/interrupt")
    assert response.status_code == 200
    assert response.json()["status"] == "interrupted"
