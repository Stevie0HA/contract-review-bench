#!/usr/bin/env python3
"""Synthetic contract-pack generator with planted findings, decoys and clean packs.

Everything is fictional. No real company, person or document is used.

Usage:
  python generate.py --out test --seed 2026 --packs 36 --clean 6
  python generate.py --out dev  --seed 1    --packs 10 --clean 2
"""
import argparse, json, os, random, re, datetime as dt

BUYERS = ["Northgate Energy Projects Ltd", "Kestrel Offshore Services Ltd", "Tarn Process Engineering Ltd",
          "Brindle Marine & Energy Ltd", "Calder Midstream Ltd", "Wexcombe Gas Systems Ltd"]
SUPPLIERS = ["Halden Valve Works Ltd", "Orrin Fabrication Ltd", "Vessel & Flange Co Ltd",
             "Tavis Instrumentation Ltd", "Marrow Forge Ltd", "Pellam Pumps Ltd", "Dunmere Castings Ltd"]
ITEM_TYPES = [("GV", "Gate valve", 1850.0), ("BV", "Ball valve, trunnion mounted", 2400.0),
              ("CV", "Check valve, swing type", 1500.0), ("FL", "Weld neck flange", 420.0),
              ("PT", "Pressure transmitter", 1150.0), ("SK", "Basket strainer", 2100.0),
              ("HX", "Plate heat exchanger", 18500.0), ("PU", "Centrifugal pump set", 26500.0)]
CLASSES = ["Class 150", "Class 300", "Class 600", "Class 900", "Class 1500"]
BAR = {"Class 150": 29, "Class 300": 77, "Class 600": 153, "Class 900": 230, "Class 1500": 383}
MATERIALS = ["ASTM A105", "ASTM A350 LF2", "ASTM A182 F316L", "ASTM A216 WCB", "ASTM A351 CF8M"]
LAWS = ["England and Wales", "Scotland", "Singapore"]

FILL = {
 "confidentiality": ("Confidentiality", [
   "Each party shall keep the other party's Confidential Information secret and shall not disclose it to any third party without prior written consent.",
   "These obligations continue for {y} years after the end of this Agreement.",
   "Disclosure required by law or by a regulator is permitted if the disclosing party gives prior notice where lawful."]),
 "ip": ("Intellectual Property", [
   "Each party retains ownership of the intellectual property it brings to this Agreement.",
   "Supplier grants the Purchaser a perpetual, non-exclusive licence to use the manuals and drawings supplied with the Goods.",
   "Supplier shall indemnify the Purchaser against claims that the Goods infringe third-party rights, subject to prompt notice of the claim."]),
 "force_majeure": ("Force Majeure", [
   "Neither party is liable for delay caused by events beyond its reasonable control, provided it notifies the other party within {dd} days.",
   "If the event continues for more than {dd2} days, either party may terminate the affected Purchase Order by written notice.",
   "Shortage of labour or materials caused by the affected party's own supply chain choices is not force majeure."]),
 "insurance": ("Insurance", [
   "Supplier shall maintain public liability insurance of not less than {ins} for each claim throughout the Term.",
   "Supplier shall maintain product liability insurance of not less than {ins} for the duration of the Warranty Period.",
   "Supplier shall provide certificates of insurance on written request."]),
 "termination": ("Termination", [
   "Either party may terminate this Agreement by written notice if the other commits a material breach that is not remedied within {dd} days of notice.",
   "The Purchaser may terminate for convenience on {dd2} days' written notice, paying for Goods delivered and work in progress.",
   "Termination does not affect rights accrued before the date of termination."]),
 "notices": ("Notices", [
   "Notices shall be in writing and sent to the address of the receiving party stated in this Agreement.",
   "A notice delivered by hand is received on delivery and a notice sent by recorded post is received on the second working day after posting.",
   "Either party may change its address by notice to the other."]),
 "assignment": ("Assignment", [
   "Neither party may assign or transfer its rights under this Agreement without the prior written consent of the other.",
   "Consent shall not be unreasonably withheld for an assignment to a group company.",
   "The assignor remains responsible for the acts of its assignee."]),
 "anti_bribery": ("Anti-Bribery", [
   "Each party shall comply with all applicable anti-bribery and anti-corruption laws.",
   "Supplier shall maintain adequate procedures to prevent bribery by persons associated with it.",
   "Breach of this clause entitles the Purchaser to terminate immediately by written notice."]),
 "data_protection": ("Data Protection", [
   "Each party shall comply with applicable data protection law in relation to personal data processed under this Agreement.",
   "Supplier shall process personal data only on the Purchaser's documented instructions.",
   "Supplier shall notify the Purchaser without undue delay of any personal data breach."]),
 "audit": ("Audit", [
   "The Purchaser may audit Supplier's quality records relating to the Goods on {dd} days' notice during normal working hours.",
   "Supplier shall retain manufacturing and inspection records for {y} years after delivery.",
   "Each party bears its own costs of an audit unless it reveals a material non-conformance."]),
 "subcontracting": ("Subcontracting", [
   "Supplier shall not subcontract any critical manufacturing step without the Purchaser's written approval.",
   "Supplier remains responsible for the acts and omissions of its subcontractors.",
   "Supplier shall flow down the inspection and records requirements of this Agreement to approved subcontractors."]),
 "dispute": ("Dispute Resolution", [
   "The parties shall first try to resolve any dispute by escalation to senior management for {dd} days.",
   "If the dispute is not resolved, either party may refer it to mediation before starting proceedings.",
   "Nothing in this clause prevents a party from seeking urgent injunctive relief."]),
 "entire": ("Entire Agreement", [
   "This Agreement and its Schedules are the entire agreement between the parties on their subject matter.",
   "Each party acknowledges it has not relied on any statement not set out in this Agreement.",
   "Nothing in this clause limits liability for fraud."]),
 "waiver": ("Waiver", [
   "A failure or delay in exercising a right is not a waiver of that right.",
   "A waiver is effective only if given in writing and signed by the waiving party.",
   "A waiver of one breach is not a waiver of any later breach."]),
 "severability": ("Severability", [
   "If any provision is found invalid or unenforceable, the rest of this Agreement continues in effect.",
   "The parties shall negotiate in good faith a valid replacement that achieves the original intent.",
   "This clause does not apply where removing the provision defeats the main purpose of this Agreement."]),
 "quality": ("Quality System", [
   "Supplier shall maintain a quality management system certified to ISO 9001 or equivalent throughout the Term.",
   "Supplier shall notify the Purchaser within {dd} days if its certification is suspended or withdrawn.",
   "Supplier shall implement the corrective actions the Purchaser reasonably requires after an audit."]),
 "packing": ("Packing and Shipping", [
   "Supplier shall pack the Goods to protect them against damage and corrosion during transport and storage.",
   "Each package shall be marked with the Purchase Order number, item code and gross weight.",
   "Risk passes to the Purchaser on delivery; title passes on payment."]),
 "documentation": ("Documentation", [
   "Supplier shall supply a data book with each delivery containing material certificates, test reports and inspection release certificates.",
   "Documents shall be in English and in the format agreed with the Purchaser.",
   "Delivery is not complete until the data book has been accepted by the Purchaser."]),
}
ANNEX_FILL = [
  "Supplier shall comply with the Purchaser's site safety rules when attending any Purchaser location.",
  "The Purchaser may suspend work on written notice for up to {dd} days without liability for the suspension.",
  "Supplier shall return all Purchaser property on completion of the Goods or on earlier request.",
  "Headings are for convenience only and do not affect interpretation.",
  "References to a statute include that statute as amended or re-enacted from time to time.",
]


def d(x):
    return f"{x.day} {x.strftime('%B %Y')}"


def m(x):
    return f"£{x:,.2f}"


class Pack:
    pass


# --------------------------------------------------------------------------------------
# mutations: each returns a finding dict or None if it cannot be applied
# --------------------------------------------------------------------------------------
def pick(X, group, exclude=()):
    n = len(X["items"])
    cand = [i for i in range(n) if i not in X["used"][group] and i not in exclude]
    if not cand:
        return None
    i = X["rng"].choice(cand)
    X["used"][group].add(i)
    return i


def other(rng, seq, cur):
    return rng.choice([s for s in seq if s != cur])


def F(tier, material, mtype, locs, desc):
    return dict(tier=tier, material=material, type=mtype, locs=locs, desc=desc)


def m01(X):
    k = pick(X, "sa_line")
    if k is None: return None
    it = X["items"][k]
    true = round(it["qty_max"] * it["unit"], 2)
    wrong = round(true * X["rng"].choice([0.9, 1.1, 1.2, 0.8]), 2)
    X["sa_line_override"][k] = wrong
    return F(1, True, "M01", [("SA", f"S1.{k+1}")],
             f"Schedule 1 line {k+1}: line value shown as {m(wrong)} but {it['qty_max']} x {m(it['unit'])} = {m(true)}.")

def m02(X):
    true = sum(round(i["qty_max"] * i["unit"], 2) for i in X["items"])
    wrong = round(true + X["rng"].choice([-4200, 1800, 12000, -950]), 2)
    X["sa_total_override"] = wrong
    return F(1, True, "M02", [("SA", "S1.T")], f"Schedule 1 total shown as {m(wrong)} but the lines sum to {m(true)}.")

def m03(X):
    X["P"]["sig_supplier_blank"] = True
    return F(1, True, "M03", [("SA", "SIG.S")], "Supplier signature block on the Supply Agreement is blank; agreement is unsigned by the Supplier.")

def m04(X):
    P = X["P"]
    bad = P["eff"] - dt.timedelta(days=X["rng"].randint(20, 120))
    P["longstop_clause"] = bad; P["longstop_sched"] = bad
    return F(2, True, "M04", [("SA", "@longstop"), ("SA", "@eff")],
             f"Long-Stop Delivery Date ({d(bad)}) in clause 5.1 is before the Effective Date ({d(P['eff'])}).")

def m05(X):
    X["P"]["xref_bad"] = X["rng"].choice([17, 18, 19, 21]) + 0.0
    return F(2, False, "M05", [("SA", "@price_term")], "Clause 4.2 refers to a clause number that does not exist in the Agreement.")

def m06(X):
    P = X["P"]; P["pay_sched"] = other(X["rng"], [30, 45, 60, 90], P["pay_main"])
    return F(2, True, "M06", [("SA", "@pay_days"), ("SA", "S3.1")],
             f"Payment terms conflict: clause 6.1 says {P['pay_main']} days, Schedule 3 says {P['pay_sched']} days.")

def m07(X):
    P = X["P"]; P["war_clause"] = other(X["rng"], [12, 18, 24, 36], P["war_def"])
    return F(2, True, "M07", [("SA", "@war_def"), ("SA", "@war_clause")],
             f"Warranty conflict: definition says {P['war_def']} months, clause 8.1 says {P['war_clause']} months.")

def m08(X):
    P = X["P"]; P["ld_cap_sched"] = other(X["rng"], [5, 7.5, 10, 15], P["ld_cap_clause"])
    return F(2, True, "M08", [("SA", "@ld_cap"), ("SA", "S3.3")],
             f"LD cap conflict: clause 9.2 says {P['ld_cap_clause']}%, Schedule 3 says {P['ld_cap_sched']}%.")

def m09(X):
    P = X["P"]; P["liab_sched"] = other(X["rng"], [500000, 1000000, 2500000, 5000000], P["liab_clause"])
    return F(2, True, "M09", [("SA", "@liab"), ("SA", "S3.4")],
             f"Liability cap conflict: clause 10.1 says {m(P['liab_clause'])}, Schedule 3 says {m(P['liab_sched'])}.")

def m10(X):
    P = X["P"]; P["law_sched"] = other(X["rng"], LAWS, P["law_sa"])
    return F(2, True, "M10", [("SA", "@law"), ("SA", "S3.5")],
             f"Governing law conflict: clause says {P['law_sa']}, Schedule 3 says {P['law_sched']}.")

def m11(X):
    k = pick(X, "po", exclude=[X["vo_k"]])
    if k is None: return None
    it = X["items"][k]; row = X["po"][k]
    row["unit"] = round(it["unit"] * X["rng"].choice([1.08, 1.15, 0.92, 1.25]), 2)
    return F(3, True, "M11", [("PO", f"L.{k+1}"), ("SA", f"S1.{k+1}")],
             f"PO line {k+1} unit price {m(row['unit'])} differs from Agreement price {m(it['unit'])}.")

def m12(X):
    k = pick(X, "po", exclude=[X["vo_k"]])
    if k is None: return None
    it = X["items"][k]; q = it["qty_max"] + X["rng"].randint(5, 25)
    X["po"][k]["qty"] = q; X["cert"][k]["qty"] = q
    return F(3, True, "M12", [("PO", f"L.{k+1}"), ("SA", f"S1.{k+1}")],
             f"PO line {k+1} quantity {q} exceeds the Maximum Quantity {it['qty_max']} in Schedule 1.")

def m13(X):
    k = pick(X, "po", exclude=[X["vo_k"]])
    if k is None: return None
    it = X["items"][k]; X["po"][k]["cls"] = other(X["rng"], CLASSES, it["cls"])
    return F(3, True, "M13", [("PO", f"L.{k+1}"), ("SA", f"S2.{k+1}")],
             f"PO line {k+1} states {X['po'][k]['cls']} but Schedule 2 requires {it['cls']}.")

def m14(X):
    k = pick(X, "po", exclude=[X["vo_k"]])
    if k is None: return None
    X["used"]["cert"].add(k)
    it = X["items"][k]; X["po"][k]["mat"] = other(X["rng"], MATERIALS, it["mat"])
    return F(3, True, "M14", [("PO", f"L.{k+1}"), ("SA", f"S2.{k+1}")],
             f"PO line {k+1} states material {X['po'][k]['mat']} but Schedule 2 requires {it['mat']}.")

def m15(X):
    P = X["P"]; digits = list(P["sa_no"]); i = len(digits) - 1
    digits[i] = str((int(digits[i]) + X["rng"].randint(1, 8)) % 10)
    P["sa_no_in_po"] = "".join(digits)
    return F(3, False, "M15", [("PO", "PO.H"), ("SA", "SA.H")],
             f"PO cites Agreement No. {P['sa_no_in_po']} but the Agreement number is {P['sa_no']}.")

def m16(X):
    P = X["P"]; P["law_po"] = other(X["rng"], LAWS, P["law_sa"])
    return F(3, True, "M16", [("PO", "PT.1"), ("SA", "@law")],
             f"PO terms say {P['law_po']} law; the Agreement says {P['law_sa']}.")

def m17(X):
    P = X["P"]; P["pay_po"] = other(X["rng"], [30, 45, 60, 90], P["pay_main"])
    return F(3, True, "M17", [("PO", "PT.2"), ("SA", "@pay_days")],
             f"PO payment terms {P['pay_po']} days differ from the Agreement's {P['pay_main']} days.")

def m18(X):
    P = X["P"]; digits = list(P["po_no"]); digits[-1] = str((int(digits[-1]) + X["rng"].randint(1, 8)) % 10)
    P["po_no_in_cert"] = "".join(digits)
    return F(3, True, "M18", [("CERT", "C.H"), ("PO", "PO.H")],
             f"Certificate cites PO {P['po_no_in_cert']} but the PO number is {P['po_no']}.")

def m19(X):
    k = pick(X, "cert")
    if k is None: return None
    it = X["items"][k]; X["cert"][k]["mat"] = other(X["rng"], MATERIALS, it["mat"])
    return F(3, True, "M19", [("CERT", f"C.{k+1}"), ("SA", f"S2.{k+1}")],
             f"Certificate line {k+1} reports material {X['cert'][k]['mat']} but Schedule 2 requires {it['mat']}.")

def m20(X):
    k = pick(X, "cert")
    if k is None: return None
    q = X["cert"][k]["qty"]; X["cert"][k]["qty"] = max(1, q - X["rng"].randint(3, 9))
    return F(3, True, "M20", [("CERT", f"C.{k+1}"), ("PO", f"L.{k+1}")],
             f"Certificate line {k+1} releases {X['cert'][k]['qty']} but {q} were ordered; no partial-release note.")

def m21(X):
    P = X["P"]; P["cal_expiry"] = P["test_date"] - dt.timedelta(days=X["rng"].randint(5, 90))
    return F(2, True, "M21", [("CERT", "CT.1"), ("CERT", "CT.2")],
             f"Test date {d(P['test_date'])} is after gauge calibration expiry {d(P['cal_expiry'])}.")

def m22(X):
    k = pick(X, "cert")
    if k is None: return None
    it = X["items"][k]; X["cert"][k]["bar"] = int(it["bar"] * X["rng"].choice([0.7, 0.8, 0.9]))
    return F(3, True, "M22", [("CERT", f"C.{k+1}"), ("SA", f"S2.{k+1}")],
             f"Certificate line {k+1} test pressure {X['cert'][k]['bar']} bar is below the required {it['bar']} bar.")

def m23(X):
    k = X["vo_k"]; it = X["items"][k]
    X["vo"]["unit_disp"] = round(it["unit"] * X["rng"].choice([1.1, 0.9, 1.2]), 2)
    return F(3, True, "M23", [("VO", "VO.1"), ("VO", "VO.2"), ("SA", f"S1.{k+1}")],
             f"VO shows unit price {m(X['vo']['unit_disp'])} but the Agreement price is {m(it['unit'])}.")

def m24(X):
    X["vo"]["total_wrong"] = X["rng"].choice([-5000, 3500, 9000, -1200])
    return F(1, True, "M24", [("VO", "VO.3")], "VO revised PO total does not equal the PO total plus the stated increase.")

def m25(X):
    X["vo"]["xref_wrong"] = True
    return F(3, False, "M25", [("VO", "VO.4"), ("SA", "@variations")],
             "VO cites the Payment clause as its authority; Variations are governed by a different clause.")

def m26(X):
    X["P"]["itp_hold"] = "R (Review)"
    return F(4, True, "M26", [("SA", "S4.2"), ("SA", "@holdpts")],
             "Schedule 4 downgrades the shell hydrostatic test to Review, but clause 7.2 makes it a hold point.")

def m27(X):
    X["P"]["autorenew"] = X["rng"].choice([90, 120, 180])
    return F(4, True, "M27", [("SA", "@term"), ("SA", "A.AR")],
             "Annex A contains an automatic-renewal clause that contradicts clause 3.2 (no automatic renewal).")

def m28(X):
    P = X["P"]; short = X["rng"].randint(2, 5)
    P["po_delivery"] = P["po_date"] + dt.timedelta(weeks=P["lead"] - short)
    P["test_date"] = min(P["test_date"], P["po_delivery"] - dt.timedelta(days=X["rng"].randint(10, 20)))
    return F(4, True, "M28", [("PO", "PT.3"), ("SA", "@lead")],
             f"PO delivery date allows {P['lead'] - short} weeks; clause 5.2 requires at least {P['lead']}.")

def m30(X):
    X["P"]["total_price_term"] = True
    return F(2, False, "M30", [("SA", "@price_term"), ("SA", "@def_cp")],
             "Clause 4.2 uses the undefined term 'Total Price'; the defined term is 'Contract Price'.")

def m32(X):
    P = X["P"]; P["spec_rev_po"] = other(X["rng"], list("ABCDEF"), P["spec_rev"])
    return F(3, True, "M32", [("PO", "PT.4"), ("SA", "S2.H")],
             f"PO cites specification Rev {P['spec_rev_po']}; Schedule 2 is Rev {P['spec_rev']}.")

def m34(X):
    P = X["P"]; P["notice_itp"] = other(X["rng"], [3, 5, 7, 10], P["notice_clause"])
    return F(2, False, "M34", [("SA", "@notice"), ("SA", "S4.H")],
             f"Inspection notice conflict: clause 7.1 says {P['notice_clause']} working days, Schedule 4 says {P['notice_itp']}.")

MUT = {"M01": m01, "M02": m02, "M03": m03, "M04": m04, "M05": m05, "M06": m06, "M07": m07, "M08": m08,
       "M09": m09, "M10": m10, "M11": m11, "M12": m12, "M13": m13, "M14": m14, "M15": m15, "M16": m16,
       "M17": m17, "M18": m18, "M19": m19, "M20": m20, "M21": m21, "M22": m22, "M23": m23, "M24": m24,
       "M25": m25, "M26": m26, "M27": m27, "M28": m28, "M30": m30, "M32": m32, "M34": m34}
TIERS = {1: ["M01", "M02", "M03", "M24"],
         2: ["M04", "M05", "M06", "M07", "M08", "M09", "M10", "M21", "M30", "M34"],
         3: ["M11", "M12", "M13", "M14", "M15", "M16", "M17", "M18", "M19", "M20", "M22", "M23", "M25", "M32"],
         4: ["M26", "M27", "M28"]}
KEYWORDS = {
 "M01": ["total", "calculat", "arithmetic", "multipl", "value", "sum"], "M02": ["total", "sum", "add", "arithmetic"],
 "M03": ["sign", "unsigned", "execut", "blank"], "M04": ["long-stop", "long stop", "delivery", "effective", "before"],
 "M05": ["clause", "cross", "reference", "exist"], "M06": ["payment", "days"], "M07": ["warrant", "month"],
 "M08": ["liquidated", "damages", "cap", "maximum", "ld"], "M09": ["liabil", "cap"],
 "M10": ["governing", "law", "jurisdiction"], "M11": ["price", "rate", "unit"],
 "M12": ["quantity", "qty", "maximum", "exceed"], "M13": ["class", "rating", "pressure"],
 "M14": ["material", "grade", "astm"], "M15": ["agreement", "reference", "number", "ref"],
 "M16": ["governing", "law", "jurisdiction"], "M17": ["payment", "days"],
 "M18": ["po", "purchase order", "reference", "number"], "M19": ["material", "grade", "astm"],
 "M20": ["quantity", "qty", "short", "balance", "partial"], "M21": ["calibrat", "expir"],
 "M22": ["pressure", "bar", "test"], "M23": ["original", "price", "unit", "rate"],
 "M24": ["total", "sum", "arithmetic", "calculat"], "M25": ["clause", "reference", "variation", "authority"],
 "M26": ["hold", "witness", "review", "hydro"], "M27": ["renew", "auto", "term"],
 "M28": ["lead", "delivery", "weeks", "minimum"], "M30": ["defin", "term", "contract price", "total price"],
 "M32": ["rev", "revision", "specification"], "M34": ["notice", "working days"]}

# ----------------------------------------------------------------------------------
# long-mode material: technical specification, material test certificates, long schedules
# ----------------------------------------------------------------------------------
LENGTHS = {"short": None,
           "medium": dict(ts_lines=150, s6=40, s7=30, annex=15),
           "long": dict(ts_lines=600, s6=120, s7=80, annex=40),
           "xlong": dict(ts_lines=1500, s6=300, s7=200, annex=80)}
SUBJECTS = ["gate valves", "ball valves", "check valves", "flanges", "pressure transmitters", "strainers",
            "heat exchangers", "pump sets", "valve actuators", "instrument tubing"]
ZONES = ["body", "bonnet", "trim", "bolting", "accessories"]
TS_TEMPLATES = [
 "Welding procedures for the {zone} of {subj} shall be qualified to {std} before production welding starts.",
 "Welders working on the {zone} of {subj} shall hold a current qualification to {wstd}.",
 "Radiographic or ultrasonic examination shall cover {pct}% of butt welds on the {zone} of {subj}.",
 "Surface finish of the {zone} of {subj} shall be no rougher than Ra {ra} um.",
 "Coating on the {zone} of {subj} shall have a dry film thickness of at least {dft} um.",
 "Fasteners used on the {zone} of {subj} shall be supplied with {thread} threads.",
 "The {zone} of {subj} shall be marked with the item code in characters at least {mm} mm high.",
 "Dimensional records for the {zone} of {subj} shall be kept for {y} years.",
 "Hardness of the {zone} of {subj} shall be measured at {n} locations per item.",
 "Liquid penetrant examination shall be performed on {pct}% of machined surfaces of the {zone} of {subj}.",
 "Cleanliness of the {zone} of {subj} shall be verified before assembly and recorded.",
 "Lifting points on the {zone} of {subj} shall be proof tested to {x} times the working load limit.",
 "Lubricants applied to the {zone} of {subj} shall be approved by the Purchaser in writing.",
 "Packing for the {zone} of {subj} shall include {n} desiccant bags per crate.",
 "Name plates for {subj} shall be fixed to the {zone} with stainless steel pins.",
 "Torque values for bolting on the {zone} of {subj} shall be recorded on the inspection record.",
 "Gasket material for the {zone} of {subj} shall be {gasket}.",
 "Storage of the {zone} of {subj} before delivery shall be indoors at temperatures above {temp} C.",
 "Non-conforming {zone} components of {subj} shall be segregated and tagged until dispositioned.",
 "Surface preparation of the {zone} of {subj} shall be to {sa} before coating.",
 "Heat treatment records for the {zone} of {subj} shall show furnace identity and chart numbers.",
 "Positive material identification shall be carried out on {pct}% of {zone} components of {subj}.",
 "Seals on the {zone} of {subj} shall be of {seal} type.",
 "Drawings for the {zone} of {subj} shall be issued for approval at least {n} working days before manufacture starts.",
 "Weld repairs on the {zone} of {subj} are limited to {n} attempts at the same location without Purchaser approval.",
 "Thread protectors shall be fitted to all threaded connections on the {zone} of {subj}.",
 "The {zone} of {subj} shall be free from arc strikes, spatter and sharp edges.",
 "Inspection of the {zone} of {subj} shall be recorded on forms approved by the Purchaser.",
 "Certificates for the {zone} of {subj} shall be traceable to heat or batch numbers.",
 "Visual examination of the {zone} of {subj} shall be carried out under at least {lux} lux.",
]
TS_PARAMS = dict(std=["ASME IX", "ISO 15614-1", "EN ISO 15614-1"], wstd=["ASME IX", "ISO 9606-1", "EN ISO 9606-1"],
                 pct=[5, 10, 20, 100], ra=[1.6, 3.2, 6.3, 12.5], dft=[120, 160, 200, 250, 300],
                 thread=["UNC", "UNF", "metric coarse"], mm=[6, 8, 10, 12], y=[5, 7, 10], n=[3, 5, 8, 10],
                 x=[1.5, 2, 2.5], gasket=["spiral wound", "ring joint, soft iron", "PTFE envelope"], temp=[5, 10],
                 sa=["Sa 2", "Sa 2.5"], seal=["PTFE", "graphite", "elastomer"], lux=[500, 750, 1000])
MINPROP = {"ASTM A105": (250, 485, 22), "ASTM A350 LF2": (250, 485, 22), "ASTM A182 F316L": (170, 485, 30),
           "ASTM A216 WCB": (250, 485, 22), "ASTM A351 CF8M": (205, 485, 30)}
SPARES = ["Gasket set", "Stem seal kit", "O-ring kit", "Bolting set", "Gland packing", "Bearing set", "Wear ring",
          "Seat insert", "Coil assembly", "Diaphragm kit"]
MILESTONES = ["Material order placed", "Raw material received", "First article cut", "Machining started",
              "Welding complete", "Heat treatment complete", "Machining complete", "Assembly complete",
              "Painting complete", "Inspection release", "Packing complete", "Ready for dispatch"]
A_VERBS = ["provide", "maintain", "submit", "retain", "update", "confirm", "archive", "display"]
A_OBJS = ["a current organisation chart", "the manufacturing programme", "a list of approved sub-suppliers",
          "calibration records for inspection equipment", "a register of non-conformances",
          "the packing list for each shipment", "records of staff training", "a copy of the quality plan",
          "the welding procedure register", "evidence of material traceability"]
A_CONDS = ["on the Purchaser's request", "at each review meeting", "before the start of manufacture",
           "with each delivery", "every {n} weeks during manufacture", "before final inspection"]


def long_init(rng, X, P, L):
    items = X["items"]
    P["ts_rev"] = P["spec_rev"]; P["ts_hold"] = "hold point"
    X["ts_bar"] = dict(BAR)
    X["used"]["mtc"] = set(); X["used"]["s6"] = set()
    mt = []
    for it in items:
        ymin, tmin, emin = MINPROP[it["mat"]]
        imp = [rng.randint(34, 120) for _ in range(3)]
        mt.append(dict(heat=it["heat"], mat=it["mat"], c=round(rng.uniform(0.08, 0.24), 2), mn=round(rng.uniform(0.6, 1.4), 2),
                       si=round(rng.uniform(0.15, 0.4), 2), p=round(rng.uniform(0.008, 0.03), 3), s=round(rng.uniform(0.004, 0.03), 3),
                       y=ymin + rng.randint(15, 110), t=tmin + rng.randint(15, 120), e=emin + rng.randint(2, 12), imp=imp))
    X["mtc"] = mt
    rows6 = []
    for i in range(L["s6"]):
        it = rng.choice(items)
        qty = rng.randint(1, 20); unit = round(rng.uniform(10, 900), 2)
        rows6.append(dict(part=f"SP-{i+1:04d}", desc=f"{rng.choice(SPARES)} for {it['code']}", qty=qty, unit=unit, shown=None))
    X["s6"] = rows6
    X["s7_bad_last"] = False
    # topics for the technical specification: each (template, subject, zone) used at most once
    combos = [(t, s_, z) for t in range(len(TS_TEMPLATES)) for s_ in SUBJECTS for z in ZONES]
    rng.shuffle(combos)
    X["ts_topics"] = combos[:L["ts_lines"]]
    A = [(v, o, c) for v in A_VERBS for o in A_OBJS for c in A_CONDS]
    rng.shuffle(A)
    X["annex_extra"] = A[:L["annex"]]


def m40(X):
    P = X["P"]; P["ts_rev"] = other(X["rng"], list("ABCDEF"), P["spec_rev"])
    return F(4, True, "M40", [("TS", "TS.H"), ("SA", "S2.H")],
             f"Technical Specification is Rev {P['ts_rev']}; Schedule 2 of the Agreement cites Rev {P['spec_rev']}.")

def m41(X):
    k = pick(X, "mtc")
    if k is None: return None
    X["mtc"][k]["heat"] = f"H{X['rng'].randint(100000, 999999)}"
    return F(4, True, "M41", [("MTC", f"M.{k+1}.1"), ("CERT", f"C.{k+1}")],
             f"Heat number {X['mtc'][k]['heat']} on the material certificate differs from {X['items'][k]['heat']} on the release certificate (item {k+1}).")

def m42(X):
    k = pick(X, "mtc")
    if k is None: return None
    mat = X["items"][k]["mat"]; ymin = MINPROP[mat][0]
    X["mtc"][k]["y"] = ymin - X["rng"].randint(10, 40)
    j = MATERIALS.index(mat) + 1
    return F(4, True, "M42", [("MTC", f"M.{k+1}.3"), ("TS", f"TS.Y{j}")],
             f"Yield strength {X['mtc'][k]['y']} MPa for item {k+1} is below the {ymin} MPa minimum for {mat} in the Technical Specification.")

def m43(X):
    k = pick(X, "po"); 
    if k is None: return None
    cls = X["items"][k]["cls"]; ci = CLASSES.index(cls)
    X["ts_bar"][cls] = int(BAR[cls] * X["rng"].choice([0.8, 1.2, 0.9]))
    locs = [("TS", f"TS.P{ci+1}")] + [("SA", f"S2.{i+1}") for i, it in enumerate(X["items"]) if it["cls"] == cls]
    return F(4, True, "M43", locs, f"Technical Specification gives {X['ts_bar'][cls]} bar for {cls}; Schedule 2 requires {BAR[cls]} bar.")

def m44(X):
    X["P"]["ts_hold"] = "witness point"
    return F(4, True, "M44", [("TS", "TS.HP"), ("SA", "@holdpts")],
             "Technical Specification calls the shell hydrostatic test a witness point; clause 7.2 makes it a hold point.")

def m46(X):
    n = len(X["s6"]); i = pick(X, "s6") if False else X["rng"].randrange(n)
    r = X["s6"][i]; true = round(r["qty"] * r["unit"], 2)
    r["shown"] = round(true * X["rng"].choice([0.9, 1.1, 1.2, 0.8]), 2)
    return F(4, True, "M46", [("SA", f"S6.{i+1}")],
             f"Schedule 6 line {i+1}: value {m(r['shown'])} but {r['qty']} x {m(r['unit'])} = {m(true)}.")

def m47(X):
    X["s7_bad_last"] = True
    return F(4, True, "M47", [("SA", f"S7.@LAST"), ("SA", "S3.6")],
             "Last delivery milestone in Schedule 7 falls after the Long-Stop Delivery Date in Schedule 3.")

MUT.update({"M40": m40, "M41": m41, "M42": m42, "M43": m43, "M44": m44, "M46": m46, "M47": m47})
LONG4 = ["M40", "M41", "M42", "M43", "M44", "M46", "M47"]
KEYWORDS.update({"M40": ["rev", "revision", "specification"], "M41": ["heat", "number", "traceab"],
                 "M42": ["yield", "minimum", "below", "strength"], "M43": ["pressure", "bar", "test"],
                 "M44": ["hold", "witness", "hydro"], "M46": ["value", "total", "calculat", "arithmetic", "multipl"],
                 "M47": ["milestone", "long-stop", "long stop", "after", "delivery"]})

# decoys that conflict with mutations (cannot coexist)
DECOY_CONFLICT = {"D1": {"M23", "M24", "M25"}, "D2": {"M10", "M16"}, "D3": set(), "D4": {"M20"},
                  "D5": {"M01", "M02"}, "D6": {"M21"}, "D7": {"M09"}}


def build_pack(rng, pid, mut_ids, decoy_ids, size, L=None):
    P = {}
    X = {"rng": rng, "P": P, "used": {"sa_line": set(), "po": set(), "cert": set()},
         "sa_line_override": {}, "sa_total_override": None}
    buyer = rng.choice(BUYERS); supplier = rng.choice(SUPPLIERS)
    n = rng.randint(5, 7)
    types = rng.sample(ITEM_TYPES, min(n, len(ITEM_TYPES)))
    while len(types) < n:
        types.append(rng.choice(ITEM_TYPES))
    items = []
    for i, (code, desc, base) in enumerate(types):
        cls = rng.choice(CLASSES)
        qmax = rng.choice([40, 60, 80, 120, 200])
        items.append(dict(code=f"{code}-{rng.randint(100, 999)}", desc=f"{desc}, DN{rng.choice([50, 80, 100, 150, 200])}",
                          qty_max=qmax, unit=round(base * rng.uniform(0.8, 1.3), 2), cls=cls,
                          mat=rng.choice(MATERIALS), bar=BAR[cls], heat=f"H{rng.randint(100000, 999999)}"))
    X["items"] = items
    sa_date = dt.date(2026, rng.randint(1, 5), rng.randint(1, 28))
    po_date = sa_date + dt.timedelta(days=rng.randint(25, 90))
    lead = rng.choice([12, 14, 16, 20])
    po_delivery = po_date + dt.timedelta(weeks=lead, days=rng.randint(0, 30))
    test_date = po_delivery - dt.timedelta(days=rng.randint(12, 28))
    liab = rng.choice([500000, 1000000, 2500000, 5000000])
    if "D7" in decoy_ids: liab = 50000000
    law = rng.choice(["Scotland", "Singapore"]) if "D2" in decoy_ids else "England and Wales"
    pay = rng.choice([30, 45, 60]); war = rng.choice([12, 18, 24]); ldcap = rng.choice([5, 10])
    P.update(dict(
        sa_no=f"SA-2026-{rng.randint(1000, 9999)}", sa_date=sa_date, eff=sa_date, po_no=f"PO-{rng.randint(450000, 459999)}",
        po_date=po_date, vo_no="VO-01", cert_no=f"IRC-{rng.randint(10000, 99999)}", spec=f"TS-{rng.randint(100, 999)}",
        spec_rev=rng.choice("ABCD"), lead=lead, po_delivery=po_delivery, test_date=test_date,
        cal_expiry=test_date + dt.timedelta(days=rng.randint(40, 300)),
        expiry=sa_date + dt.timedelta(days=730), longstop_clause=po_delivery + dt.timedelta(days=150),
        pay_main=pay, pay_sched=pay, pay_po=pay, war_def=war, war_clause=war,
        ld_rate=rng.choice([0.5, 1.0]), ld_cap_clause=ldcap, ld_cap_sched=ldcap,
        liab_clause=liab, liab_sched=liab, law_sa=law, law_sched=law, law_po=law,
        notice_clause=rng.choice([3, 5, 7]), itp_hold="H (Hold)", sig_supplier_blank=False,
        buyer=buyer, supplier=supplier, xref_bad=None, total_price_term=False, autorenew=None))
    P["sa_no_in_po"] = P["sa_no"]; P["po_no_in_cert"] = P["po_no"]
    if L: long_init(rng, X, P, L)
    P["spec_rev_po"] = P["spec_rev"]; P["notice_itp"] = P["notice_clause"]
    P["longstop_sched"] = P["longstop_clause"]
    X["po"] = []; X["cert"] = []
    X["vo_k"] = rng.randrange(n)
    for i, it in enumerate(items):
        q = max(2, int(it["qty_max"] * rng.uniform(0.3, 0.8)))
        X["po"].append(dict(qty=q, unit=it["unit"], cls=it["cls"], mat=it["mat"]))
    k = X["vo_k"]; old = X["po"][k]["qty"]
    new = min(items[k]["qty_max"], old + rng.randint(2, 8))
    X["vo"] = dict(old=old, new=new, unit_disp=items[k]["unit"], total_wrong=0, xref_wrong=False)
    for i, it in enumerate(items):
        fq = new if i == k else X["po"][i]["qty"]
        X["cert"].append(dict(qty=fq, mat=it["mat"], bar=it["bar"] + rng.randint(0, 3), remark="", heat=it["heat"]))

    # mutations
    findings = []
    order = sorted(mut_ids, key=lambda x: x)
    for mid in order:
        f = MUT[mid](X)
        if f is None: return None
        f["mid"] = mid; findings.append(f)

    # decoys
    decoys = []
    if "D1" in decoy_ids:
        decoys.append(dict(did="D1", locs=[("VO", "VO.1"), ("VO", "VO.2"), ("VO", "VO.3")],
                           desc="Variation increases the PO quantity within the Maximum Quantity with correct arithmetic and authority."))
    if "D2" in decoy_ids:
        decoys.append(dict(did="D2", locs=[("SA", "@law"), ("SA", "S3.5"), ("PO", "PT.1")],
                           desc=f"{law} law is unusual for this buyer but is used consistently."))
    if "D3" in decoy_ids:
        X["po_date_numeric"] = True
        decoys.append(dict(did="D3", locs=[("PO", "PO.H")], desc="PO date written numerically; same date as stated elsewhere."))
    if "D4" in decoy_ids:
        j = pick(X, "cert")
        if j is not None:
            part = rng.randint(3, 8); X["cert"][j]["qty"] -= part
            X["cert"][j]["remark"] = f"Partial release; balance of {part} to follow under same PO"
            decoys.append(dict(did="D4", locs=[("CERT", f"C.{j+1}")], desc="Certificate releases fewer than ordered, with an explicit partial-release note."))
    if "D5" in decoy_ids:
        X["total_rounded"] = True
        decoys.append(dict(did="D5", locs=[("SA", "S1.T")], desc="Schedule 1 total rounded to the nearest pound, as stated in a note."))
    if "D6" in decoy_ids:
        P["cal_expiry"] = P["test_date"]
        decoys.append(dict(did="D6", locs=[("CERT", "CT.1"), ("CERT", "CT.2")], desc="Calibration expires on the test date; still valid on that day."))
    if "D7" in decoy_ids:
        decoys.append(dict(did="D7", locs=[("SA", "@liab"), ("SA", "S3.4")], desc="High liability cap, stated consistently."))

    # ---- fill SA ----
    keys = list(FILL.keys())
    must = ["variations_dummy"]
    chosen = rng.sample([k_ for k_ in keys], min(size, len(keys)))
    if "insurance" not in chosen: chosen.append("insurance")
    rng.shuffle(chosen)
    clauses = []
    def C(key, title, subs): clauses.append((key, title, subs))
    C("defs", "Definitions", [
        ("def_cp", '"Contract Price" means the total price payable for the Goods as set out in Schedule 1.'),
        ("war_def", f'"Warranty Period" means {P["war_def"]} months from the date of delivery of the Goods.'),
        ("def_goods", '"Goods" means the items listed in Schedule 1 and specified in Schedule 2.'),
        ("def_po", '"Purchase Order" means an order for Goods placed by the Purchaser under this Agreement.')])
    C("scope", "Scope", [
        ("scope1", f'Supplier shall supply the Goods in accordance with Schedule 2 and Specification {P["spec"]}.'),
        ("maxqty", "The Purchaser may order up to the Maximum Quantity of each item stated in Schedule 1. Orders above the Maximum Quantity require a Variation under clause @@variations@@.")])
    C("termc", "Term", [
        ("eff", f'This Agreement takes effect on {d(P["eff"])} (the "Effective Date").'),
        ("term", f"This Agreement continues until {d(P['expiry'])} and shall not renew automatically; any extension requires written agreement signed by both parties.")])
    cp = "Total Price" if P["total_price_term"] else "Contract Price"
    ref = "@@variations@@" if P["xref_bad"] is None else "@@BAD@@"
    C("pricec", "Price", [
        ("price1", "The Contract Price is the ceiling value in Schedule 1. Prices are firm and fixed for the Term."),
        ("price_term", f"The {cp} shall not be subject to adjustment except under clause {ref}.")])
    C("delc", "Delivery", [
        ("longstop", f'Supplier shall deliver the Goods by the Delivery Date stated in each Purchase Order and in any case no later than {d(P["longstop_clause"])} (the "Long-Stop Delivery Date").'),
        ("lead", f"Each Purchase Order shall allow not less than {P['lead']} weeks from the date of the Purchase Order to the Delivery Date.")])
    C("payc", "Payment", [
        ("pay_days", f"The Purchaser shall pay each undisputed invoice within {P['pay_main']} days of receipt."),
        ("pay2", "Invoices shall be issued only after the Inspection Release Certificate has been issued under clause @@inspection@@.")])
    C("inspection", "Inspection", [
        ("notice", f"The Purchaser may inspect the Goods at any stage of manufacture on {P['notice_clause']} working days' notice."),
        ("holdpts", "The shell hydrostatic test is a hold point and the final inspection is a witness point, as set out in Schedule 4."),
        ("cal", "All test equipment shall hold a valid calibration certificate on the date of the test.")])
    C("warc", "Warranty", [
        ("war_clause", f"Supplier warrants the Goods against defects for {P['war_clause']} months from delivery."),
        ("war2", "Supplier shall repair or replace defective Goods at its own cost within a reasonable time.")])
    C("ldc", "Liquidated Damages", [
        ("ld1", f"If delivery is late, Supplier shall pay liquidated damages at {P['ld_rate']}% of the value of the late Goods for each complete week of delay."),
        ("ld_cap", f"Liquidated damages shall not exceed {P['ld_cap_clause']}% of the value of the late Goods.")])
    C("liabc", "Limitation of Liability", [
        ("liab", f"Each party's total aggregate liability under this Agreement is limited to {m(P['liab_clause'])}, except for death or personal injury caused by negligence, and fraud."),
        ("liab2", "Neither party is liable for indirect or consequential loss.")])
    fp = dict(y=rng.choice([2, 3, 5]), dd=rng.choice([14, 21, 30]), dd2=rng.choice([60, 90, 120]),
              ins=m(rng.choice([5000000, 10000000, 20000000])).replace(".00", ""))
    for key in chosen:
        title, sents = FILL[key]
        C(key, title, [(f"{key}{i}", s.format(**fp)) for i, s in enumerate(sents)])
    C("variations", "Variations", [
        ("var1", "No variation is effective unless recorded in a written Variation Order signed by both parties."),
        ("var2", "A Variation Order shall state the original and revised quantities and the effect on the price.")])
    C("govlaw", "Governing Law", [
        ("law", f"This Agreement is governed by the laws of {P['law_sa']}."),
        ("law2", f"The courts of {law} have exclusive jurisdiction.")])
    R = {}; S = {}
    for i, (key, title, subs) in enumerate(clauses, 1):
        R[key] = str(i)
        for j, (sk, _) in enumerate(subs, 1): S[sk] = f"{i}.{j}"
    R["BAD"] = str(len(clauses) + rng.randint(3, 9))
    def resolve(t):
        return re.sub(r"@@(\w+)@@", lambda mo: R.get(mo.group(1), "?"), t)
    if X["vo"]["xref_wrong"]: pass
    sa = [f"SA.H  SUPPLY AGREEMENT No. {P['sa_no']} dated {d(P['sa_date'])}",
          f"Between {P['buyer']} (the Purchaser) and {P['supplier']} (the Supplier).", ""]
    for i, (key, title, subs) in enumerate(clauses, 1):
        sa.append(f"{i}. {title.upper()}")
        for j, (sk, t) in enumerate(subs, 1):
            sa.append(f"{i}.{j}  {resolve(t)}")
        sa.append("")
    sa.append("SCHEDULE 1 - PRICE SCHEDULE (ceiling quantities)")
    sa.append("Ref   | Item | Description | Max Qty | Unit price | Max value")
    tot = 0.0
    for i, it in enumerate(items):
        true = round(it["qty_max"] * it["unit"], 2); tot += true
        shown = X["sa_line_override"].get(i, true)
        sa.append(f"S1.{i+1} | {it['code']} | {it['desc']} | {it['qty_max']} | {m(it['unit'])} | {m(shown)}")
    if X["sa_total_override"] is not None:
        sa.append(f"S1.T  | TOTAL | | | | {m(X['sa_total_override'])}")
    elif X.get("total_rounded"):
        sa.append(f"S1.T  | TOTAL | | | | £{round(tot):,}   (Note: total rounded to the nearest pound)")
    else:
        sa.append(f"S1.T  | TOTAL | | | | {m(tot)}")
    sa.append("")
    sa.append(f"S2.H  SCHEDULE 2 - TECHNICAL REQUIREMENTS (Specification {P['spec']} Rev {P['spec_rev']})")
    sa.append("Ref   | Item | Rating | Material | Minimum shell test pressure (bar)")
    for i, it in enumerate(items):
        sa.append(f"S2.{i+1} | {it['code']} | {it['cls']} | {it['mat']} | {it['bar']}")
    sa.append("")
    sa.append("SCHEDULE 3 - COMMERCIAL SUMMARY")
    sa += [f"S3.1  Payment: {P['pay_sched']} days from receipt of invoice",
           f"S3.2  Warranty: {P['war_def']} months from delivery",
           f"S3.3  LD cap: {P['ld_cap_sched']}% of value of late Goods",
           f"S3.4  Liability cap: {m(P['liab_sched'])}",
           f"S3.5  Governing law: {P['law_sched']}",
           f"S3.6  Long-Stop Delivery Date: {d(P['longstop_sched'])}", ""]
    sa.append(f"S4.H  SCHEDULE 4 - INSPECTION AND TEST PLAN (notice of inspection: {P['notice_itp']} working days)")
    sa += ["S4.1  Material verification (PMI) | R (Review)",
           f"S4.2  Shell hydrostatic test | {P['itp_hold']}",
           "S4.3  Final visual and dimensional inspection | W (Witness)", ""]
    sa.append("SCHEDULE 5 - ANNEX: GENERAL CONDITIONS")
    ann = rng.sample(ANNEX_FILL, 3)
    for i, t in enumerate(ann, 1): sa.append(f"A.{i}  {t.format(dd=rng.choice([14, 30]))}")
    if L:
        for i, (v_, o_, c_) in enumerate(X["annex_extra"], len(ann) + 1):
            sa.append(f"A.{i}  Supplier shall {v_} {o_} {c_.format(n=rng.choice([2, 4, 6]))}.")
    if P["autorenew"]:
        sa.append(f"A.AR  Notwithstanding clause 3.2, this Agreement shall renew automatically for successive periods of 12 months unless either party gives {P['autorenew']} days' written notice before the end of the then-current period.")
    if L:
        sa.append("")
        sa.append("SCHEDULE 6 - RECOMMENDED SPARE PARTS")
        sa.append("Ref   | Part | Description | Qty | Unit price | Value")
        t6 = 0.0
        for i, r in enumerate(X["s6"], 1):
            true = round(r["qty"] * r["unit"], 2); t6 += true
            shown = r["shown"] if r["shown"] is not None else true
            sa.append(f"S6.{i} | {r['part']} | {r['desc']} | {r['qty']} | {m(r['unit'])} | {m(shown)}")
        sa.append(f"S6.T | TOTAL | | | | {m(round(t6, 2))}")
        sa.append("")
        sa.append("SCHEDULE 7 - DELIVERY MILESTONES")
        sa.append("Ref   | Milestone | Date")
        n7 = L["s7"]; base_ls = P["longstop_sched"]
        span = (base_ls - P["eff"]).days - 40
        cur = P["eff"] + dt.timedelta(days=10); X["s7"] = []
        for i in range(1, n7 + 1):
            it_ = items[(i - 1) % len(items)]
            text_ = f"{MILESTONES[(i - 1) % len(MILESTONES)]} - {it_['code']}"
            dte = base_ls + dt.timedelta(days=rng.randint(5, 40)) if (i == n7 and X["s7_bad_last"]) else cur
            sa.append(f"S7.{i} | {text_} | {d(dte)}")
            cur = cur + dt.timedelta(days=max(1, span // n7)); X["s7"].append(dte)
    sa.append("")
    sa.append(f"SIG.P  Signed for the Purchaser: A. Whitcombe (Procurement Director)   Date: {d(P['sa_date'])}")
    if P["sig_supplier_blank"]:
        sa.append("SIG.S  Signed for the Supplier: ______________________   Date: ____________")
    else:
        sa.append(f"SIG.S  Signed for the Supplier: R. Halloran (Commercial Manager)   Date: {d(P['sa_date'])}")

    # ---- PO ----
    po_ds = P["po_date"].strftime("%d/%m/%Y") if X.get("po_date_numeric") else d(P["po_date"])
    po = [f"PO.H  PURCHASE ORDER No. {P['po_no']} dated {po_ds}",
          f"Issued under Supply Agreement No. {P['sa_no_in_po']} dated {d(P['sa_date'])}",
          f"To: {P['supplier']}   From: {P['buyer']}", "",
          "Ref  | Item | Description | Rating | Material | Qty | Unit price | Line value"]
    pt = 0.0
    for i, it in enumerate(items):
        r = X["po"][i]; lv = round(r["qty"] * r["unit"], 2); pt += lv
        po.append(f"L.{i+1} | {it['code']} | {it['desc']} | {r['cls']} | {r['mat']} | {r['qty']} | {m(r['unit'])} | {m(lv)}")
    po.append(f"L.T  | TOTAL | | | | | | {m(round(pt, 2))}")
    po += ["", f"PT.1  Governing law: {P['law_po']}", f"PT.2  Payment: {P['pay_po']} days from receipt of invoice",
           f"PT.3  Delivery Date: {d(P['po_delivery'])}",
           f"PT.4  Goods to be supplied to Specification {P['spec']} Rev {P['spec_rev_po']}",
           "PT.5  Inspection in accordance with Schedule 4 of the Agreement."]
    # ---- VO ----
    vo = X["vo"]; k = X["vo_k"]; it = items[k]
    oldv = round(vo["old"] * vo["unit_disp"], 2); newv = round(vo["new"] * vo["unit_disp"], 2); diff = round(newv - oldv, 2)
    before = round(pt, 2); after = round(before + diff + vo["total_wrong"], 2)
    var_ref = R["payc"] if vo["xref_wrong"] else R["variations"]
    vos = [f"VO.H  VARIATION ORDER No. {P['vo_no']} to Purchase Order {P['po_no']}",
           f"VO.1  Item {it['code']} (PO line {k+1}): quantity changed from {vo['old']} to {vo['new']} at unit price {m(vo['unit_disp'])}.",
           f"VO.2  Original line value {m(oldv)}; revised line value {m(newv)}; increase {m(diff)}.",
           f"VO.3  PO total before this Variation {m(before)}; revised PO total {m(after)}.",
           f"VO.4  Issued under clause {var_ref} of the Agreement.",
           f"VO.S1  Signed for the Purchaser: A. Whitcombe (Procurement Director)   Date: {d(P['po_date'] + dt.timedelta(days=12))}",
           f"VO.S2  Signed for the Supplier: R. Halloran (Commercial Manager)   Date: {d(P['po_date'] + dt.timedelta(days=12))}"]
    # ---- CERT ----
    ce = [f"C.H  INSPECTION RELEASE CERTIFICATE No. {P['cert_no']}",
          f"Purchase Order No. {P['po_no_in_cert']}   Supplier: {P['supplier']}", "",
          "Ref  | Item | Material | Heat No. | Qty released | Shell test pressure achieved (bar) | Remark"]
    for i, it in enumerate(items):
        c = X["cert"][i]
        ce.append(f"C.{i+1} | {it['code']} | {c['mat']} | {c['heat']} | {c['qty']} | {c['bar']} | {c['remark']}")
    ce += ["", f"CT.1  Date of test: {d(P['test_date'])}",
           f"CT.2  Pressure gauge calibration certificate valid until: {d(P['cal_expiry'])}",
           "CT.3  Purchaser's inspector attended the shell test.",
           f"C.SIG  Signed: M. Tennant (QA Manager, {P['supplier']})   Date: {d(P['test_date'] + dt.timedelta(days=2))}"]

    extra = {}
    if L:
        ts = [f"TS.H  TECHNICAL SPECIFICATION {P['spec']} Rev {P['ts_rev']}",
              "This specification applies to all Goods supplied under the Agreement.", ""]
        topics = X["ts_topics"]
        at_p, at_y = len(topics) // 3, (2 * len(topics)) // 3
        for i, (t_, s_, z_) in enumerate(topics):
            if i == at_p:
                ts.append("MINIMUM SHELL TEST PRESSURES BY RATING")
                for ci, c_ in enumerate(CLASSES, 1): ts.append(f"TS.P{ci} | {c_} | {X['ts_bar'][c_]} bar")
                ts.append(f"TS.HP  The shell hydrostatic test is a {P['ts_hold']} and the final inspection is a witness point.")
                ts.append("")
            if i == at_y:
                ts.append("MINIMUM MECHANICAL PROPERTIES")
                ts.append("Ref | Material | Yield min (MPa) | Tensile min (MPa) | Elongation min (%)")
                for mi, mt_ in enumerate(MATERIALS, 1):
                    y_, t2_, e_ = MINPROP[mt_]; ts.append(f"TS.Y{mi} | {mt_} | {y_} | {t2_} | {e_}")
                ts.append("TS.C  Phosphorus max 0.035% and sulphur max 0.040% in all materials; impact test minimum average 27 J at the design temperature.")
                ts.append("")
            vals = {k_: rng.choice(v_) for k_, v_ in TS_PARAMS.items()}
            ts.append(f"TS.{i+1}  " + TS_TEMPLATES[t_].format(subj=s_, zone=z_, **vals))
        mt = [f"MTC.H  MATERIAL TEST CERTIFICATES for Purchase Order {P['po_no']}", ""]
        for k_, (it_, r_) in enumerate(zip(items, X["mtc"]), 1):
            mt.append(f"M.{k_}.1 | {it_['code']} | Heat {r_['heat']} | {r_['mat']}")
            mt.append(f"M.{k_}.2 | Chemistry | C {r_['c']} | Mn {r_['mn']} | Si {r_['si']} | P {r_['p']} | S {r_['s']}")
            mt.append(f"M.{k_}.3 | Tensile | Yield {r_['y']} MPa | Tensile {r_['t']} MPa | Elongation {r_['e']}%")
            mt.append(f"M.{k_}.4 | Impact | {r_['imp'][0]} J | {r_['imp'][1]} J | {r_['imp'][2]} J | avg {round(sum(r_['imp']) / 3, 1)} J")
        extra = {"TS": "\n".join(ts), "MTC": "\n".join(mt)}

    def res(loc):
        doc, ref = loc
        if ref.startswith("@"):
            return [doc, S.get(ref[1:], R.get(ref[1:], "?"))]
        return [doc, ref.replace("@LAST", str(len(X.get("s7", []))))]
    for f in findings: f["locs"] = [res(l) for l in f["locs"]]
    for dd_ in decoys: dd_["locs"] = [res(l) for l in dd_["locs"]]
    docs = {"SA": "\n".join(sa), "PO": "\n".join(po), "VO": "\n".join(vos), "CERT": "\n".join(ce)}
    docs.update(extra)
    return docs, findings, decoys


def write_pdf(path, text):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(path, pagesize=A4); W, H = A4; y = H - 40
    c.setFont("Courier", 8)
    for line in text.split("\n"):
        chunks = [line[i:i + 118] for i in range(0, max(len(line), 1), 118)] or [""]
        for ch in chunks:
            if y < 40: c.showPage(); c.setFont("Courier", 8); y = H - 40
            c.drawString(36, y, ch); y -= 10
    c.save()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True); ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--packs", type=int, default=36); ap.add_argument("--clean", type=int, default=6)
    ap.add_argument("--size", type=int, default=9, help="number of filler clauses (document length)")
    ap.add_argument("--pdf", action="store_true"); ap.add_argument("--prefix", default="P")
    ap.add_argument("--length", default="short", choices=list(LENGTHS), help="short | medium | long | xlong")
    a = ap.parse_args()
    L = LENGTHS[a.length]
    T = {k_: list(v_) for k_, v_ in TIERS.items()}
    if L:
        L = dict(L); L["s7"] = L.pop("s7") if "s7" in L else max(20, L["s6"] * 2 // 3)
        T[4] += LONG4; T[2].remove("M04")
        if a.size == 9: a.size = 18
    rng = random.Random(a.seed)
    key = dict(seed=a.seed, packs=[], note="Fictional documents. Findings located by (doc, ref) as printed in the text.")
    nfind = 0; tot_chars = 0
    clean_idx = set(rng.sample(range(a.packs), a.clean))
    for pi in range(a.packs):
        pid = f"{a.prefix}{pi+1:02d}"
        is_clean = pi in clean_idx
        for attempt in range(50):
            muts = []
            if not is_clean:
                muts = [rng.choice(T[1]), rng.choice(T[2]), rng.choice(T[3]), rng.choice(T[3]), rng.choice(T[4])]
                if L: muts += [rng.choice(T[4]), rng.choice(T[4])]
                if rng.random() < 0.5: muts.append(rng.choice(T[2]))
                if rng.random() < 0.4: muts.append(rng.choice(T[3]))
                muts = sorted(set(muts))
            pool = [dd for dd in DECOY_CONFLICT if not (DECOY_CONFLICT[dd] & set(muts))]
            decs = rng.sample(pool, min(len(pool), rng.randint(2, 4)))
            res = build_pack(random.Random(rng.random()), pid, muts, decs, a.size + rng.randint(-2, 3), L)
            if res: break
        docs, findings, decoys = res
        pdir = os.path.join(a.out, "packs", pid); os.makedirs(pdir, exist_ok=True)
        tot_chars += sum(len(t_) for t_ in docs.values())
        for name, text in docs.items():
            with open(os.path.join(pdir, f"{name}.md"), "w") as fh: fh.write(text + "\n")
            if a.pdf: write_pdf(os.path.join(pdir, f"{name}.pdf"), text)
        fl = []
        for i, f in enumerate(findings, 1):
            fl.append(dict(id=f"{pid}-F{i:02d}", tier=f["tier"], material=f["material"], type=f["mid"],
                           locs=f["locs"], desc=f["desc"], keywords=KEYWORDS[f["mid"]]))
        nfind += len(fl)
        key["packs"].append(dict(pack=pid, clean=is_clean, findings=fl, decoys=decoys))
    os.makedirs(os.path.join(a.out, "key"), exist_ok=True)
    with open(os.path.join(a.out, "key", "answer_key.json"), "w") as fh: json.dump(key, fh, indent=1)
    t = {1: 0, 2: 0, 3: 0, 4: 0}; mat = 0
    for p in key["packs"]:
        for f in p["findings"]: t[f["tier"]] += 1; mat += f["material"]
    print(f"{a.out}: {a.packs} packs ({a.clean} clean), {nfind} findings, by tier {t}, material {mat}, "
          f"decoys {sum(len(p['decoys']) for p in key['packs'])}; about {tot_chars / a.packs / 3.6:,.0f} tokens per pack (estimate)")


if __name__ == "__main__":
    main()
