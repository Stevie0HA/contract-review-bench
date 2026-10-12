#!/usr/bin/env python3
"""Score model findings against the answer key.

  python score.py --key test/key/answer_key.json --results results/runA
  python score.py --key test/key/answer_key.json --results results/runB --baseline results/runA
  python score.py --key dev/key/answer_key.json --selftest

Model output per pack: {"findings":[{"doc":"SA","ref":"6.1","issue":"..."}]}  (file: <pack>.rep<k>.json)
A finding scores when its (doc, ref) matches a planted location. In --strict mode its text must also
contain one of the finding's keywords. Matching a decoy location (and nothing planted) is a decoy trap.
"""
import argparse, glob, json, os, random, re, statistics, sys

ALIAS = {"SUPPLYAGREEMENT": "SA", "AGREEMENT": "SA", "PURCHASEORDER": "PO", "VARIATIONORDER": "VO",
         "CERTIFICATE": "CERT", "IRC": "CERT", "INSPECTIONRELEASECERTIFICATE": "CERT",
         "TECHNICALSPECIFICATION": "TS", "SPECIFICATION": "TS", "SPEC": "TS",
         "MATERIALTESTCERTIFICATES": "MTC", "MATERIALTESTCERTIFICATE": "MTC", "MILLCERT": "MTC"}


def ndoc(s):
    s = re.sub(r"[^A-Za-z]", "", str(s)).upper()
    return ALIAS.get(s, s)


def nref(s):
    s = re.sub(r"\s+", "", str(s)).upper().replace("CLAUSE", "").replace("SCHEDULE", "S")
    return s.strip(".")


def refs_of(f):
    raw = f.get("ref", "")
    parts = raw if isinstance(raw, list) else re.split(r"[,;/&]|\band\b", str(raw))
    return {nref(p) for p in parts if str(p).strip()}


def loc_set(locs):
    return {(ndoc(d), nref(r)) for d, r in locs}


def score_pack(pk, findings, strict):
    planted = [(f, loc_set(f["locs"])) for f in pk["findings"]]
    decoys = [loc_set(dd["locs"]) for dd in pk["decoys"]]
    matched = {}; fp = 0; trap = 0; dup = 0
    for mf in findings:
        doc = ndoc(mf.get("doc", "")); rs = refs_of(mf)
        text = (str(mf.get("issue", "")) + " " + str(mf.get("description", ""))).lower()
        hit = None
        for pf, ls in planted:
            if any((doc, r) in ls for r in rs):
                if strict and not any(k in text for k in pf["keywords"]): continue
                hit = pf; break
        if hit is not None:
            if hit["id"] in matched: dup += 1
            else: matched[hit["id"]] = hit
            continue
        if any(any((doc, r) in ls for r in rs) for ls in decoys): trap += 1
        fp += 1
    return dict(pack=pk["pack"], clean=pk["clean"], matched=set(matched), fp=fp, trap=trap, dup=dup,
                n_findings=len(findings))


def load_results(path, key_packs):
    out = {}
    for pk in key_packs:
        reps = []
        for fn in sorted(glob.glob(os.path.join(path, f"{pk['pack']}.rep*.json"))):
            try:
                reps.append(json.load(open(fn)))
            except Exception:
                reps.append({"findings": [], "parse_error": True})
        out[pk["pack"]] = reps
    return out


def metrics(per_pack, key_packs, idx):
    """per_pack: {pack: [scored rep dicts]}; idx: list of pack names (with repeats for bootstrap)."""
    kp = {p["pack"]: p for p in key_packs}
    tot = dict(n=0, tp=0, n_m=0, tp_m=0, n34m=0, tp34m=0, fp=0, trap=0, packs=0, clean_fp=0, clean_n=0)
    tier = {t: [0, 0] for t in (1, 2, 3, 4)}
    for name in idx:
        reps = per_pack[name]
        if not reps: continue
        R = len(reps)
        for f in kp[name]["findings"]:
            hit = sum(1 for r in reps if f["id"] in r["matched"]) / R
            tot["n"] += 1; tot["tp"] += hit; tier[f["tier"]][0] += 1; tier[f["tier"]][1] += hit
            if f["material"]: tot["n_m"] += 1; tot["tp_m"] += hit
            if f["material"] and f["tier"] >= 3: tot["n34m"] += 1; tot["tp34m"] += hit
        fp = sum(r["fp"] for r in reps) / R; tr = sum(r["trap"] for r in reps) / R
        tot["fp"] += fp; tot["trap"] += tr; tot["packs"] += 1
        if kp[name]["clean"]: tot["clean_fp"] += fp; tot["clean_n"] += 1
    div = lambda a, b: (a / b) if b else float("nan")
    res = {"recall_all": div(tot["tp"], tot["n"]), "recall_material": div(tot["tp_m"], tot["n_m"]),
           "recall_T3T4_material": div(tot["tp34m"], tot["n34m"]),
           "false_alarms_per_pack": div(tot["fp"], tot["packs"]), "decoy_traps_per_pack": div(tot["trap"], tot["packs"]),
           "clean_pack_false_alarms": div(tot["clean_fp"], tot["clean_n"])}
    for t in (1, 2, 3, 4): res[f"recall_T{t}"] = div(tier[t][1], tier[t][0])
    return res


def evaluate(key, resdir, strict):
    raw = load_results(resdir, key["packs"])
    scored = {}
    for pk in key["packs"]:
        scored[pk["pack"]] = [score_pack(pk, r.get("findings", []) or [], strict) for r in raw[pk["pack"]]]
    return scored


def bootstrap(key, scored, n=2000, seed=7, scored_b=None):
    rng = random.Random(seed); names = [p["pack"] for p in key["packs"] if scored[p["pack"]]]
    point = metrics(scored, key["packs"], names)
    samples = []
    for _ in range(n):
        idx = [rng.choice(names) for _ in names]
        a = metrics(scored, key["packs"], idx)
        if scored_b is not None:
            b = metrics(scored_b, key["packs"], idx)
            samples.append({k: a[k] - b[k] for k in a})
        else:
            samples.append(a)
    ci = {}
    for k in point:
        vals = sorted(s[k] for s in samples if s[k] == s[k])
        ci[k] = (vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1]) if vals else (float("nan"),) * 2
    return point, ci


def fmt(k, v):
    return f"{v:6.2f}" if "per_pack" in k or "false_alarms" in k or "traps" in k else f"{100 * v:5.1f}%"


def report(title, point, ci):
    print(f"\n{title}")
    for k in ["recall_all", "recall_material", "recall_T3T4_material", "recall_T1", "recall_T2", "recall_T3", "recall_T4",
              "false_alarms_per_pack", "decoy_traps_per_pack", "clean_pack_false_alarms"]:
        lo, hi = ci[k]
        print(f"  {k:26s} {fmt(k, point[k])}   95% CI [{fmt(k, lo).strip()}, {fmt(k, hi).strip()}]")


def selftest(key_path):
    key = json.load(open(key_path)); tmp = "/tmp/_bench_selftest"; os.makedirs(tmp, exist_ok=True)
    rng = random.Random(3)
    for kind in ("oracle", "half", "noisy", "lazy"):
        d_ = os.path.join(tmp, kind); os.makedirs(d_, exist_ok=True)
        for pk in key["packs"]:
            fnd = []
            for f in pk["findings"]:
                if kind == "oracle" or (kind == "half" and rng.random() < 0.5) or (kind == "noisy" and rng.random() < 0.8):
                    d, r = f["locs"][0]; fnd.append(dict(doc=d, ref=r, issue=f["keywords"][0]))
            if kind == "noisy":
                for dd in pk["decoys"]:
                    if rng.random() < 0.5: d, r = dd["locs"][0]; fnd.append(dict(doc=d, ref=r, issue="looks wrong"))
                fnd.append(dict(doc="SA", ref="99.9", issue="invented"))
            json.dump({"findings": fnd}, open(os.path.join(d_, f"{pk['pack']}.rep1.json"), "w"))
    ok = True
    for kind in ("oracle", "half", "noisy", "lazy"):
        sc = evaluate(key, os.path.join(tmp, kind), strict=True)
        point, ci = bootstrap(key, sc, n=300)
        report(f"selftest: {kind}", point, ci)
        if kind == "oracle": ok &= point["recall_all"] == 1.0 and point["false_alarms_per_pack"] == 0
        if kind == "lazy": ok &= point["recall_all"] == 0.0
        if kind == "half": ok &= 0.3 < point["recall_all"] < 0.7
        if kind == "noisy": ok &= point["false_alarms_per_pack"] > 0.9 and point["decoy_traps_per_pack"] > 0
    print("\nSELFTEST", "PASSED" if ok else "FAILED"); sys.exit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True); ap.add_argument("--results")
    ap.add_argument("--baseline"); ap.add_argument("--strict", action="store_true")
    ap.add_argument("--selftest", action="store_true"); ap.add_argument("--json")
    a = ap.parse_args()
    if a.selftest: selftest(a.key)
    key = json.load(open(a.key))
    sc = evaluate(key, a.results, a.strict)
    missing = [p for p, r in sc.items() if not r]
    if missing: print(f"warning: no results for {len(missing)} packs: {missing[:5]}...")
    point, ci = bootstrap(key, sc)
    report(f"{a.results} ({'strict' if a.strict else 'location-only'} matching)", point, ci)
    out = {"run": a.results, "point": point, "ci": ci}
    if a.baseline:
        sb = evaluate(key, a.baseline, a.strict)
        dpoint, dci = bootstrap(key, sc, scored_b=sb)
        report(f"DIFFERENCE  {a.results}  minus  {a.baseline}  (paired bootstrap over packs)", dpoint, dci)
        out["diff"] = {"point": dpoint, "ci": dci}
    if a.json: json.dump(out, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
