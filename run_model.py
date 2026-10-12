#!/usr/bin/env python3
"""Run a model over the packs through any OpenAI-compatible endpoint (vLLM, llama.cpp server, Ollama, LM Studio...).
Standard library only. Writes results/<run>/<pack>.rep<k>.json, which score.py reads.

  python run_model.py --set test --base-url http://localhost:8000/v1 --model gpt-oss-120b --run gptoss120b --reps 3
  python run_model.py --set test --base-url http://localhost:8000/v1 --model my-model --run x --packs P01,P02 --concurrency 4

Send back only the results/<run>/ folder; the documents are fictional, and nothing here needs the answer key.
"""
import argparse, json, os, re, sys, time, urllib.request, concurrent.futures as cf

SYSTEM = """You are a careful contract reviewer. You are given a pack of related documents: a Supply Agreement (SA), a Purchase Order (PO), a Variation Order (VO) and an Inspection Release Certificate (CERT). Longer packs also include a Technical Specification (TS) and Material Test Certificates (MTC).
Find genuine defects: arithmetic errors, internal contradictions, inconsistencies between documents, cross-references that do not exist, missing or invalid execution, and similar errors.
Only report real defects. Do not report items that are consistent, unusual-but-consistent, or merely worth noting. A pack may contain no defects at all.
Every line, clause, table row and header carries a reference label printed in the text (for example 6.1, S1.3, L.2, PT.2, C.4, VO.3, SA.H, TS.P2, M.3.3). Cite references exactly as printed.
Return ONLY JSON in this form:
{"findings":[{"doc":"SA|PO|VO|CERT|TS|MTC","ref":"<label>","issue":"<one sentence>"}]}
If the same defect appears in two places, report it once, citing the most relevant label (you may list two labels separated by a comma)."""


def read_pack(base, pid):
    parts = []
    for n in ("SA", "PO", "VO", "CERT", "TS", "MTC"):
        if not os.path.exists(os.path.join(base, "packs", pid, f"{n}.md")): continue
        parts.append(f"=== DOCUMENT {n} ===\n" + open(os.path.join(base, "packs", pid, f"{n}.md")).read())
    return "\n\n".join(parts)


def call(url, model, api_key, user, max_tokens, timeout, temperature):
    body = json.dumps({"model": model, "temperature": temperature, "max_tokens": max_tokens,
                       "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]}).encode()
    req = urllib.request.Request(url.rstrip("/") + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"})
    t = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read())
    return data["choices"][0]["message"]["content"], data.get("usage", {}), time.time() - t


def parse(text):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    mo = re.search(r"\{.*\}", text, re.S)
    if not mo: return None
    try:
        obj = json.loads(mo.group(0))
        return obj.get("findings", []) if isinstance(obj, dict) else None
    except Exception:
        return None


def job(args, pid, rep, outdir):
    fn = os.path.join(outdir, f"{pid}.rep{rep}.json")
    if os.path.exists(fn) and not args.force: return pid, rep, "skip"
    user = read_pack(args.set, pid)
    for attempt in range(3):
        try:
            txt, usage, secs = call(args.base_url, args.model, args.api_key, user, args.max_tokens, args.timeout, args.temperature)
            f = parse(txt)
            json.dump({"pack": pid, "rep": rep, "findings": f if f is not None else [], "parse_error": f is None,
                       "usage": usage, "seconds": secs, "raw": txt if f is None else ""}, open(fn, "w"))
            return pid, rep, f"ok {secs:.0f}s" + ("" if f is not None else " PARSE-ERROR")
        except Exception as e:
            err = str(e)
            time.sleep(3)
    json.dump({"pack": pid, "rep": rep, "findings": [], "error": err}, open(fn, "w"))
    return pid, rep, f"ERROR {err[:60]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True, help="folder containing packs/ (e.g. test or dev)")
    ap.add_argument("--base-url", default="http://localhost:8000/v1"); ap.add_argument("--model", required=True)
    ap.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", "none"))
    ap.add_argument("--run", required=True); ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--packs", default=""); ap.add_argument("--concurrency", type=int, default=2)
    ap.add_argument("--max-tokens", type=int, default=6000); ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--temperature", type=float, default=0.0); ap.add_argument("--force", action="store_true")
    ap.add_argument("--results-dir", default="results")
    args = ap.parse_args()
    outdir = os.path.join(args.results_dir, args.run); os.makedirs(outdir, exist_ok=True)
    packs = sorted(os.listdir(os.path.join(args.set, "packs")))
    if args.packs: packs = [p for p in packs if p in args.packs.split(",")]
    jobs = [(p, r) for p in packs for r in range(1, args.reps + 1)]
    print(f"{len(jobs)} jobs -> {outdir}")
    with cf.ThreadPoolExecutor(args.concurrency) as ex:
        futs = [ex.submit(job, args, p, r, outdir) for p, r in jobs]
        for i, f in enumerate(cf.as_completed(futs), 1):
            pid, rep, st = f.result(); print(f"[{i}/{len(jobs)}] {pid} rep{rep}: {st}", flush=True)


if __name__ == "__main__":
    main()
