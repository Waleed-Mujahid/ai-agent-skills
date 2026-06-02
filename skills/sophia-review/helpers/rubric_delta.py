#!/usr/bin/env python3
"""Build the rubric delta from framework_details.json (+ optional history).

For every leaf subcategory: current level, the next level up (target), the verbatim
L_current vs L_target rubric text, the parent category + its weight, and whether a
previous answer exists. Drives Phase 0 (where you stand) and the differential
questions.

Real framework_details.json shape (verified 2026-06-02):
    categories[]                          root categories (weightage = headline %)
      .title, .weightage
      .subcategories[]                    leaf subcats (is_leaf=True)
        .id, .title, .weightage           subcat weight is % WITHIN its category
        .content_format.format_content.options[]   {rank:"1".."5", label, description}
        .previous_selection.assessment_comments    last year's HTML answer
        .previous_selection.selected_option_rank   usually null in a draft cycle

The selected level is NOT in the framework during a draft cycle — it comes from the
self-rating history file's evidence_history.results[] (criteria = subcat title,
competency = category, competency_choice_value = level int, latest by created_at).

Usage:
    python3 rubric_delta.py <framework_details.json> \
        [--history <self_competency_history.json>] \
        [--out DELTA.md] [--json DELTA.json]
"""
import json
import re
import sys


def strip_tags(html):
    return re.sub(r"<[^>]+>", "", html or "").strip()


def load_levels_from_history(path):
    """Map subcat title -> latest self-rated level (int) from evidence history."""
    try:
        h = json.load(open(path))
    except Exception:
        return {}
    results = (h.get("evidence_history") or {}).get("results") or []
    latest = {}  # title -> (created_at, level)
    for r in results:
        crit = r.get("criteria")
        val = r.get("competency_choice_value")
        if not crit or val in (None, ""):
            continue
        try:
            lvl = int(val)
        except (TypeError, ValueError):
            continue
        ts = r.get("created_at") or ""
        if crit not in latest or ts > latest[crit][0]:
            latest[crit] = (ts, lvl)
    return {k: v[1] for k, v in latest.items()}


def iter_leaves(cat, root_title, root_weight):
    """Yield leaf subcategories under a root category, attributing root weight."""
    subs = cat.get("subcategories") or []
    if not subs and cat.get("is_leaf"):
        yield cat, root_title, root_weight
        return
    for s in subs:
        if s.get("is_leaf") or not (s.get("subcategories")):
            yield s, root_title, root_weight
        else:
            yield from iter_leaves(s, root_title, root_weight)


def parse(framework_path, history_path=None):
    data = json.load(open(framework_path))
    hist_levels = load_levels_from_history(history_path) if history_path else {}
    rows = []
    for cat in data.get("categories", []):
        root_title = cat.get("title")
        root_weight = cat.get("weightage", 0)
        for sub, c_title, c_weight in iter_leaves(cat, root_title, root_weight):
            opts = ((sub.get("content_format") or {})
                    .get("format_content", {}) or {}).get("options", []) or []
            by_rank = {}
            for o in opts:
                try:
                    by_rank[int(o.get("rank"))] = o.get("description", "")
                except (TypeError, ValueError):
                    pass
            prev = sub.get("previous_selection") or {}
            title = sub.get("title")
            current = prev.get("selected_option_rank") or prev.get("value")
            if current in (None, ""):
                current = hist_levels.get(title)  # fall back to self-rating history
            current = int(current) if current not in (None, "") else None
            # Sophia uses an out-of-range sentinel (e.g. 10000) for "not applicable /
            # not rated" — treat anything outside 1..5 as unknown (set a baseline).
            if current is not None and not (1 <= current <= 5):
                current = None
            last_answer = strip_tags(prev.get("assessment_comments"))
            known = current is not None
            target = (current + 1) if (known and current < 5) else (1 if not known else 5)
            tier, action = target_policy(current, not last_answer)
            rows.append({
                "id": sub.get("id"),
                "name": title,
                "category": c_title,
                "weight": c_weight,
                "subcat_weight": sub.get("weightage", 0),
                "current": current,
                "current_str": f"L{current}" if known else "?",
                "target": target,
                "hold": known and current >= 5,
                "must_fill": not last_answer,
                "tier": tier,            # raise | stretch | fill | baseline | hold
                "action": action,        # human-readable default proposal
                "L_current_desc": by_rank.get(current, "N/A") if known else "unknown",
                "L_target_desc": by_rank.get(target, "N/A"),
                "last_answer": last_answer[:600],
            })
    rows.sort(key=lambda r: (-r["weight"], r["category"] or "", -r["subcat_weight"]))
    return rows


def target_policy(current, must_fill):
    """Realistic default per subcat. L4 is hard (recognition beyond the team), so L3
    defaults to HOLD with an opt-in stretch; raises are reserved for where there's margin.
    Returns (tier, action_label)."""
    if current is None:
        if must_fill:
            return "fill", "fill from scratch (aim L2–L3)"
        return "baseline", "set a baseline (aim ~L2)"
    if current <= 2:
        return "raise", f"raise L{current} → L{current + 1}"        # good margin
    if current == 3:
        return "stretch", "hold L3 — L4 is a stretch (only with strong evidence)"
    return "hold", f"hold L{current}"                              # L4/L5: hold


PROPOSED = {  # short label for the Proposed column
    "raise": lambda r: f"L{r['target']}",
    "stretch": lambda r: "L3 (·L4?)",
    "fill": lambda r: "~L2",
    "baseline": lambda r: "~L2",
    "hold": lambda r: r["current_str"],
}


def to_markdown(rows):
    out = ["# Rubric Delta — Where You Stand\n",
           "**Action** is the realistic default, not a blanket +1. Raise where there's "
           "margin (≤L2 → next: L3 is usually \"owns modules / go-to person in team\"). "
           "L3→L4 is a **stretch** — held by default, attempted only where the evidence map "
           "earns it. Confirm or change at Gate 0; stretches are re-confirmed after Phase 2.\n",
           "| Category | Subcategory | Cat % | Now | Proposed | Action | Prev answer? |",
           "|----------|-------------|------:|:---:|:--------:|--------|--------------|"]
    for r in rows:
        proposed = PROPOSED[r["tier"]](r)
        prev = "❌ none (must fill)" if r["must_fill"] else "✅ yes"
        out.append(
            f"| {r['category']} | **{r['name']}** | {r['weight']} | "
            f"{r['current_str']} | {proposed} | {r['action']} | {prev} |"
        )
    # group counts so the user sees the shape at a glance
    from collections import Counter
    c = Counter(r["tier"] for r in rows)
    out.append(
        f"\n**Default plan:** {c.get('raise',0)} raises (good margin), "
        f"{c.get('stretch',0)} L3→L4 stretches (evidence-gated), "
        f"{c.get('fill',0)} fill-from-scratch, {c.get('baseline',0)} baseline, "
        f"{c.get('hold',0)} hold.\n"
        "> Refer to subcategories by name — IDs live in `.sophia/delta.json` for tooling only.\n")
    out.append("\n---\n\n## Targets — rubric gap per subcategory (holds omitted)\n")
    for r in rows:
        if r["tier"] == "hold":
            continue
        tag = {"raise": "", "stretch": "  ⟵ STRETCH (L4 hard)", "fill": "  ⟵ MUST-FILL",
               "baseline": "  ⟵ baseline"}[r["tier"]]
        out.append(f"### {r['name']}  ·  {r['category']} ({r['weight']}% of score){tag}\n")
        out.append(f"- **Now ({r['current_str']}):** {r['L_current_desc']}")
        out.append(f"- **Next (L{r['target']}):** {r['L_target_desc']}")
        if r["must_fill"]:
            out.append("- ⚠ **No previous answer — write from scratch.**")
        elif r["last_answer"]:
            out.append(f"- *Last year (excerpt):* {r['last_answer']}")
        out.append("")
    return "\n".join(out)


def main():
    argv = sys.argv[1:]
    if not argv:
        sys.exit("Usage: rubric_delta.py <framework.json> [--history H.json] [--out F.md] [--json F.json]")
    fw = argv[0]
    hist = argv[argv.index("--history") + 1] if "--history" in argv else None
    out_md = argv[argv.index("--out") + 1] if "--out" in argv else None
    out_json = argv[argv.index("--json") + 1] if "--json" in argv else None
    rows = parse(fw, hist)
    md = to_markdown(rows)
    if out_md:
        open(out_md, "w").write(md)
        print(f"wrote {out_md} ({len(rows)} subcats, "
              f"{sum(1 for r in rows if r['current'] is None)} with unknown level)")
    else:
        print(md)
    if out_json:
        json.dump(rows, open(out_json, "w"), indent=2)
        print(f"wrote {out_json}")


if __name__ == "__main__":
    main()
