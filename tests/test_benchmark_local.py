"""Local benchmark reproducibility, token bounds and truthful result accounting."""

from pathlib import Path

import httpx
import pytest

from scripts.benchmark_local import benchmark, select_rows, summarize


def test_selection_is_balanced_and_stable() -> None:
    rows = select_rows(Path("data/validation.csv"))
    assert len(rows) == 27
    assert len({row["complaint_id"] for row in rows}) == 27
    assert rows == select_rows(Path("data/validation.csv"))
    from collections import Counter

    assert set(Counter((row["product"], row["issue"]) for row in rows).values()) == {3}
    assert all(len(row["text_sha256"]) == 64 for row in rows)


def test_incremental_benchmark_records_errors_and_bounds(tmp_path: Path) -> None:
    requests = []
    completions = 0

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        nonlocal completions
        payload = json.loads(request.content) if request.content else {}
        if request.url.path == "/apply-template":
            return httpx.Response(
                200, json={"prompt": "\n".join(m["content"] for m in payload["messages"])}
            )
        if request.url.path == "/tokenize":
            return httpx.Response(200, json={"tokens": list(range(len(payload["content"]) // 3))})
        if request.url.path == "/v1/chat/completions":
            requests.append(payload)
            completions += 1
            text = (
                '{"product":"Credit card","issue":"Billing disputes"}'
                if completions == 1
                else "not valid JSON"
            )
            return httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": text}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 300, "completion_tokens": 18},
                },
            )
        return httpx.Response(200, json={"status": "ok"})

    with httpx.Client(
        base_url="http://127.0.0.1:8504", transport=httpx.MockTransport(handler)
    ) as client:
        result = benchmark(
            "mock-model", tmp_path / "result.json", client=client, limit=2, monitor=False
        )
    assert result["completed"] == 2
    assert result["status"] == "complete"
    assert result["errors"] == 1
    assert result["json_schema_valid_rate"] == 0.5
    assert (tmp_path / "result.json").is_file()
    assert result["predictions"][0]["tokens_input"] == 300
    assert result["predictions"][1]["raw_generation"] == "not valid JSON"
    assert all(row["prompt_tokens_preflight"] <= 1856 for row in result["predictions"])
    assert all(
        request["cache_prompt"] is False and request["max_tokens"] == 128 for request in requests
    )
    assert all(
        request["chat_template_kwargs"] == {"enable_thinking": False} for request in requests
    )


def test_metric_errors_count_against_quality() -> None:
    predictions = [
        {
            "actual_product": "a",
            "actual_issue": "x",
            "product": "a",
            "issue": "x",
            "schema_valid": True,
            "latency_ms": 100,
            "tokens_input": 10,
            "tokens_output": 2,
        },
        {
            "actual_product": "b",
            "actual_issue": "y",
            "product": "Unknown",
            "issue": "Needs review",
            "schema_valid": False,
            "latency_ms": 300,
            "tokens_input": 0,
            "tokens_output": 0,
            "error": "invalid",
        },
    ]
    result = summarize(predictions)
    assert result["product"]["accuracy"] == 0.5
    assert result["joint_accuracy"] == 0.5
    assert result["errors"] == 1
    assert result["latency_ms_p50"] == 200
    assert result["latency_ms_p95"] == 290


def test_shared_excerpt_and_token_budget() -> None:
    import json

    from scripts.benchmark_local import bounded_messages

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        if request.url.path == "/apply-template":
            complaint = json.loads(payload["messages"][1]["content"])["complaint"]
            assert len(complaint) == 2000
            return httpx.Response(200, json={"prompt": "template"})
        return httpx.Response(200, json={"tokens": [0] * 1900})

    with httpx.Client(
        base_url="http://127.0.0.1:8504", transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(ValueError, match="budget"):
            bounded_messages(client, "long narrative " * 500, {"Credit card": ["Billing disputes"]})


def test_resource_summary_deltas_are_machine_level() -> None:
    from scripts.benchmark_local import resource_summary

    report = resource_summary(
        [
            {"server_rss_kib": "1000", "swap": "used = 3.0G"},
            {"server_rss_kib": "1200", "swap": "used = 3.5G"},
        ]
    )
    assert report["server_rss_change_kib"] == 200
    assert report["host_swap_change_bytes"] == 0.5 * 1024**3
    assert resource_summary([])["server_rss_peak_kib"] is None
    assert "entire machine" in report["caveat"]


def test_interrupt_keeps_completed_rows(tmp_path: Path) -> None:
    import json

    completions = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal completions
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path == "/apply-template":
            return httpx.Response(200, json={"prompt": "prompt"})
        if request.url.path == "/tokenize":
            return httpx.Response(200, json={"tokens": [1] * 100})
        completions += 1
        if completions == 2:
            raise KeyboardInterrupt()
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    output = tmp_path / "partial.json"
    with httpx.Client(
        base_url="http://127.0.0.1:8504", transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(KeyboardInterrupt):
            benchmark("mock", output, client=client, limit=2, monitor=False)
    report = json.loads(output.read_text())
    assert report["status"] == "interrupted"
    assert report["completed"] == 1
    assert len(report["predictions"]) == 1


def test_pair_schema_excludes_cross_product_combinations() -> None:
    from jsonschema import ValidationError, validate

    from scripts.benchmark_local import pair_schema

    taxonomy = {"Credit card": ["Billing", "Fees"], "Checking": ["Deposits"]}
    schema = pair_schema(taxonomy)
    for product, issues in taxonomy.items():
        for issue in issues:
            validate({"product": product, "issue": issue}, schema)
    validate({"product": "Unknown", "issue": "Needs review"}, schema)
    for invalid in [
        {"product": "Credit card", "issue": "Deposits"},
        {"product": "Credit card", "issue": "Billing", "extra": True},
        {"product": "Unknown", "issue": "Billing"},
        {"product": "Credit card"},
    ]:
        with pytest.raises(ValidationError):
            validate(invalid, schema)


def test_constrained_mode_is_explicit_and_sent_to_server(tmp_path: Path) -> None:
    import json

    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path == "/apply-template":
            return httpx.Response(200, json={"prompt": "prompt"})
        if request.url.path == "/tokenize":
            return httpx.Response(200, json={"tokens": [1] * 100})
        payload = json.loads(request.content)
        calls.append(payload)
        if payload["response_format"]["json_schema"]["name"] == "constraint_probe":
            return httpx.Response(
                200, json={"choices": [{"message": {"content": '{"schema_probe":"verified"}'}}]}
            )
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": '{"product":"Unknown","issue":"Needs review"}'}}
                ]
            },
        )

    with httpx.Client(
        base_url="http://127.0.0.1:8504", transport=httpx.MockTransport(handler)
    ) as client:
        report = benchmark(
            "mock",
            tmp_path / "constrained.json",
            client=client,
            limit=1,
            monitor=False,
            constrain_labels=True,
        )
    assert calls[-1]["response_format"]["type"] == "json_schema"
    assert len(calls[-1]["response_format"]["json_schema"]["schema"]["oneOf"]) == 10
    assert report["constrain_labels"] is True
    assert report["schema_enforcement"] == "verified_fixed_literal_probe"
    assert "runtime probe" in report["limitations"]
    assert report["response_format"] == calls[-1]["response_format"]


@pytest.mark.parametrize(
    "raw",
    ["ignored", "{}", '{"schema_probe":"ignored"}', '{"schema_probe":"verified","extra":true}'],
)
def test_schema_probe_refuses_silently_ignored_enforcement(raw: str) -> None:
    from scripts.benchmark_local import verify_schema_enforcement

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": raw}}]})

    with httpx.Client(
        base_url="http://127.0.0.1:8504", transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(ValueError, match="probe failed"):
            verify_schema_enforcement(client, "mock")
