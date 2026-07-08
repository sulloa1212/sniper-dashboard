#!/usr/bin/env python3
"""
Build latest.html from dashboard_data.json + the locked template.
The AI supplies only raw values in the JSON; this script computes every angle,
bar width, and CSS class so the layout can never be drawn wrong.

Usage:  python build_html.py
Inputs: Sniper_Dashboard_TEMPLATE.html  (locked template, for head + tail)
        template_body.html.j2           (dynamic body)
        dashboard_data.json             (today's data)
Output: latest.html
"""
import json, re
from jinja2 import Template

TEMPLATE   = "Sniper_Dashboard_TEMPLATE.html"
BODY_J2    = "template_body.html.j2"
DATA       = "dashboard_data.json"
OUT        = "latest.html"

BAND_CLASS = {"COOL": "cool", "MILD": "mild", "WARM": "warm", "HOT": "hot", "CRITICAL": "crit", "CRIT": "crit"}
DOT        = {"GREEN": "g", "YELLOW": "y", "RED": "r"}
# Header tag next to the H1 — maps 1:1 from the verdict color (spec-locked).
TAG        = {"GREEN": ("t-bull", "RISK-ON"), "YELLOW": ("t-neut", "CAUTION"), "RED": ("t-bear", "RISK-OFF")}
BIAS_CLASS = {"bull": "bull", "bear": "bear", "coin": "coin"}
VAL_CLASS  = {"pending": "val-pending", "watch": "val-watch", "invalid": "val-invalid",
              "ineligible": "val-invalid", "skip": "val-invalid", "na": "val-invalid"}
GAP_RISK_CLASS = {"high": "gap-hi", "elevated": "gap-el", "moderate": "gap-mod", "low": "gap-lo"}
LEAN_CLASS = {"up": "up", "down": "dn", "dn": "dn", "coin": "coin"}
BAR_CLS    = ["vol", "evt", "geo", "term", "cmd"]   # fixed order of the 5 component bars

def angle(value):
    """Needle angle on the 0-100 half-circle dial (matches the template's formula)."""
    return f"{round((float(value) / 100.0) * 180.0 - 90.0, 1):g}"

def fmt_num(score, mx):
    return f"{float(score):.1f} / {int(float(mx))}"

def grade_class(grade):
    """A/A+/B/B+/C/C+ -> colored letter; EMPTY/N-A/anything else -> muted 'x' style."""
    g = str(grade or "").strip().upper()
    return {"A": "a", "B": "b", "C": "c"}.get(g[:1], "x") if g else "x"

def build():
    d = json.load(open(DATA, encoding="utf-8"))

    # ---- pull the (static) logos straight from the locked template ----
    src = open(TEMPLATE, encoding="utf-8").read()
    def grab(pattern):
        m = re.search(pattern, src, re.DOTALL)
        return m.group(0) if m else ""
    d["logo_plate"] = grab(r'<div class="logo-plate">.*?</div>')
    d["mw_icon"]    = grab(r'<img class="brand-mw"[^>]*>')
    d["logo_foot"]  = grab(r'<div class="fbrand">.*?</div>')

    # ---- header tag from the verdict color ----
    d["tag_cls"], d["tag_label"] = TAG.get(str(d["verdict"]["color"]).upper(), TAG["YELLOW"])

    # ---- composite dial ----
    comp = d["composite"]
    comp["angle"] = angle(comp["score"])
    comp["band_class"] = BAND_CLASS.get(str(comp.get("band", "")).upper(), "mild")

    # ---- gap dial ----
    gap = d["gap"]
    gap["angle"] = angle(gap["pct"])
    gap["trigger_angle"] = angle(gap["trigger"])
    gap["band_class"] = gap.get("band_class") or ("mild" if float(gap["pct"]) < float(gap["trigger"]) else "hot")
    gap["heading"] = gap.get("heading") or "P(≥1% Overnight Gap to Next Open)"

    # ---- verdict dot ----
    d["verdict"]["dot"] = DOT.get(str(d["verdict"]["color"]).upper(), "y")

    # ---- how-built bars (compute width + label + fixed class) ----
    bars = []
    for i, b in enumerate(d["how_built"]):
        mx = float(b["max"])
        width = int(float(b["score"]) / mx * 100 + 0.5) if mx else 0
        bars.append({
            "cls":  BAR_CLS[i] if i < len(BAR_CLS) else "vol",
            "name": b["name"],
            "num":  fmt_num(b["score"], b["max"]),
            "width": width,
        })
    d["how_built"] = bars

    # ---- setups (map bias/grade/val to css classes) ----
    for r in d["setups"]:
        r["bias_cls"]   = BIAS_CLASS.get(str(r.get("bias", "")).lower(), "")
        r["bias_label"] = r.get("bias_label", "")
        r["type_label"] = r.get("type_label", "")
        r["grade_cls"]  = grade_class(r.get("grade", ""))
        r["grade_label"]= r.get("grade_label") or r.get("grade", "")
        r["val_cls"]    = VAL_CLASS.get(str(r.get("val", "")).lower(), "val-watch")
        r["val_label"]  = r.get("val_label", "")
        r["check_note"] = r.get("check_note", "")

    # ---- earnings table (map gap-risk / lean to pill classes) ----
    earnings = d.setdefault("earnings", {"intro": "", "rows": [], "outro": ""})
    for r in earnings.get("rows", []):
        r["gap_cls"]  = GAP_RISK_CLASS.get(str(r.get("gap", "")).lower(), "gap-mod")
        r["lean_cls"] = LEAN_CLASS.get(str(r.get("lean", "")).lower(), "coin")

    body = Template(open(BODY_J2, encoding="utf-8").read()).render(**d)

    # ---- stitch: locked head + rendered body + locked tail ----
    head = src[:src.index('<div id="shareable">')]

    # Update the static template title with today's date/headline
    meta = d.get("meta", {})
    stamp = meta.get("stamp", "")
    new_title = meta.get("title") or (f"Sniper Daily Dashboard · {stamp}" if stamp else "Sniper Daily Dashboard")
    head = re.sub(r'<title>.*?</title>', f'<title>{new_title}</title>', head)

    tail = src[src.index('</main>'):]
    # Keep the Save-as-PNG filename in sync with the report date
    date_iso = meta.get("date_iso", "")
    if date_iso:
        tail = re.sub(r"Sniper_Dashboard_\d{4}-\d{2}-\d{2}\.png", f"Sniper_Dashboard_{date_iso}.png", tail)

    html = head + body + "\n" + tail

    open(OUT, "w", encoding="utf-8").write(html)
    print(f"Wrote {OUT}  ({len(html):,} bytes)")

if __name__ == "__main__":
    build()
