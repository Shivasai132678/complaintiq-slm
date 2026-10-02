"""REST contract, validation, persistence and SPA path containment."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from complaintiq.api import create_app
from complaintiq.service import ComplaintService


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    service = ComplaintService(str(tmp_path / "api.sqlite"))
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>ComplaintIQ application</html>")
    (dist / "assets").mkdir()
    (dist / "assets" / "main.js").write_text('console.log("app")')
    evaluation = tmp_path / "evaluation.json"
    evaluation.write_text('{"status":"measured","backend":"baseline","test_size":153}')
    return TestClient(create_app(service=service, static_dir=dist, evaluation_path=evaluation))


def test_api_workflow(client: TestClient) -> None:
    health = client.get("/api/health").json()
    assert health["backend"] == "baseline"
    assert health["training_status"] == "deferred"
    assert health["dataset_size"] == 990
    assert client.get("/api/complaints").json() == {"items": []}
    response = client.post(
        "/api/complaints",
        json={
            "text": "My credit card has a billing error and duplicate merchant charge",
            "backend": "baseline",
        },
    )
    assert response.status_code == 201
    record = response.json()
    assert record["backend"] == "baseline"
    assert client.get("/api/complaints").json()["items"][0]["id"] == record["id"]
    assert client.get("/api/analytics").json()["total"] == 1
    assert client.get("/api/evaluation").json()["status"] == "measured"


@pytest.mark.parametrize(
    "payload",
    [
        {"text": ""},
        {"text": " "},
        {"text": "a" * 6001},
        {"text": 42},
        {"text": "hello", "backend": "slm"},
        {"text": "hello", "model_path": "/private/secret"},
    ],
)
def test_api_rejects_invalid_input(client: TestClient, payload: dict) -> None:
    response = client.post("/api/complaints", json=payload)
    assert response.status_code == 422
    assert isinstance(response.json()["error"]["message"], str)
    assert client.get("/api/analytics").json()["total"] == 0


def test_batch_limits_and_save(client: TestClient) -> None:
    response = client.post(
        "/api/batch",
        json={
            "texts": ["I dispute this credit report information", "My checking account is frozen"],
            "backend": "baseline",
        },
    )
    assert response.status_code == 200
    assert response.json()["saved"] == 2
    assert len(response.json()["items"]) == 2
    assert client.post("/api/batch", json={"texts": ["hello"] * 21}).status_code == 422
    assert client.post("/api/batch", json={"texts": []}).status_code == 422
    assert client.post("/api/batch", json={"texts": ["a" * 6001]}).status_code == 422


def test_static_routes_and_missing_api(client: TestClient) -> None:
    assert "ComplaintIQ application" in client.get("/").text
    assert "ComplaintIQ application" in client.get("/analytics").text
    assert client.get("/assets/main.js").status_code == 200
    assert client.get("/assets/absent.js").status_code == 404
    assert client.get("/api/absent").status_code == 404
    assert client.get("/%2e%2e/evaluation.json").status_code == 404


def test_errors_do_not_expose_local_paths(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(text: str) -> dict:
        raise RuntimeError("/Users/private/secret.db failed")

    monkeypatch.setattr(client.app.state.service, "analyze", fail)
    response = client.post("/api/complaints", json={"text": "A complaint"})
    assert response.status_code == 503
    assert "/Users/private" not in response.text
    batch = client.post("/api/batch", json={"texts": ["A complaint"]}).json()
    assert batch["saved"] == 0
    assert "error" in batch["items"][0]


def test_router_errors_follow_consistent_contract(client: TestClient) -> None:
    response = client.post("/api/health")
    assert response.status_code == 405
    assert "GET" in response.headers["allow"]
    assert "error" in response.json()
