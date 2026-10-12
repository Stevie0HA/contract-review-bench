# Pre-registration (write this down BEFORE running the test set)

Question: does a larger model that needs two Sparks (about 200-400B, 4-bit) materially beat the best model that fits on one Spark
on contract review, at a pace that is practical overnight?

1. **Tuning:** prompts and settings are tuned on `dev/` only. `test/` is run once per arm, after tuning is frozen.
2. **Arms:** (a) best one-Spark model(s); (b) two-Spark big model; (c) small model plus pipeline (if built); (d) Claude as reference.
   Same prompt, temperature 0, 3 reps each.
3. **Two stages:** the criteria below are applied separately to `test/` (short) and `long/` (long packs). The long-pack result decides the question if they disagree, because real contract packs are long.
   **Primary metric:** recall on T3+T4 material findings (`recall_T3T4_material`).
4. **"Materially better" means all of (on `long/` unless stated):**
   - primary recall higher by at least 10 percentage points than the best one-Spark arm,
   - the 95% paired-bootstrap interval for that difference excludes 0,
   - false alarms per pack not worse by more than 0.5, and clean-pack false alarms not worse by more than 0.5,
   - throughput acceptable: the whole `long/` set (3 reps) in under 12 hours on the arm's hardware, measured from the token and time figures the runner records.
5. **If the criteria are not met, the conclusion is "no material gain"** and a second Spark has to be justified by something else.
6. Report all arms and all metrics, including the ones that do not favour the larger model. Do not switch the primary metric after seeing results.
7. Before accepting a low score, hand-check 20 misses and 20 false alarms for matching errors; fix the scorer on dev only.

Signed off by: ______________   Date: ____________
