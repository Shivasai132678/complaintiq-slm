# Scope-gate data

- `other_products.csv`: 2,400 public CFPB complaint narratives about products outside the supported taxonomy (400 each: mortgage, student loan, debt collection, consumer/vehicle loan, payday/personal loan, money transfer). Source: the same official CFPB December 2011 – April 2018 narrative archive (SHA-256 `9d4fabeb5db925ce…`), exact duplicates removed, ordered by a seed-42 hash of the complaint ID. Rows alternate between `tune` (used to train the gate) and `test` (held out).
- `unrelated_authored.csv`: 108 short, non-financial or off-topic complaints and prompts written for this project (restaurants, travel, utilities, chit-chat, prompt-injection attempts, other languages). Rows alternate `tune` / `test`. This is a small synthetic challenge set, not real traffic; only the `test` half is reported.

Evaluate with `.venv/bin/python -m scripts.evaluate_scope`.
