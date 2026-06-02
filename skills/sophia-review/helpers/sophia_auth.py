#!/usr/bin/env python3
"""Sophia auth — bootstrap an access token from a browser refresh-token cookie.

Auth model (Sophia uses short-lived access JWTs + a long-lived refresh token):

    browser login  ->  copy `refresh-token` cookie  ->  paste into a file
                    ->  this script exchanges it for an access token
                    ->  caches the access token, decodes its `exp` clientside
                    ->  auto-refreshes when within REFRESH_SKEW seconds of expiry

Token store (per-workdir, gitignored, chmod 600):
    <workdir>/.sophia/refresh_token    the refresh-token cookie value (you paste this)
    <workdir>/.sophia/access_token     cached access JWT (this script writes it)
    <workdir>/.sophia/config.json      must contain {"sophia_user_id": <int>}

Resolution order for the refresh token:
    1. $SOPHIA_REFRESH env var
    2. <workdir>/.sophia/refresh_token
    3. ~/.sophia_refresh                 (legacy global fallback)

Resolution order for a (possibly stale) access token to seed the Bearer:
    1. $SOPHIA_TOKEN env var
    2. <workdir>/.sophia/access_token
    3. ~/.sophia_token                   (legacy global fallback)

CLI:
    python3 sophia_auth.py token [--workdir DIR]   # print a valid access token (refresh if needed)
    python3 sophia_auth.py refresh [--workdir DIR] # force a refresh, print new token
    python3 sophia_auth.py whoami [--workdir DIR]  # decode & print access token claims

Importable:
    from sophia_auth import get_valid_token
    tok = get_valid_token(workdir=".")             # returns a non-expired access token or raises

NOTE (unverified across tenants): the refresh exchange POSTs to
    {BASE}/users/<sophia_user_id>/refresh-token   body {"refresh": "<refresh_token>"}
We send the refresh token itself as the Bearer for the exchange (bootstrap case:
the only credential we hold is the refresh cookie). If your tenant rejects that,
set SOPHIA_REFRESH_BEARER to a valid access token, or see the troubleshooting block
this script prints on failure. The response is searched for the new access token
under any of: access, access_token, token, data.access.
"""
import base64
import json
import os
import pathlib
import subprocess
import sys
import time

API_ROOT = os.environ.get(
    "SOPHIA_API_ROOT", "https://api.platformsophia.com/api/v1"
)
REFRESH_SKEW = 60  # refresh if token expires within this many seconds


# --------------------------------------------------------------------------- #
# storage helpers
# --------------------------------------------------------------------------- #
def _store_dir(workdir):
    d = pathlib.Path(workdir or ".").expanduser() / ".sophia"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _read_first(*candidates):
    """Return (value, source) for the first existing/non-empty candidate.

    Each candidate is ("env", NAME) or ("file", path)."""
    for kind, ref in candidates:
        if kind == "env":
            v = os.environ.get(ref)
            if v and v.strip():
                return v.strip(), f"env:{ref}"
        else:
            p = pathlib.Path(ref).expanduser()
            if p.exists():
                v = p.read_text().strip()
                if v:
                    return v, f"file:{p}"
    return None, None


def load_config(workdir):
    p = _store_dir(workdir) / "config.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return {}
    return {}


def get_refresh_token(workdir):
    tok, src = _read_first(
        ("env", "SOPHIA_REFRESH"),
        ("file", _store_dir(workdir) / "refresh_token"),
        ("file", pathlib.Path.home() / ".sophia_refresh"),
    )
    return tok, src


def get_cached_access(workdir):
    tok, src = _read_first(
        ("env", "SOPHIA_TOKEN"),
        ("file", _store_dir(workdir) / "access_token"),
        ("file", pathlib.Path.home() / ".sophia_token"),
    )
    return tok, src


def save_access(workdir, token):
    p = _store_dir(workdir) / "access_token"
    p.write_text(token.strip())
    try:
        p.chmod(0o600)
    except Exception:
        pass
    return p


# --------------------------------------------------------------------------- #
# JWT inspection (no signature verification — clientside expiry check only)
# --------------------------------------------------------------------------- #
def decode_jwt(token):
    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        return json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception:
        return {}


def seconds_left(token):
    exp = decode_jwt(token).get("exp")
    if not exp:
        return None  # unknown — treat as needs-refresh by caller
    return int(exp) - int(time.time())


def is_fresh(token):
    left = seconds_left(token)
    if left is None:
        return False
    return left > REFRESH_SKEW


# --------------------------------------------------------------------------- #
# network (curl — no third-party deps)
# --------------------------------------------------------------------------- #
def _curl(method, url, bearer=None, body=None):
    cmd = [
        "/usr/bin/curl", "-sS",
        "-o", "/tmp/sophia_auth_resp.bin",
        "-w", "%{http_code}",
        "-X", method, url,
    ]
    if bearer:
        cmd += ["-H", f"Authorization: Bearer {bearer}"]
    if body is not None:
        cmd += ["-H", "Content-Type: application/json", "--data-binary", "@-"]
        r = subprocess.run(cmd, input=body, capture_output=True, check=False)
    else:
        r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    code = (r.stdout if isinstance(r.stdout, str) else r.stdout.decode()).strip()
    resp = pathlib.Path("/tmp/sophia_auth_resp.bin").read_bytes()
    return code, resp


def _find_access(obj):
    """Recursively pull an access-token-looking string from a JSON response."""
    if isinstance(obj, dict):
        for key in ("access", "access_token", "token", "accessToken"):
            v = obj.get(key)
            if isinstance(v, str) and v.count(".") == 2:
                return v
        for v in obj.values():
            hit = _find_access(v)
            if hit:
                return hit
    elif isinstance(obj, list):
        for v in obj:
            hit = _find_access(v)
            if hit:
                return hit
    return None


def extract_user_id(token):
    """Pull a user id out of a JWT's claims (works on the refresh token itself)."""
    claims = decode_jwt(token)
    for key in ("user_id", "userId", "uid", "user", "sub", "id"):
        v = claims.get(key)
        if isinstance(v, (int, str)) and str(v).isdigit():
            return int(v)
    return None


def resolve_user_id(workdir, refresh_token=None):
    """sophia_user_id from config/env, else decoded from the refresh-token JWT."""
    cfg = load_config(workdir)
    uid = cfg.get("sophia_user_id") or os.environ.get("SOPHIA_USER_ID")
    if uid:
        return int(uid)
    if refresh_token is None:
        refresh_token, _ = get_refresh_token(workdir)
    if refresh_token:
        return extract_user_id(refresh_token)
    return None


def refresh_access(workdir):
    """Exchange the refresh token for a new access token. Saves and returns it."""
    refresh, src = get_refresh_token(workdir)
    if not refresh:
        raise SystemExit(_repaste_help(workdir))
    user_id = resolve_user_id(workdir, refresh)
    if not user_id:
        raise SystemExit(
            "ERROR: sophia_user_id unknown and not decodable from the refresh token. "
            f"Put it in {_store_dir(workdir)/'config.json'} as "
            "{\"sophia_user_id\": <int>} or set $SOPHIA_USER_ID."
        )

    url = f"{API_ROOT}/users/{user_id}/refresh-token"
    body = json.dumps({"refresh": refresh}).encode()
    # Bootstrap: the only credential we hold is the refresh token, so try it as Bearer.
    bearer = os.environ.get("SOPHIA_REFRESH_BEARER") or refresh
    code, resp = _curl("POST", url, bearer=bearer, body=body)
    if code not in ("200", "201"):
        raise SystemExit(
            f"ERROR: refresh exchange returned HTTP {code} from {url}\n"
            f"  response: {resp[:400].decode(errors='replace')}\n"
            + _repaste_help(workdir)
        )
    try:
        data = json.loads(resp)
    except Exception:
        raise SystemExit(f"ERROR: refresh response not JSON: {resp[:300]!r}")
    access = _find_access(data)
    if not access:
        raise SystemExit(
            "ERROR: could not locate an access token in the refresh response. "
            f"keys seen: {list(data.keys()) if isinstance(data, dict) else type(data)}\n"
            "Inspect the real response shape and update _find_access() keys."
        )
    save_access(workdir, access)
    return access


def get_valid_token(workdir="."):
    """Return a non-expired access token, refreshing if needed."""
    cached, _ = get_cached_access(workdir)
    if cached and is_fresh(cached):
        return cached
    return refresh_access(workdir)


def _repaste_help(workdir):
    store = _store_dir(workdir)
    return (
        "\n--- Sophia re-auth needed ---\n"
        "1. Open Sophia in your browser and log in.\n"
        "2. DevTools (F12) -> Application -> Cookies -> https://*.platformsophia.com\n"
        "3. Copy the value of the `refresh-token` cookie.\n"
        f"4. Paste it into: {store/'refresh_token'}\n"
        f"   e.g.  pbpaste > {store/'refresh_token'} && chmod 600 {store/'refresh_token'}\n"
        "   (or export SOPHIA_REFRESH=... in this shell)\n"
        "5. Re-run the command.\n"
    )


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _parse_workdir(argv):
    workdir = "."
    if "--workdir" in argv:
        i = argv.index("--workdir")
        workdir = argv[i + 1]
    return workdir


def main():
    argv = sys.argv[1:]
    cmd = argv[0] if argv else "token"
    workdir = _parse_workdir(argv)
    if cmd == "token":
        print(get_valid_token(workdir))
    elif cmd == "refresh":
        print(refresh_access(workdir))
    elif cmd == "whoami":
        tok, src = get_cached_access(workdir)
        if not tok:
            raise SystemExit("no cached access token")
        claims = decode_jwt(tok)
        left = seconds_left(tok)
        print(json.dumps({"source": src, "seconds_left": left, "claims": claims}, indent=2))
    elif cmd == "userid":
        # Auto-discover the Sophia user id (decoded from the refresh-token JWT).
        uid = resolve_user_id(workdir)
        if not uid:
            raise SystemExit("could not resolve user id — paste the refresh-token cookie first")
        print(uid)
    else:
        raise SystemExit(f"unknown command: {cmd} (use token|refresh|whoami|userid)")


if __name__ == "__main__":
    main()
