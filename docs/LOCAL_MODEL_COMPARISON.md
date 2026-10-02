# Local model comparison

Measured October 2, 2026 on the user's **MacBook Air M1 with 8 GB unified memory**, while the ComplaintIQ application remained running at `127.0.0.1:8501` using its baseline backend.

**Qwen2.5-1.5B-Instruct is the selected candidate for later fine-tuning.** It classified this small validation sample more accurately than Qwen3.5-0.8B and followed the requested output structure more often without a label grammar. Neither model beat the trained baseline on joint classification. No fine-tuning has been performed, and the new application API still uses the baseline.

## Measured results

All rows below use the same 27 validation complaints and identical narrative excerpts. “Pair accuracy” requires both product and issue to match their reference labels. “Allowed output” requires exactly the two requested fields and an allowed product/issue combination; it does **not** mean the prediction is correct.

| Backend and decoding | Product accuracy | Pair accuracy | Allowed output | Errors | Inference median | Inference p95 |
|---|---:|---:|---:|---:|---:|---:|
| Trained TF-IDF/logistic regression | 88.89% (24/27) | 55.56% (15/27) | 100% | 0 | 0.762 ms | 1.135 ms |
| Qwen2.5-1.5B, JSON object only | 51.85% (14/27) | 25.93% (7/27) | 59.26% (16/27) | 11 | 1,005 ms | 1,522 ms |
| Qwen3.5-0.8B, JSON object only | 3.70% (1/27) | 0% (0/27) | 11.11% (3/27) | 24 | 755 ms | 1,017 ms |
| Qwen2.5-1.5B, verified pair schema | 77.78% (21/27) | **48.15% (13/27)** | 100% | 0 | **944 ms** | 1,390 ms |
| Qwen3.5-0.8B, verified pair schema | 59.26% (16/27) | 22.22% (6/27) | 100% | 0 | 646 ms | 875 ms |

The pair schema improved usable output for both models. Its 100% allowed-output rate reflects **runtime constrained decoding plus independent validation**, rather than an intrinsic model accuracy result. It allows the nine known product/issue pairs and the `Unknown`/`Needs review` pair. A grammar-valid answer can still classify the complaint incorrectly.

The JSON-object runs requested valid JSON without enforcing label pairs. Failures were retained as raw outputs and counted as missed predictions; they were not repaired or reinterpreted. Both models completed the runs without observed out-of-memory failures. This establishes operation at the measured workload and settings, not suitability for longer prompts or concurrent requests.

## Reproducible comparison protocol

- Selection: deterministic SHA-256 ordering, three complaints per product/issue class, nine classes, taken from the **validation** split. The untouched test split was not used for model choice.
- Selection hash: `10be03d897268a783a61531e1ad083e99db7e4267d4f941681bd4eea5ac9dcaf`.
- Input: identical first 2,000 characters per complaint, identical shared taxonomy and system prompt. Two of the 27 complaints were shortened. Model-specific chat templates differ; their input token counts are recorded independently.
- Budget: 2,048 context tokens, 128 output tokens, 64-token safety margin. Inputs above 1,856 preflight tokens fail explicitly rather than receiving model-specific clipping.
- Generation: temperature zero, seed 42, thinking disabled, result/prompt caching disabled, one inference slot. No LIME perturbations are included in these timings.
- Models: Q4_K_M GGUF files. Exact repositories, revisions, file sizes, hashes, llama.cpp build and launch flags are recorded in `artifacts/local_models_manifest.json`.
- Each verified-schema run first passed an unrelated fixed-literal constraint probe. Its raw response is saved under `schema_probe`. The installed server accepts the nested `response_format.json_schema.schema` envelope. An earlier envelope attempt was not enforced and is excluded from these completed constrained comparison reports.
- Inference timings cover the chat-completion HTTP request, including server prompt processing and generation. Separate end-to-end timing fields include token preflight. Loading, the constraint probe and memory-snapshot collection are excluded from the inference medians. Probe warm-up and differing host load can affect comparisons.

The baseline row uses the same 27 prefixes and model fitted only on `data/training.csv`. These validation results are separate from the 153-record held-out baseline evaluation in `artifacts/evaluation.json`, even though the two baseline pair accuracies happen to round to the same value.

## Memory observations

| Run | Highest sampled server RSS |
|---|---:|
| Qwen2.5-1.5B, JSON object | 1.203 GiB |
| Qwen3.5-0.8B, JSON object | 1.137 GiB |
| Qwen2.5-1.5B, verified pair schema | 1.417 GiB |
| Qwen3.5-0.8B, verified pair schema | 1.762 GiB |

These are sampled process RSS values, **not total model/GPU memory or a guaranteed peak**. Metal allocations on unified memory are not fully represented by RSS. Initial per-run samples occur after the server is loaded, and constrained runs sample after the constraint probe. Differences between these values do not establish which model requires less total memory.

The pre-load machine snapshot already reported **3,713.06 MiB (about 3.63 GiB) of swap in use**. Other Mac applications and the running demo contributed to host load. Machine-level swap counters cannot attribute memory use to one model. Both verified-schema runs recorded zero net host swap change between their first and last samples, but they began with approximately 4.24–4.25 GiB already used. Full raw memory snapshots and their caveats remain in the artifacts.

## Decision and remaining work

Retain Qwen2.5-1.5B as the next training candidate: on this run it traded about 0.30 seconds of median inference time for seven additional correct product/issue pairs compared with Qwen3.5-0.8B. Its raw output also matched the allowed schema more often. This is a practical choice from a small exploratory sample, not a general model ranking.

The Qwen2.5 weights are retained locally. The task-created Qwen3.5 download and its local download metadata were removed, freeing about 533 MB; its benchmark evidence remains available. Both benchmark model servers were stopped after testing.

The baseline remains the current application backend because it performs better on this task today. Later work must adapt and run the training workflow for the selected model, validate the exported checkpoint, evaluate the final chosen configuration once on the untouched test split, and connect the verified SLM to the application. Improved post-training accuracy is not guaranteed. The existing Qwen3-4B training assets remain prepared and unexecuted; they are not evidence that the selected 1.5B model has been trained.

## Evidence files

- `artifacts/local_models_manifest.json`: weights and runtime identity.
- `artifacts/local_baseline_validation.json`: same-sample baseline.
- `artifacts/local_qwen25_validation.json`, `artifacts/local_qwen35_validation.json`: JSON-object runs.
- `artifacts/local_qwen25_constrained_validation.json`, `artifacts/local_qwen35_constrained_validation.json`: runtime-probed pair-schema runs.
- `artifacts/local_preload_memory.json`, `artifacts/local_before_qwen35_memory.json`: host observations before relevant runs.
- `scripts/benchmark_local.py`, `tests/test_benchmark_local.py`: benchmark implementation and tests.
