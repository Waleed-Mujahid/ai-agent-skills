#!/usr/bin/env python3
"""
harvest_plane.py — Fetch Plane work items for a user via REST API
Usage: python3 harvest_plane.py <workspace_slug> <project_id> <date_from> <output_file> [assignee_name]

Requires: PLANE_TOKEN env var (PAT token)
Falls back to mcp__plane-arbisoft__* tools if no PLANE_TOKEN.

Note: If using MCP tools directly (recommended for Waleed's workspace), skip this script
and call mcp__plane-arbisoft__list_work_items from Claude directly.
"""

import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime

def fetch_plane(workspace_slug, project_id, date_from, output_file, assignee_name=None):
    token = os.environ.get("PLANE_TOKEN")
    if not token:
        print("ERROR: PLANE_TOKEN not set. Set it or use MCP tools directly.", file=sys.stderr)
        sys.exit(1)

    base_url = f"https://api.plane.so/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/"
    headers = {
        "X-Api-Key": token,
        "Content-Type": "application/json",
    }

    all_items = []
    next_url = f"{base_url}?per_page=100&cursor=100:0:0"

    while next_url:
        req = urllib.request.Request(next_url, headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read())
        except Exception as e:
            print(f"ERROR fetching {next_url}: {e}", file=sys.stderr)
            break

        results = data.get("results", [])
        all_items.extend(results)

        # Pagination
        next_cursor = data.get("next_cursor")
        if next_cursor and data.get("next_page_results"):
            next_url = f"{base_url}?per_page=100&cursor={next_cursor}"
        else:
            next_url = None

    # Filter by date and optionally assignee
    date_threshold = datetime.fromisoformat(date_from)
    filtered = []
    for item in all_items:
        updated = item.get("updated_at", "")
        if updated:
            try:
                dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                if dt.replace(tzinfo=None) < date_threshold:
                    continue
            except:
                pass

        if assignee_name:
            assignees = item.get("assignees", [])
            if not any(assignee_name.lower() in str(a).lower() for a in assignees):
                continue

        filtered.append(item)

    # Write markdown table
    lines = [
        f"# Plane Work Items — {workspace_slug}/{project_id} since {date_from}",
        f"\nTotal items found: {len(filtered)}\n",
        "| sequence_id | title | state | date | description-1liner |",
        "|-------------|-------|-------|------|-------------------|",
    ]

    for item in filtered:
        seq = item.get("sequence_id", "?")
        title = (item.get("name") or "")[:80]
        state = item.get("state_detail", {}).get("name", item.get("state", "Unknown"))
        date = (item.get("updated_at") or "")[:10]
        desc = (item.get("description_stripped") or "")[:80]
        lines.append(f"| {seq} | {title} | {state} | {date} | {desc} |")

    with open(output_file, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Wrote {len(filtered)} items to {output_file}", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print(__doc__)
        sys.exit(1)

    fetch_plane(
        workspace_slug=sys.argv[1],
        project_id=sys.argv[2],
        date_from=sys.argv[3],
        output_file=sys.argv[4],
        assignee_name=sys.argv[5] if len(sys.argv) > 5 else None,
    )
