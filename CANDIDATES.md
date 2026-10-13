# Candidate models and run order

Written on 2026-10-13, before any Spark results exist, so the order and the decision rule cannot be shaped by outcomes.
The decision rule itself is in `PREREGISTRATION.md` and is unchanged.

| # | Model | Hardware needed | Notes |
|---|---|---|---|
| 1 | Qwen3.8 27B | 1 Spark | First run on a MacBook (dev set); rerun on the Spark as the baseline |
| 2 | Nemotron 3 Nano (30B) | 1 Spark | Fast comparison point |
| 3 | gpt-oss-120b | 1 Spark | Also run on an M2 Ultra 128 GB by an outside tester |
| 4 | Nemotron 3 Super (120B) | 1 Spark | Strong long-document candidate |
| 5 | A DeepSeek model that fits | 1 Spark | Only if a size fits and the licence is checked |
| 6 | GLM-5.3-Flash (320B, 4-bit) | 2 Sparks | Tests whether a second Spark earns its place |

## How each is run
- The same `dev`, then `test`, then `long` sets, through the same runner and settings.
- Three repeats per pack; record the model, quantisation, hardware, serving software and `--max-tokens`.
- Thinking models need a large `--max-tokens` (16000+). Check results for empty answers before scoring.
- Third-party serving kits are tried separately, with no confidential data on the machines.

## Decision rule (see PREREGISTRATION.md)
A model counts as materially better only if it beats the one-Spark winner by at least 10 points on material T3+T4 recall,
the 95% interval excludes zero, and false alarms are not worse by more than 0.5 per pack.

Models can be added later, but add them below the line with the date, and do not reorder this list after results exist.

---
