#!/usr/bin/env python3
"""Phase 1.5 coverage audit — month histogram per evidence file.

Flags months inside the cycle window with < MIN_ATOMS dated atoms, so a harvest
agent that stopped paginating early (skewing to recent months) gets caught
before the evidence map is built.

Usage:
    python3 coverage_audit.py <evidence_dir> [--cycle-start YYYY-MM-DD] [--cycle-end YYYY-MM-DD] [--min N]
"""
import re
import sys
from collections import Counter
from pathlib import Path

MIN_ATOMS = 3
# Sparse by nature — flagged but NOT treated as a harvest bug. These sources are
# legitimately thin: shoutouts are occasional, upstream PRs are rare, calendar is
# harvested as headline events only (the skill explicitly avoids precise-cadence
# claims), and code reviews cluster rather than spread evenly month-to-month.
SPARSE_OK = {"j_shoutouts.md", "b_github_upstream_prs.md",
             "i_calendar_meetings.md", "c_github_reviews.md"}


def months_between(start, end):
    sy, sm = int(start[:4]), int(start[5:7])
    ey, em = int(end[:4]), int(end[5:7])
    out = []
    y, m = sy, sm
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return out


def main():
    argv = sys.argv[1:]
    if not argv:
        sys.exit("Usage: coverage_audit.py <evidence_dir> [--cycle-start D] [--cycle-end D] [--min N]")
    evdir = Path(argv[0]).expanduser()
    cstart = argv[argv.index("--cycle-start") + 1] if "--cycle-start" in argv else None
    cend = argv[argv.index("--cycle-end") + 1] if "--cycle-end" in argv else None
    min_atoms = int(argv[argv.index("--min") + 1]) if "--min" in argv else MIN_ATOMS
    window = set(months_between(cstart, cend)) if (cstart and cend) else None

    problems = 0
    for path in sorted(evdir.glob("*.md")):
        text = path.read_text()
        dates = re.findall(r"\b(\d{4}-\d{2})-\d{2}\b", text)
        counts = Counter(dates)
        if window:
            sparse = sorted(m for m in window if counts.get(m, 0) < min_atoms)
        else:
            sparse = sorted(m for m, c in counts.items() if c < min_atoms)
        tag = "(sparse-ok)" if path.name in SPARSE_OK else ""
        if sparse and not tag:
            problems += 1
            print(f"[SPARSE] {path.name}: months < {min_atoms} atoms: {sparse}")
        elif sparse:
            print(f"[sparse-ok] {path.name}: {sparse}")
        else:
            print(f"[OK] {path.name}: {dict(sorted(counts.items()))}")
    print(f"\n{problems} file(s) need re-pagination." if problems else "\nCoverage OK.")


if __name__ == "__main__":
    main()
