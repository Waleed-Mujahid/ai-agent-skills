#!/usr/bin/env python3
"""
harvest_cursor.py — Extract Cursor IDE composer/chat sessions from workspace SQLite DBs.

Usage:
    python3 harvest_cursor.py [base_path] [output_jsonl]

Defaults:
    base_path    = ~/Library/Application Support/Cursor/User
    output_jsonl = /tmp/cursor_sessions.jsonl

Generic: parameterize base_path for any user's Cursor installation.
"""

import sqlite3
import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime, timezone

CYCLE_START_MS = 1750896000000  # 2025-06-26 00:00:00 UTC
CYCLE_END_MS   = 1748217599000  # 2026-05-25 23:59:59 UTC

# Fix: 2026-05-25 epoch
# 2026-05-25 23:59:59 UTC = 1779148799
CYCLE_END_MS   = 1779148799000


def get_db_mtime_ms(db_path: Path) -> int:
    try:
        return int(db_path.stat().st_mtime * 1000)
    except Exception:
        return 0


def read_workspace_folder(ws_dir: Path) -> str:
    """Read workspace.json → folder path → derive project name."""
    ws_json = ws_dir / "workspace.json"
    if not ws_json.exists():
        return ws_dir.name
    try:
        data = json.loads(ws_json.read_text(encoding="utf-8"))
        folder = data.get("folder", "")
        if folder.startswith("file://"):
            folder = folder[7:]
        return Path(folder).name if folder else ws_dir.name
    except Exception:
        return ws_dir.name


def read_workspace_full_path(ws_dir: Path) -> str:
    """Read workspace.json → full folder path."""
    ws_json = ws_dir / "workspace.json"
    if not ws_json.exists():
        return ""
    try:
        data = json.loads(ws_json.read_text(encoding="utf-8"))
        folder = data.get("folder", "")
        if folder.startswith("file://"):
            folder = folder[7:]
        return folder
    except Exception:
        return ""


def strip_html(text: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def query_db(db_path: Path, project_name: str, full_path: str) -> list:
    """Query a single state.vscdb and return composer session dicts."""
    sessions = []
    try:
        uri = db_path.as_uri() + "?mode=ro&immutable=1"
        con = sqlite3.connect(uri, uri=True, timeout=5)
        cur = con.cursor()

        # Check tables
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cur.fetchall()}

        if "ItemTable" not in tables:
            con.close()
            return sessions

        # Probe cursorDiskKV first 5 keys for schema discovery
        cursorDiskKV_keys = []
        if "cursorDiskKV" in tables:
            cur.execute("SELECT key FROM cursorDiskKV LIMIT 5")
            cursorDiskKV_keys = [r[0] for r in cur.fetchall()]

        # Fetch relevant ItemTable rows
        cur.execute(
            "SELECT key, value FROM ItemTable WHERE "
            "key='composer.composerData' OR "
            "key='aiService.generations' OR "
            "key='aiService.prompts'"
        )
        rows = {r[0]: r[1] for r in cur.fetchall()}
        con.close()

        if "composer.composerData" not in rows:
            return sessions

        db_mtime_ms = get_db_mtime_ms(db_path)

        # Parse composer metadata
        try:
            raw = rows["composer.composerData"]
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="replace")
            composer_data = json.loads(raw)
        except Exception:
            return sessions

        # Parse generations (timestamped prompts)
        generations = []
        if "aiService.generations" in rows:
            try:
                raw_g = rows["aiService.generations"]
                if isinstance(raw_g, bytes):
                    raw_g = raw_g.decode("utf-8", errors="replace")
                generations = json.loads(raw_g)
            except Exception:
                pass

        # Parse prompts list (just text)
        prompts_list = []
        if "aiService.prompts" in rows:
            try:
                raw_p = rows["aiService.prompts"]
                if isinstance(raw_p, bytes):
                    raw_p = raw_p.decode("utf-8", errors="replace")
                prompts_list = json.loads(raw_p)
            except Exception:
                pass

        # Derive earliest/latest timestamp from generations
        gen_timestamps = sorted([g.get("unixMs", 0) for g in generations if g.get("unixMs")])
        gen_prompts = [
            strip_html(g.get("textDescription", ""))[:200]
            for g in generations
            if g.get("textDescription")
        ]

        composers = composer_data.get("allComposers", [])
        for i, c in enumerate(composers):
            created_at_ms = c.get("createdAt") or c.get("lastUpdatedAt") or db_mtime_ms
            updated_at_ms = c.get("lastUpdatedAt") or created_at_ms

            # If no createdAt in composer, use first generation timestamp
            if created_at_ms == db_mtime_ms and gen_timestamps:
                created_at_ms = gen_timestamps[0]

            files_changed = c.get("filesChangedCount", 0)
            lines_added = c.get("totalLinesAdded", 0)
            lines_removed = c.get("totalLinesRemoved", 0)

            # Message count: use generations count for first composer; divide for multi
            if len(composers) == 1:
                msg_count = max(len(generations), len(prompts_list), 1)
            else:
                # Split evenly (approximation)
                msg_count = max(1, len(generations) // len(composers))

            name = c.get("name", "")
            subtitle = c.get("subtitle", "")

            # First user prompt: prefer actual generation text, then name/subtitle
            first_prompt = ""
            last_prompt = ""
            if gen_prompts and i == 0:
                first_prompt = gen_prompts[0]
                last_prompt = gen_prompts[-1] if len(gen_prompts) > 1 else gen_prompts[0]
            elif prompts_list and i == 0:
                first_text = prompts_list[0].get("text", "") if isinstance(prompts_list[0], dict) else str(prompts_list[0])
                first_prompt = strip_html(first_text)[:200]
                last_text = prompts_list[-1].get("text", "") if isinstance(prompts_list[-1], dict) else str(prompts_list[-1])
                last_prompt = strip_html(last_text)[:200]
            else:
                first_prompt = (name or subtitle or "")[:200]
                last_prompt = first_prompt

            session = {
                "sessionId": c.get("composerId", ""),
                "projectName": project_name,
                "projectPath": full_path,
                "dbPath": str(db_path),
                "createdAt_ms": created_at_ms,
                "updatedAt_ms": updated_at_ms,
                "createdAt_iso": datetime.fromtimestamp(
                    created_at_ms / 1000, tz=timezone.utc
                ).strftime("%Y-%m-%d") if created_at_ms > 0 else "",
                "messageCount": msg_count,
                "firstUserPrompt": first_prompt,
                "lastUserPrompt": last_prompt,
                "sessionName": name,
                "subtitle": subtitle,
                "unifiedMode": c.get("unifiedMode", ""),
                "filesChanged": files_changed,
                "linesAdded": lines_added,
                "linesRemoved": lines_removed,
                "isArchived": c.get("isArchived", False),
                "cursorDiskKV_sample_keys": cursorDiskKV_keys,
            }
            sessions.append(session)

    except sqlite3.OperationalError as e:
        msg = str(e)
        if "locked" in msg or "unable to open" in msg or "readonly" in msg:
            print(f"[SKIP locked] {db_path}: {e}", file=sys.stderr)
        else:
            print(f"[ERROR sqlite] {db_path}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"[ERROR] {db_path}: {type(e).__name__}: {e}", file=sys.stderr)

    return sessions


def harvest(base_path: Path, output_path: Path):
    ws_storage = base_path / "workspaceStorage"
    all_sessions = []
    dbs_scanned = 0
    dbs_with_data = 0
    locked_count = 0

    print(f"Scanning: {ws_storage}", file=sys.stderr)
    if not ws_storage.exists():
        print(f"ERROR: {ws_storage} does not exist", file=sys.stderr)
        sys.exit(1)

    for ws_dir in sorted(ws_storage.iterdir()):
        if not ws_dir.is_dir():
            continue
        db_path = ws_dir / "state.vscdb"
        if not db_path.exists():
            continue

        dbs_scanned += 1
        project_name = read_workspace_folder(ws_dir)
        full_path = read_workspace_full_path(ws_dir)

        prev_count = len(all_sessions)
        sessions = query_db(db_path, project_name, full_path)
        if sessions:
            dbs_with_data += 1
            all_sessions.extend(sessions)

    # Also scan global DB
    global_db = base_path / "globalStorage" / "state.vscdb"
    if global_db.exists():
        dbs_scanned += 1
        sessions = query_db(global_db, "_global", "")
        if sessions:
            dbs_with_data += 1
            all_sessions.extend(sessions)

    print(
        f"Scanned {dbs_scanned} DBs, {dbs_with_data} had chat data, "
        f"{len(all_sessions)} raw sessions",
        file=sys.stderr,
    )

    # Filter to cycle window — use DB mtime as fallback when timestamp missing/zero
    in_cycle = []
    out_cycle = []
    for s in all_sessions:
        ts = s["createdAt_ms"]
        if ts == 0:
            # Use DB mtime
            db_path = Path(s["dbPath"])
            ts = get_db_mtime_ms(db_path)
            s["createdAt_ms"] = ts
            s["createdAt_iso"] = datetime.fromtimestamp(
                ts / 1000, tz=timezone.utc
            ).strftime("%Y-%m-%d") if ts > 0 else ""
            s["_used_mtime"] = True

        if CYCLE_START_MS <= ts <= CYCLE_END_MS:
            in_cycle.append(s)
        else:
            out_cycle.append(s)

    print(
        f"In cycle window: {len(in_cycle)}, outside: {len(out_cycle)}",
        file=sys.stderr,
    )

    # Write all in-cycle sessions as JSONL
    with open(output_path, "w", encoding="utf-8") as f:
        for s in in_cycle:
            f.write(json.dumps(s) + "\n")

    print(f"Wrote {len(in_cycle)} sessions → {output_path}", file=sys.stderr)

    # Print workspace summary
    from collections import Counter
    ws_counts = Counter(s["projectName"] for s in in_cycle)
    print("\nTop workspaces by session count:", file=sys.stderr)
    for name, count in ws_counts.most_common(10):
        print(f"  {count:3d}  {name}", file=sys.stderr)

    return in_cycle


def main():
    base_path = Path(
        sys.argv[1] if len(sys.argv) > 1 else
        os.path.expanduser("~/Library/Application Support/Cursor/User")
    )
    output_path = Path(
        sys.argv[2] if len(sys.argv) > 2 else "/tmp/cursor_sessions.jsonl"
    )

    harvest(base_path, output_path)


if __name__ == "__main__":
    main()
