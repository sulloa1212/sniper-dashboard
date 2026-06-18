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
BIAS_CLASS = {"bull": "bull", "bear": "bear"}
GRADE_CLASS= {"A": "gA", "B": "gB", "C": "gC"}
VAL_CLASS  = {"pending": "val-pending", "watch": "val-watch", "invalid": "val-invalid", "ineligible": "val-invalid"}
BAR_CLS    = ["vol", "evt", "geo", "term", "cmd"]   # fixed order of the 5 component bars

def angle(value):
    """Needle angle on the 0-100 half-circle dial (matches the template's formula)."""
    return round((float(value) / 100.0) * 180.0 - 90.0, 1)

def fmt_num(score, mx):
    s = f"{float(score):g}"
    return f"{s} / {mx}"

def build():
    d = json.load(open(DATA, encoding="utf-8"))

    # ---- pull the (static) logos straight from the locked template ----
    src = open(TEMPLATE, encoding="utf-8").read()
    def grab(pattern):
        m = re.search(pattern, src, re.DOTALL)
        return m.group(0) if m else ""
    d["logo_plate"] = grab(r'<div class="logo-plate">.*?</div>')
    d["mw_icon"]    = grab(r'<img class="mw-icon"[^>]*>')
    d["logo_foot"]  = grab(r'<div class="fbrand">.*?</div>')

    # ---- composite dial ----
    comp = d["composite"]
    comp["angle"] = angle(comp["score"])
    comp["band_class"] = BAND_CLASS.get(str(comp.get("band", "")).upper(), "mild")

    # ---- gap dial ----
    gap = d["gap"]
    gap["angle"] = angle(gap["pct"])
    gap["trigger_angle"] = angle(gap["trigger"])
    gap["band_class"] = gap.get("band_class") or ("mild" if float(gap["pct"]) < float(gap["trigger"]) else "hot")

    # ---- verdict dot ----
    d["verdict"]["dot"] = DOT.get(str(d["verdict"]["color"]).upper(), "y")

    # ---- how-built bars (compute width + label + fixed class) ----
    bars = []
    for i, b in enumerate(d["how_built"]):
        mx = float(b["max"])
        width = round(float(b["score"]) / mx * 100) if mx else 0
        bars.append({
            "cls":  BAR_CLS[i] if i < len(BAR_CLS) else "vol",
            "name": b["name"],
            "num":  fmt_num(b["score"], b["max"]),
            "width": width,
        })
    d["how_built"] = bars

    # ---- setups (map bias/grade/val to css classes) ----
    for r in d["setups"]:
        r["bias_cls"]  = BIAS_CLASS.get(str(r.get("bias", "")).lower(), "")
        r["bias_label"]= r.get("bias_label", "")
        r["type_label"]= r.get("type_label", "")
        r["grade_cls"] = GRADE_CLASS.get(str(r.get("grade", "")).upper(), "")
        r["grade_label"]= r.get("grade_label", "")
        r["val_cls"]   = VAL_CLASS.get(str(r.get("val", "")).lower(), "val-watch")
        r["val_label"] = r.get("val_label", "")

    body = Template(open(BODY_J2, encoding="utf-8").read()).render(**d)

    # ---- stitch: locked head + rendered body + locked tail ----
    src = open(TEMPLATE, encoding="utf-8").read()
    head = src[:src.index('<div id="shareable">')]
    tail = src[src.index('</main>'):]
    html = head + body + "\n" + tail

    open(OUT, "w", encoding="utf-8").write(html)
    print(f"Wrote {OUT}  ({len(html):,} bytes)")

if __name__ == "__main__":
    build()
