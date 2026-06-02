#!/usr/bin/env python3
"""Submit a Sophia self-review answer for one category and verify persistence.

Usage:
    python3 submit_answer.py <category_id> <html_file> [--workdir DIR]

Example:
    python3 submit_answer.py 1177 answers/1177_project_delivery.html --workdir ~/Documents/sophia_2026

user_competency_framework_id is read from <workdir>/.sophia/config.json.
Token + auto-refresh on 401 handled by sophia_auth (refresh-token bootstrap).

Verified working payload (do NOT change without re-verifying):
    POST {BASE}/competencies/self-review/self-evaluations/?approach=comments-only
    {"user_competency_framework_id": N, "responses": [{"category_id": M, "assessment_comments": HTML}]}
Wrong shapes that 201 but silently drop:  {"subcategory_id": ...}  |  flat {"category_id": ...}

Exit codes:  0 = submitted AND verified stored length > 0   |   1 = anything else
"""
import json
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sophia_auth import API_ROOT, get_valid_token, load_config, refresh_access  # noqa: E402

BASE = f"{API_ROOT}/competencies"
POST_URL = f"{BASE}/self-review/self-evaluations/?approach=comments-only"


def die(msg, code=1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def strip_html_comments(html):
    return re.sub(r"<!--.*?-->\s*", "", html, flags=re.S).strip()


def curl(method, url, token, body=None):
    cmd = [
        "/usr/bin/curl", "-sS", "-o", "/tmp/sophia_resp.bin", "-w", "%{http_code}",
        "-X", method, url, "-H", f"Authorization: Bearer {token}",
    ]
    if body is not None:
        cmd += ["-H", "Content-Type: application/json", "--data-binary", "@-"]
        r = subprocess.run(cmd, input=body, capture_output=True, check=False)
    else:
        r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    code = (r.stdout if isinstance(r.stdout, str) else r.stdout.decode()).strip()
    return code, pathlib.Path("/tmp/sophia_resp.bin").read_bytes()


def curl_auto(method, url, workdir, body=None):
    """curl with one auto-refresh retry on 401."""
    token = get_valid_token(workdir)
    code, resp = curl(method, url, token, body)
    if code == "401":
        token = refresh_access(workdir)
        code, resp = curl(method, url, token, body)
    return code, resp


def find_category(cats, target_id):
    for c in cats:
        if c.get("id") == target_id:
            return c
        hit = find_category(c.get("subcategories") or [], target_id)
        if hit:
            return hit
    return None


def main():
    argv = sys.argv[1:]
    workdir = "."
    if "--workdir" in argv:
        i = argv.index("--workdir")
        workdir = argv[i + 1]
        del argv[i:i + 2]
    workdir = str(pathlib.Path(workdir).expanduser())

    if len(argv) != 2:
        die("Usage: submit_answer.py <category_id> <html_file> [--workdir DIR]")
    try:
        category_id = int(argv[0])
    except ValueError:
        die("category_id must be an integer")
    html_path = pathlib.Path(argv[1]).expanduser()
    if not html_path.exists():
        die(f"HTML file not found: {html_path}")

    cfg = load_config(workdir)
    ucf = cfg.get("user_competency_framework_id")
    if not ucf:
        die(f"user_competency_framework_id missing in {workdir}/.sophia/config.json")
    get_url = f"{BASE}/framework/?user_competency_framework_id={ucf}"

    html = strip_html_comments(html_path.read_text())
    if not html:
        die("HTML body is empty after stripping comments")

    payload = json.dumps({
        "user_competency_framework_id": ucf,
        "responses": [{"category_id": category_id, "assessment_comments": html}],
    }).encode()

    print(f"POST category_id={category_id} ucf={ucf} (html len={len(html)})")
    code, resp = curl_auto("POST", POST_URL, workdir, body=payload)
    print(f"  HTTP {code}")
    if code not in ("200", "201"):
        print("  response:", resp[:600].decode(errors="replace"))
        die("submit failed")

    print("Verifying persistence via GET framework...")
    code, resp = curl_auto("GET", get_url, workdir)
    if code != "200":
        die(f"verify GET returned HTTP {code}")
    try:
        data = json.loads(resp)
    except Exception as e:
        die(f"verify response not JSON: {e}")
    cat = find_category(data.get("categories", []), category_id)
    if not cat:
        die(f"category_id={category_id} not found in framework")
    stored = (cat.get("previous_selection") or {}).get("assessment_comments") or ""
    if not stored:
        die(f"stored assessment_comments empty for {category_id} (submission silently dropped)")
    if stored.strip() != html.strip() and len(stored) < int(len(html) * 0.9):
        die(f"stored len {len(stored)} much smaller than submitted len {len(html)}")
    print(f"  OK: {category_id} stored, len={len(stored)}")
    sys.exit(0)


if __name__ == "__main__":
    main()
