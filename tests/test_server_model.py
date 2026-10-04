"""Local HTTP inference boundaries: model identity, schema, failures and caching."""

import json

import httpx
import pytest

from complaintiq.server_model import ServerSLMClassifier


def test_server_inference_validates_identity_output_and_context(tmp_path, monkeypatch):
    path = tmp_path / "test.gguf"
    path.write_bytes(b"GGUF")
    requests = []
    mode = {"value": "ok"}

    def handle(request):
        payload = json.loads(request.content) if request.content else {}
        requests.append((request.url.path, payload))
        if request.url.path == "/health":
            return httpx.Response(503 if mode["value"] == "down" else 200, json={"status": "ok"})
        if request.url.path == "/v1/models":
            return httpx.Response(
                200,
                json={"data": [{"id": "other.gguf" if mode["value"] == "switched" else str(path)}]},
            )
        if request.url.path == "/apply-template":
            return httpx.Response(200, json={"prompt": "prompt"})
        if request.url.path == "/tokenize":
            return httpx.Response(
                200, json={"tokens": [1] * (2000 if mode["value"] == "long" else 20)}
            )
        if mode["value"] == "down":
            return httpx.Response(503)
        content = '{"product":"Credit card","issue":"Billing"}'
        if mode["value"] == "invalid":
            content = '{"product":"Mortgage","issue":"Billing"}'
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 20, "completion_tokens": 8},
            },
        )

    real_client = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs),
    )
    model = ServerSLMClassifier(str(path), {"Credit card": ["Billing"]}, "http://127.0.0.1:8504")
    text = "Credit card billing. " * 150
    result = model.classify(text)
    assert result["input_truncated"] is True
    assert result["input_chars_used"] == 2000
    payload = requests[-1][1]
    assert len(json.loads(payload["messages"][1]["content"])["complaint"]) == 2000
    assert payload["response_format"]["json_schema"]["schema"]["oneOf"][0]["properties"]["issue"][
        "enum"
    ] == ["Billing"]
    assert model.classify(text)["cached"] is True
    assert model.classify(text)["tokens_output"] == 0
    model.check_health()
    mode["value"] = "switched"
    with pytest.raises(ValueError, match="no longer loaded"):
        model.check_health()
    mode["value"] = "down"
    with pytest.raises(httpx.HTTPStatusError):
        model.check_health()
    for value, error in (
        ("invalid", ValueError),
        ("long", ValueError),
        ("down", httpx.HTTPStatusError),
    ):
        mode["value"] = value
        with pytest.raises(error):
            model.classify(value)
        assert value not in model._cache
    with pytest.raises(ValueError, match="local HTTP"):
        ServerSLMClassifier(str(path), {}, "https://remote.example")


def test_api_uses_configured_slm_without_silent_backend_switch(tmp_path):
    from fastapi.testclient import TestClient

    from complaintiq.api import create_app
    from complaintiq.service import ComplaintService

    service = ComplaintService(str(tmp_path / "test.sqlite"))

    class Model:
        model_version = "fine-tuned.gguf"

        def classify(self, text):
            return {"product": "Credit card", "issue": "Billing disputes"}

    service.backend = "slm"
    service.model = Model()
    client = TestClient(create_app(service=service))
    assert client.get("/api/health").json()["slm_status"] == "ready"
    result = client.post("/api/complaints", json={"text": "A card billing dispute"})
    assert result.status_code == 201
    assert result.json()["backend"] == "slm"
    assert (
        client.post(
            "/api/complaints", json={"text": "A dispute", "backend": "baseline"}
        ).status_code
        == 422
    )
    assert (
        client.post("/api/batch", json={"texts": ["A dispute"], "backend": "baseline"}).status_code
        == 422
    )

    def unavailable():
        raise RuntimeError("Runtime disconnected at /private/model")

    service.model.check_health = unavailable
    health = client.get("/api/health")
    assert health.status_code == 503
    assert "/private/model" not in health.text
