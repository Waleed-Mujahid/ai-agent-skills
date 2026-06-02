#!/usr/bin/env python3
"""Inspect a Sophia self-review workdir and report how far the run got.

Lets the skill resume in a brand-new chat: run this first, read the checklist,
jump to the recommended phase. Infers state from the artifacts on disk (plus the
explicit `.sophia/progress.json` markers the skill writes as it passes gates).

Usage:
    python3 progress.py [--workdir DIR]      # default ~/Documents/sophia-review
"""
import json
import pathlib
import sys


def _exists_nonempty(p):
    return p.exists() and p.stat().st_size > 0


def _count_lines(p):
    try:
        return sum(1 for ln in p.read_text().splitlines() if ln.strip().startswith("|"))
    except Exception:
        return 0


def main():
    argv = sys.argv[1:]
    workdir = pathlib.Path(
        (argv[argv.index("--workdir") + 1] if "--workdir" in argv else "~/Documents/sophia-review")
    ).expanduser()
    ev = workdir / "evidence"
    ans = workdir / "answers"
    sd = workdir / ".sophia"
    progress = {}
    pj = sd / "progress.json"
    if pj.exists():
        try:
            progress = json.loads(pj.read_text())
        except Exception:
            progress = {}

    cfg = {}
    if (sd / "config.json").exists():
        try:
            cfg = json.loads((sd / "config.json").read_text())
        except Exception:
            pass

    if not workdir.exists():
        print(f"No workdir at {workdir} — this is a FRESH start. Begin at Phase 0.")
        return

    # ---- infer each milestone ----
    have_refresh = _exists_nonempty(sd / "refresh_token")
    have_ucf = bool(cfg.get("user_competency_framework_id"))
    have_uid = bool(cfg.get("sophia_user_id"))
    have_data = _exists_nonempty(workdir / "framework_details.json")
    have_delta = _exists_nonempty(ev / "00_rubric_delta.md")
    have_prev = (ans / "_prev").exists() and any((ans / "_prev").glob("*.html"))
    have_targets = _exists_nonempty(sd / "targets.json")

    harvest_files = ["a_github_edly_prs.md", "b_github_upstream_prs.md", "c_github_reviews.md",
                     "d_plane_tickets.md", "e_slack_channels.md", "f_slack_dms.md",
                     "g_claude_sessions.md", "h_cursor_sessions.md", "i_calendar_meetings.md",
                     "j_shoutouts.md"]
    harvested = [f for f in harvest_files if _exists_nonempty(ev / f)]
    have_map = _exists_nonempty(ev / "10_evidence_map.md")
    drafts = sorted(p.name for p in ans.glob("*.html")) if ans.exists() else []

    def mark(ok):
        return "✅" if ok else "⬜"

    print(f"# Sophia review progress — {workdir}\n")
    print(f"{mark(have_refresh)} Phase 0.2  auth: refresh token saved")
    print(f"{mark(have_ucf and have_uid)} Phase 0.2  ids: UCF={cfg.get('user_competency_framework_id','?')} user={cfg.get('sophia_user_id','?')}")
    print(f"{mark(have_data)} Phase 0.3  Sophia data fetched (framework_details.json …)")
    print(f"{mark(have_delta)} Phase 0.5  rubric delta built")
    print(f"{mark(have_prev)} Phase 0.5  previous answers dumped (answers/_prev/)")
    print(f"{mark(have_targets)} Gate 0     targets confirmed (.sophia/targets.json)")
    print(f"{mark(len(harvested) >= 3)} Phase 1    evidence harvested: {len(harvested)}/{len(harvest_files)} sources {harvested}")
    print(f"{mark(have_map)} Phase 2    evidence map ({_count_lines(ev/'10_evidence_map.md')} rows)")
    print(f"{mark(bool(drafts))} Phase 4    drafts written: {len(drafts)} {drafts if len(drafts)<=12 else drafts[:12]+['…']}")
    if progress:
        print(f"\nExplicit markers (.sophia/progress.json): {progress}")

    # ---- recommend next phase ----
    if not have_refresh or not (have_ucf and have_uid):
        nxt = "Phase 0.2 — finish auth + ids"
    elif not have_data:
        nxt = "Phase 0.3 — fetch Sophia data"
    elif not have_delta:
        nxt = "Phase 0.5 — build rubric delta"
    elif not have_targets:
        nxt = "Gate 0 — present the table, capture the user's target per subcat, write targets.json"
    elif len(harvested) < 3:
        nxt = "Phase 1 — parallel evidence harvest"
    elif not have_map:
        nxt = "Phase 2 — build evidence map"
    elif not drafts:
        nxt = "Phase 3/4 — differentials, then draft"
    else:
        nxt = "Phase 4/5 — continue drafting remaining subcats, then submit + verify"
    print(f"\n👉 RESUME AT: {nxt}")


if __name__ == "__main__":
    main()
