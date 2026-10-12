# Contract review benchmark (synthetic)

**Can your local model find the errors in a contract pack?** Run it on your own hardware, score it, and compare.

## Quick start (about 5 minutes to set up)
1. You need Python 3 and any model served on an OpenAI-compatible endpoint (Ollama, LM Studio, llama.cpp server, vLLM).
   Use a context of at least 32k tokens (48k+ for the `long` sets). Thinking models need a large `--max-tokens` (16000+).
2. Try the small set first:
   ```
   python run_model.py --set dev --base-url http://localhost:11434/v1 --model YOUR_MODEL --run mytest --reps 1 --concurrency 1 --max-tokens 16000
   python score.py --key dev/key/answer_key.json --results results/mytest --strict
   ```
3. Want a leaderboard entry? Run `test` (and `long` if you can) the same way and **send back only the `results/<run>/` folder**
   (open an issue or message me). Say what hardware, software and quantisation you used. Please try `--concurrency 8` if your setup can.
   I score it and add it to the table.

## Held-out sets
`test/` and `long/` ship **without answer keys** so that no model is tuned on them. `dev/` and `long-dev/` include keys for your own tuning.
Everything here is fictional; no real company, person or client document is used anywhere.


## About
Fictional contract packs with planted defects, decoys and clean packs, for comparing local models
(one Spark vs two, big vs small, quantised vs not) on contract and inspection-document review.
No real company, person or client document is used anywhere. Safe to share.

## Sets
| Folder | Packs | Findings | Size per pack | Use |
|---|---|---|---|---|
| `dev/` | 10 (2 clean) | 45 | about 3k tokens | tune prompts and settings, short packs |
| `test/` | 36 (6 clean) | 174 | about 3k tokens | final comparison, short packs |
| `long-dev/` | 6 (1 clean) | 38 | about 26k tokens (estimate) | tune settings for long packs |
| `long/` | 24 (4 clean) | 142 | about 26k tokens (estimate) | final comparison, long packs |

Token sizes are estimates (characters / 3.6); real tokenisers may give 30-35k for long packs, so allow a 48k+ context.
`python generate.py --length xlong` makes packs about 2.5x longer again.

## What is in a pack
Short packs: Supply Agreement (SA), Purchase Order (PO), Variation Order (VO), Inspection Release Certificate (CERT).
Long packs add a Technical Specification (TS, 600 numbered requirements plus test-pressure and mechanical-property tables),
Material Test Certificates (MTC), a 120-row spare-parts schedule (S6), an 80-row milestone schedule (S7) and a longer annex.
Every clause, table row and header has a printed reference label (6.1, S1.3, L.2, PT.2, C.4, TS.P2, M.3.3).

- **Tiers:** T1 one location (arithmetic, unsigned) - T2 two places in one document - T3 across documents -
  T4 subtle, buried or long-range (hold point downgraded, auto-renewal hidden in an annex, delivery shorter than the minimum
  lead time; in long packs also a spec revision mismatch, a test-pressure table entry that contradicts Schedule 2, a heat number
  that differs between certificates, a yield strength below the specified minimum, an arithmetic slip inside the 120-row
  spare-parts table, a last milestone after the long-stop date).
- **Material** = could change price, quantity, specification, liability, payment, inspection or legal validity.
- **Decoys** look odd but are fine (legitimate variation, unusual-but-consistent governing law, rounded total with a note,
  partial release with a note, calibration valid on the test day, high liability cap). Flagging one is a "decoy trap".
- **Clean packs** have no defects, so anything reported is a false alarm.

## Run it
```
python verify.py --set long-dev                                       # independent check of the key: 0 mismatches
python run_model.py --set long-dev --base-url http://HOST:8000/v1 --model NAME --run NAME-long-dev --reps 3 --concurrency 2
python score.py --key long-dev/key/answer_key.json --results results/NAME-long-dev --strict
python score.py --key dev/key/answer_key.json --results results/B --baseline results/A --strict   # paired difference + CI
python score.py --key dev/key/answer_key.json --selftest              # scorer sanity test
python generate.py --out mine --seed 99 --packs 20 --clean 3 --length long --prefix X   # fresh set with a new seed
```
`run_model.py` uses only the standard library and any OpenAI-compatible endpoint (vLLM, llama.cpp server, Ollama, LM Studio).
The held-out `test/` and `long/` keys are not published, so for those someone running it for you only needs to send back the `results/NAME/` folder; the answer key is not needed to run it.
It records tokens and seconds per request in each result file, so throughput (prefill and generation) comes for free.

## Scoring
A finding counts when its (doc, ref) matches a planted location; `--strict` also requires a keyword from the defect type in the text.
Reported with 95% bootstrap intervals over packs (reps averaged per pack): recall (all, material, T1-T4, and T3+T4 material),
false alarms per pack, decoy traps per pack, false alarms on clean packs.

## Validity checks done
- `verify.py` finds the planted defects by rule, reading only the documents, and also runs base-consistency tests
  that must never fire. It agrees with the key on all four sets: 76 packs, 0 mismatches. Nothing planted is missing and
  nothing unplanted is present.
- That checker found two accidental extra inconsistencies in the first release of the short set (13 of 36 test packs); they are fixed,
  and the short sets were regenerated. **Use only the sets in this version.**
- The first real run (Qwen3.8 27B, dev) exposed three more flaws, now fixed: variation orders had no signature block although the
  agreement requires signed variations; the Schedule 2 pressure column wording was ambiguous between minimum and exact; and one
  answer key lacked a second location. Sets regenerated, 0 mismatches. **Version 2 supersedes version 1 results.**
- Scorer self-test: oracle = 100% recall / 0 false alarms; random-half about 47%; noisy = traps counted; lazy = 0%.
- Runner tested end to end against a mock server for short and long packs.

## Limits (read before trusting a result)
- **Thinking models:** give them a large `--max-tokens` (16000+) or they can return empty answers; check results for empty files.
- **Location-based matching** is strict about labels. A model that finds the defect but cites a wrong label is scored as a miss;
  `--strict` also needs a keyword. Spot-check misses by hand on the first run to see whether the matching is too harsh.
- **Template text is cleaner than real contracts.** The 600 specification lines are generated, each topic used once, and are
  mutually consistent; real specifications are messier. Expect real-document performance to be lower.
- Each defect type recurs across packs with different values, and a model could learn the types. Keep the test seeds unseen while
  tuning (use dev), and regenerate with a new seed if they leak.
- Long packs mix prefill-heavy work with a small output, so they reward compute (prefill) more than memory bandwidth; short packs
  mostly test accuracy. Report both.

## Licence
MIT. Contributions and bug reports welcome: if a pack looks wrong, say which pack and which label.
