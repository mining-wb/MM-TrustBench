# API 接口：evaluate、task 状态、history
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

# 在 conftest 已设 MM_TRUSTBENCH_TEST，故 database 会用内存库
from src.api import app

client = TestClient(app)


#====== ping ======
def test_ping():
    resp = client.get("/ping")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


#====== evaluate：缺参 400 ======
def test_evaluate_missing_image():
    resp = client.post("/api/v1/evaluate", json={"question": "图里有猫吗？"})
    assert resp.status_code == 400
    data = resp.json()
    assert data.get("code") == 400
    assert "图片" in (data.get("message") or "")


#====== evaluate：mock 流水线返回 200 ======
@patch("src.api._pipeline")
def test_evaluate_success(mock_pipeline):
    mock_pipeline.process.return_value = {
        "answer": "yes",
        "evidence": "I see a cat.",
        "self_check": "Evidence supports yes.",
    }
    resp = client.post(
        "/api/v1/evaluate",
        json={"question": "图里有猫吗？", "image_base64": "fake_base64_data"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("final_answer") == "yes"
    assert "evidence" in body
    assert "self_check" in body


#====== task 不存在 404 ======
def test_get_task_not_found():
    resp = client.get("/api/v1/task/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
    assert resp.json().get("code") == 404


#====== history 返回结构 ======
def test_history_returns_tasks():
    resp = client.get("/api/v1/history", params={"limit": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert "tasks" in data
    assert isinstance(data["tasks"], list)
