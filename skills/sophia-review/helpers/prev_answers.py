#!/usr/bin/env python3
"""Dump each subcategory's FULL previous-cycle answer to its own HTML file.

The rubric delta only carries a 600-char stripped snippet of last year's answer
(for readability). When drafting, the model should see the complete prior text so
it can improve on it — and "hold" subcategories need the full answer to carry
forward (re-submit) so they don't blank out. This writes the full HTML per subcat.

Usage:
    python3 prev_answers.py <framework_details.json> --out <dir>

Writes <dir>/<id>_<slug>.html for every leaf subcat that has a previous answer.
Slug matches the skill convention: lowercase name, non-alnum runs -> "_".
Prints a table:  id | subcategory | has_prev | chars
"""
import json
import pathlib
import re
import sys


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "_", (name or "").lower()).strip("_")


def iter_leaves(cat):
    subs = cat.get("subcategories") or []
    if not subs and cat.get("is_leaf"):
        yield cat
        return
    for s in subs:
        if s.get("is_leaf") or not s.get("subcategories"):
            yield s
        else:
            yield from iter_leaves(s)


def main():
    argv = sys.argv[1:]
    if not argv or "--out" not in argv:
        sys.exit("Usage: prev_answers.py <framework_details.json> --out <dir>")
    fw = argv[0]
    outdir = pathlib.Path(argv[argv.index("--out") + 1]).expanduser()
    outdir.mkdir(parents=True, exist_ok=True)

    data = json.load(open(fw))
    rows = []
    for cat in data.get("categories", []):
        for sub in iter_leaves(cat):
            sid = sub.get("id")
            name = sub.get("title")
            html = (sub.get("previous_selection") or {}).get("assessment_comments") or ""
            has_prev = bool(html.strip())
            if has_prev:
                path = outdir / f"{sid}_{slugify(name)}.html"
                path.write_text(html)
            rows.append((sid, name, has_prev, len(html)))

    print(f"{'id':>6} | {'subcategory':40} | prev | chars")
    print("-" * 70)
    for sid, name, has_prev, n in rows:
        print(f"{sid:>6} | {(name or '')[:40]:40} | {'yes ' if has_prev else 'NO  '} | {n}")
    dumped = sum(1 for r in rows if r[2])
    print(f"\nwrote {dumped} prior answers to {outdir} "
          f"({len(rows) - dumped} subcats have NO previous answer — MUST-FILL)")


if __name__ == "__main__":
    main()
