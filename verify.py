#!/usr/bin/env python3
"""Independent rule-based checker. Reads the generated documents (not the generator state), detects
the planted defect types by rule, and compares them with answer_key.json. Agreement means the key
is complete (no unplanted defects) and correct (every planted defect is really present).

Usage: python verify.py --set test
"""
import argparse, json, os, re, datetime as dt

MONTHS = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                      "September", "October", "November", "December"], 1)}


def pdate(s):
    mo = re.search(r"(\d{1,2}) (\w+) (\d{4})", s)
    return dt.date(int(mo.group(3)), MONTHS[mo.group(2)], int(mo.group(1)))


def money(s):
    return float(s.replace("£", "").replace(",", "").rstrip("."))


def rows(text, prefix):
    out = {}
    for line in text.split("\n"):
        mo = re.match(rf"^{re.escape(prefix)}(\w+)\s*\|(.*)$", line)
        if mo:
            out[mo.group(1)] = [c.strip() for c in mo.group(2).split("|")]
    return out


def check(sa, po, vo, ce, ts=None, mtc=None):
    found = set()
    # clause map
    clause_nums = set(re.findall(r"^(\d+)\. [A-Z]", sa, re.M))
    title_to_num = {t: n for n, t in re.findall(r"^(\d+)\. ([A-Z \-]+)$", sa, re.M)}
    s1 = rows(sa, "S1."); s2 = rows(sa, "S2.")
    tot = 0.0
    for k, c in s1.items():
        if k == "T": continue
        qty, unit, val = int(c[2]), money(c[3]), money(c[4])
        tot += round(qty * unit, 2)
        if abs(round(qty * unit, 2) - val) > 0.005: found.add("M01")
    tm = re.search(r"^S1\.T .*?\| (£[\d,\.]+)", sa, re.M)
    shown = money(tm.group(1)); rounded = "rounded to the nearest pound" in sa
    if abs(shown - tot) > (1.0 if rounded else 0.005): found.add("M02")
    if "______" in re.search(r"^SIG\.S.*$", sa, re.M).group(0): found.add("M03")
    eff = pdate(re.search(r"takes effect on (.*?) \(", sa).group(1))
    ls = pdate(re.search(r"no later than (.*?) \(the", sa).group(1))
    if ls < eff: found.add("M04")
    for n in re.findall(r"under clause (\d+)", sa):
        if n not in clause_nums: found.add("M05")
    pay1 = int(re.search(r"within (\d+) days of receipt", sa).group(1))
    pay3 = int(re.search(r"S3\.1  Payment: (\d+) days", sa).group(1))
    if pay1 != pay3: found.add("M06")
    wd = int(re.search(r"means (\d+) months", sa).group(1)); wc = int(re.search(r"defects for (\d+) months", sa).group(1))
    if wd != wc: found.add("M07")
    lc = float(re.search(r"shall not exceed ([\d\.]+)%", sa).group(1)); ls3 = float(re.search(r"S3\.3  LD cap: ([\d\.]+)%", sa).group(1))
    if lc != ls3: found.add("M08")
    l1 = money(re.search(r"limited to (£[\d,\.]+)", sa).group(1)); l3 = money(re.search(r"S3\.4  Liability cap: (£[\d,\.]+)", sa).group(1))
    if l1 != l3: found.add("M09")
    law1 = re.search(r"governed by the laws of (.*?)\.", sa).group(1); law3 = re.search(r"S3\.5  Governing law: (.*)", sa).group(1).strip()
    if law1 != law3: found.add("M10")
    # PO
    pr = rows(po, "L.")
    for k, c in pr.items():
        if k == "T": continue
        i = k
        qty, unit = int(c[4]), money(c[5])
        if abs(unit - money(s1[i][3])) > 0.005: found.add("M11")
        if qty > int(s1[i][2]): found.add("M12")
        if c[2] != s2[i][1]: found.add("M13")
        if c[3] != s2[i][2]: found.add("M14")
    if re.search(r"Supply Agreement No\. (\S+) dated", po).group(1) != re.search(r"SUPPLY AGREEMENT No\. (\S+) dated", sa).group(1): found.add("M15")
    if re.search(r"PT\.1  Governing law: (.*)", po).group(1).strip() != law1: found.add("M16")
    if int(re.search(r"PT\.2  Payment: (\d+) days", po).group(1)) != pay1: found.add("M17")
    po_no = re.search(r"PURCHASE ORDER No\. (\S+) dated", po).group(1)
    if re.search(r"Purchase Order No\. (\S+)", ce).group(1) != po_no: found.add("M18")
    # VO -> final qty
    vm = re.search(r"\(PO line (\d+)\): quantity changed from (\d+) to (\d+) at unit price (£[\d,\.]+)", vo)
    vk, vold, vnew, vunit = vm.group(1), int(vm.group(2)), int(vm.group(3)), money(vm.group(4))
    final = {k: (vnew if k == vk else int(c[4])) for k, c in pr.items() if k != "T"}
    cr = rows(ce, "C.")
    for k, c in cr.items():
        if k in ("H", "SIG"): continue
        if c[1] != s2[k][2]: found.add("M19")
        if int(c[3]) != final[k] and "Partial release" not in c[5]: found.add("M20")
        if int(c[4]) < int(s2[k][3]): found.add("M22")
    td = pdate(re.search(r"CT\.1  Date of test: (.*)", ce).group(1)); cal = pdate(re.search(r"CT\.2 .*valid until: (.*)", ce).group(1))
    if td > cal: found.add("M21")
    if abs(vunit - money(s1[vk][3])) > 0.005: found.add("M23")
    ov = round(vold * vunit, 2); nv = round(vnew * vunit, 2); diff = round(nv - ov, 2)
    m3 = re.search(r"before this Variation (£[\d,\.]+); revised PO total (£[\d,\.]+)", vo)
    if abs(money(m3.group(1)) + diff - money(m3.group(2))) > 0.005: found.add("M24")
    if abs(money(m3.group(1)) - sum(round(int(c[4]) * money(c[5]), 2) for k, c in pr.items() if k != "T")) > 0.005: found.add("BASE-PO-TOTAL")
    vc = re.search(r"under clause (\d+) of the Agreement", vo).group(1)
    if vc != title_to_num["VARIATIONS"]: found.add("M25")
    if not re.search(r"S4\.2 .*\| H \(Hold\)", sa): found.add("M26")
    if "A.AR" in sa: found.add("M27")
    lead = int(re.search(r"not less than (\d+) weeks", sa).group(1))
    pd_ = re.search(r"dated (.*)$", po.split("\n")[0]).group(1)
    pod = dt.datetime.strptime(pd_, "%d/%m/%Y").date() if "/" in pd_ else pdate(pd_)
    dl = pdate(re.search(r"PT\.3  Delivery Date: (.*)", po).group(1))
    if (dl - pod).days < lead * 7: found.add("M28")
    if "Total Price" in sa: found.add("M30")
    if re.search(r"Rev (\w)\b", po.split("PT.4")[1]).group(1) != re.search(r"S2\.H .*Rev (\w)\)", sa).group(1): found.add("M32")
    n1 = int(re.search(r"on (\d+) working days' notice", sa).group(1)); n4 = int(re.search(r"notice of inspection: (\d+) working days", sa).group(1))
    if n1 != n4: found.add("M34")
    # ---- base consistency: must never fire, otherwise an unplanted defect leaked into the documents ----
    s36 = pdate(re.search(r"S3\.6  Long-Stop Delivery Date: (.*)", sa).group(1))
    if s36 != ls: found.add("BASE-LONGSTOP")
    if int(re.search(r"S3\.2  Warranty: (\d+) months", sa).group(1)) != wd: found.add("BASE-WARRANTY")
    if vold != int(pr[vk][4]): found.add("BASE-VO-OLD")
    if not (pod <= td <= dl): found.add("BASE-TEST-DATE")
    if vnew > int(s1[vk][2]): found.add("BASE-VO-MAX")
    if not (re.search(r"^VO\.S1 .*Signed for the Purchaser: \w", vo, re.M) and re.search(r"^VO\.S2 .*Signed for the Supplier: \w", vo, re.M)): found.add("BASE-VO-SIG")
    if "minimum shell test pressure" not in sa.lower(): found.add("BASE-MINIMUM-WORDING")
    if long_mode(ts, mtc):
        found |= check_long(sa, ce, ts, mtc, s1, s2, s36)
    return found


def long_mode(ts, mtc):
    return ts is not None and mtc is not None


def check_long(sa, ce, ts, mtc, s1, s2, s36):
    found = set()
    ts_rev = re.search(r"TECHNICAL SPECIFICATION \S+ Rev (\w)", ts).group(1)
    if ts_rev != re.search(r"S2\.H .*Rev (\w)\)", sa).group(1): found.add("M40")
    bar = {c[0]: int(re.match(r"(\d+)", c[1]).group(1)) for c in rows(ts, "TS.P").values()}
    for k, c in s2.items():
        if k == "H": continue
        if bar[c[1]] != int(c[3]): found.add("M43")
    if "hold point" not in re.search(r"^TS\.HP .*$", ts, re.M).group(0).split("and the final")[0]: found.add("M44")
    minp = {c[0]: tuple(int(x) for x in c[1:4]) for c in rows(ts, "TS.Y").values() if c[0].startswith("ASTM")}
    certrows = rows(ce, "C.")
    cur = {}
    for line in mtc.split("\n"):
        mo = re.match(r"^M\.(\d+)\.(\d) \| (.*)$", line)
        if mo: cur.setdefault(mo.group(1), {})[mo.group(2)] = [x.strip() for x in mo.group(3).split("|")]
    for k, b in cur.items():
        heat = b["1"][1].replace("Heat ", ""); mat = b["1"][2]
        if heat != certrows[k][2]: found.add("M41")
        if mat != s2[k][2]: found.add("BASE-MTC-MAT")
        y = int(re.search(r"Yield (\d+)", b["3"][1]).group(1)); t = int(re.search(r"Tensile (\d+)", b["3"][2]).group(1))
        e = int(re.search(r"Elongation (\d+)", b["3"][3]).group(1))
        if y < minp[mat][0]: found.add("M42")
        if t < minp[mat][1] or e < minp[mat][2]: found.add("BASE-MTC-TENSILE")
        pv = float(re.search(r"P ([\d\.]+)", b["2"][4]).group(1)); sv = float(re.search(r"S ([\d\.]+)", b["2"][5]).group(1))
        if pv > 0.035 or sv > 0.040: found.add("BASE-MTC-CHEM")
        imp = [int(re.match(r"(\d+)", x).group(1)) for x in b["4"][1:4]]
        avg = float(re.search(r"avg ([\d\.]+)", b["4"][4]).group(1))
        if abs(round(sum(imp) / 3, 1) - avg) > 0.05 or min(imp) < 27 or avg < 27: found.add("BASE-MTC-IMPACT")
    s6 = rows(sa, "S6."); t6 = 0.0
    for k, c in s6.items():
        if k == "T": continue
        true = round(int(c[2]) * money(c[3]), 2); t6 += true
        if abs(true - money(c[4])) > 0.005: found.add("M46")
    if abs(money(s6["T"][-1]) - round(t6, 2)) > 0.005: found.add("BASE-S6-TOTAL")
    dates = [pdate(c[1]) for k, c in rows(sa, "S7.").items()]
    if dates[-1] > s36: found.add("M47")
    if any(b_ < a_ for a_, b_ in zip(dates[:-2], dates[1:-1])): found.add("BASE-S7-ORDER")
    return found


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--set", required=True); a = ap.parse_args()
    key = json.load(open(os.path.join(a.set, "key", "answer_key.json")))
    bad = 0; checked = 0
    for p in key["packs"]:
        d_ = os.path.join(a.set, "packs", p["pack"])
        docs = [open(os.path.join(d_, f"{n}.md")).read() for n in ("SA", "PO", "VO", "CERT")]
        if os.path.exists(os.path.join(d_, "TS.md")):
            docs += [open(os.path.join(d_, "TS.md")).read(), open(os.path.join(d_, "MTC.md")).read()]
        found = check(*docs)
        planted = {f["type"] for f in p["findings"]}
        checked += 1
        if found != planted:
            bad += 1
            print(f"{p['pack']}: planted {sorted(planted)}  checker found {sorted(found)}")
    print(f"{a.set}: {checked} packs checked, {bad} mismatches")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
