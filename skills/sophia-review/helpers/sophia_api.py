#!/usr/bin/env python3
"""Fetch the Sophia self-review data bundle for one user/framework.

Pulls the same set of JSON files we hand-collected for the reference run, but
keyed off the caller's own user_competency_framework_id + sophia_user_id (from
.sophia/config.json). Token + auto-refresh handled by sophia_auth.

Usage:
    python3 sophia_api.py [--workdir DIR]

Writes into <workdir>/ :
    framework_details.json          rubric (L1-L5) + last year's answers per subcat  [THE core file]
    progress_overview.json          draft eval state, current selections
    summary_dashboard.json          high-level dashboard, deadlines
    admin_competency_history.json   score history (best-effort; skipped on 403/404)
    person_competency_history.json  evidence history all reviewers (best-effort)

Config keys read (from .sophia/config.json):
    user_competency_framework_id    (required)
    sophia_user_id                  (required — used for admin history + auth)
    framework_name                  (optional — e.g. "Software Engineer")
"""
import json
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sophia_auth import (  # noqa: E402
    API_ROOT, get_valid_token, load_config, refresh_access, resolve_user_id,
)


def _curl_get(url, bearer):
    cmd = [
        "/usr/bin/curl", "-sS",
        "-o", "/tmp/sophia_api_resp.bin",
        "-w", "%{http_code}",
        "-X", "GET", url,
        "-H", f"Authorization: Bearer {bearer}",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    code = r.stdout.strip()
    resp = pathlib.Path("/tmp/sophia_api_resp.bin").read_bytes()
    return code, resp


def fetch(url, workdir, required=True):
    """GET url with auto-refresh on 401. Returns parsed JSON or None."""
    token = get_valid_token(workdir)
    code, resp = _curl_get(url, token)
    if code == "401":
        token = refresh_access(workdir)
        code, resp = _curl_get(url, token)
    if code != "200":
        msg = f"  HTTP {code} for {url}"
        if required:
            raise SystemExit("ERROR:" + msg + "\n  " + resp[:300].decode(errors="replace"))
        print(msg + "  (optional — skipped)")
        return None
    try:
        return json.loads(resp)
    except Exception as e:
        if required:
            raise SystemExit(f"ERROR: {url} returned non-JSON: {e}")
        print(f"  non-JSON for {url} (optional — skipped)")
        return None


def main():
    argv = sys.argv[1:]
    workdir = "."
    if "--workdir" in argv:
        workdir = argv[argv.index("--workdir") + 1]
    workdir = str(pathlib.Path(workdir).expanduser())

    cfg = load_config(workdir)
    ucf = cfg.get("user_competency_framework_id") or os.environ.get("SOPHIA_UCF_ID")
    uid = resolve_user_id(workdir)  # config/env, else decoded from refresh-token JWT
    fw = cfg.get("framework_name", "")
    if not ucf:
        raise SystemExit(
            "ERROR: user_competency_framework_id missing. Add it to "
            f"{workdir}/.sophia/config.json (open Sophia DevTools -> Network -> find a "
            "`framework/?user_competency_framework_id=XXXX` request -> copy XXXX)."
        )

    base = f"{API_ROOT}/competencies"
    fw_q = f"&framework={fw.replace(' ', '+')}" if fw else ""
    jobs = [
        ("framework_details.json",
         f"{base}/framework/?user_competency_framework_id={ucf}", True),
        ("progress_overview.json",
         f"{base}/self-review/progress/overview/?user_competency_framework_id={ucf}", True),
        ("summary_dashboard.json",
         f"{base}/self-review/summary/dashboard/?user_competency_framework_id={ucf}", True),
    ]
    if uid:
        jobs.append(("admin_competency_history.json",
                     f"{base}/admin/users/{uid}/competency-history/", False))
    jobs.append(("person_competency_history.json",
                 f"{base}/self-review/workstream/person-competency-history/"
                 f"?evidence_history_self_only=true&evidence_history_limit=200"
                 f"&latest_evaluation_only=true&definition_changes_offset=0"
                 f"&evidence_history_offset=0{fw_q}", False))

    for fname, url, required in jobs:
        print(f"GET {fname} ...")
        data = fetch(url, workdir, required=required)
        if data is not None:
            out = pathlib.Path(workdir) / fname
            out.write_text(json.dumps(data, indent=2))
            print(f"  saved {out} ({out.stat().st_size} bytes)")
    print("done.")


if __name__ == "__main__":
    main()
