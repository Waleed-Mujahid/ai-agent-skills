# Slack Shoutouts Harvest — MCP Tool Recipe

Use `mcp__claude_ai_Slack__*` tools directly from Claude. Do NOT delegate to opencode (MCP unavailable in subagents).

## Overview

Shoutouts are public praise messages sent to or about the user. Harvest from:
1. A dedicated shoutouts channel (if the org has one)
2. Search results across public + private channels

---

## Step 1 — URL → Thread Timestamp Conversion

Slack message URLs use a `p`-prefixed timestamp in the URL path. Convert to the `thread_ts` format needed by `slack_read_thread`:

```
URL format:  https://yourorg.slack.com/archives/C012345/p1771934396271209
                                                          ↑ p + 16 digits

Conversion:
  raw       = "1771934396271209"          # strip leading "p"
  integer   = raw[:-6]    → "1771934396"
  decimal   = raw[-6:]    → "271209"
  thread_ts = "1771934396.271209"
```

Python one-liner:
```python
def url_to_ts(url: str) -> str:
    p_part = url.rstrip("/").split("/")[-1]  # "p1771934396271209"
    digits = p_part.lstrip("p")             # "1771934396271209"
    return digits[:-6] + "." + digits[-6:]  # "1771934396.271209"
```

---

## Step 2 — Read Explicit Shoutout URLs

If the user provides explicit shoutout message URLs, fetch each thread:

```python
for url in SHOUTOUT_URLS:
    ts = url_to_ts(url)
    channel_id = url.split("/archives/")[1].split("/")[0]  # extract Cxxxxxxx

    # Fetch the thread
    thread = mcp__claude_ai_Slack__slack_read_thread(
        channel_id=channel_id,
        thread_ts=ts
    )

    # Get reactions on the root message
    reactions = mcp__claude_ai_Slack__slack_get_reactions(
        channel_id=channel_id,
        timestamp=ts
    )
```

---

## Step 3 — Channel Sweep

If a shoutouts channel ID is provided, read the full channel and paginate:

**CRITICAL: paginate to cycle start OR empty page, never stop after a fixed number of pages.**

```python
SHOUTOUTS_CHANNEL_ID = "<channel_id>"    # e.g. "C012SHOUT"
USER_DISPLAY_NAME    = "<waleed>"        # used to filter messages about the user

cursor = None
all_msgs = []

while True:
    result = mcp__claude_ai_Slack__slack_read_channel(
        channel_id=SHOUTOUTS_CHANNEL_ID,
        limit=200,
        cursor=cursor       # omit on first call if not supported; check response for cursor
    )

    msgs = result if isinstance(result, list) else result.get("messages", [])
    all_msgs.extend(msgs)

    # Stop conditions
    if not msgs:
        break

    oldest_ts = float(msgs[-1].get("ts", "0"))
    if oldest_ts < date_from_epoch:
        break

    cursor = result.get("response_metadata", {}).get("next_cursor") if isinstance(result, dict) else None
    if not cursor:
        break

# Filter: keep messages that mention the user's display name or Slack user ID
relevant = [
    m for m in all_msgs
    if USER_DISPLAY_NAME.lower() in m.get("text", "").lower()
    or USER_SLACK_ID in m.get("text", "")
]
```

---

## Step 4 — Search for Additional Shoutouts

Search across all public and private channels for messages mentioning the user:

```python
results = mcp__claude_ai_Slack__slack_search_public_and_private(
    query=f"shoutout {USER_DISPLAY_NAME}",
)

# Also try alternate search terms
results2 = mcp__claude_ai_Slack__slack_search_public_and_private(
    query=f"kudos {USER_DISPLAY_NAME}",
)

results3 = mcp__claude_ai_Slack__slack_search_public_and_private(
    query=f"great work {USER_DISPLAY_NAME}",
)
```

Deduplicate by `ts` + `channel` before combining with channel sweep results.

---

## Step 5 — Build Output Table

For each shoutout, fetch reactions if not already fetched:

```python
reactions = mcp__claude_ai_Slack__slack_get_reactions(
    channel_id="<channel_id>",
    timestamp="<ts>"
)
```

Format reaction counts as `emoji_name:count` pairs, e.g. `👍:5, 🎉:3, ❤️:2`.

**Output table:**

```markdown
| date | author | excerpt | reactions | thread_link | context |
|------|--------|---------|-----------|-------------|---------|
| YYYY-MM-DD | <display_name> | <first 150 chars of message> | <emoji counts> | <slack_url> | <channel_name or DM> |
```

- **author**: person who wrote the shoutout (not the recipient)
- **excerpt**: first 150 chars of the message text, with `@mentions` preserved
- **reactions**: formatted emoji reaction list (omit if none)
- **thread_link**: reconstruct from `channel_id` + `ts` → `p` format URL, or use provided URL
- **context**: channel name (e.g. `#shoutouts`, `#general`) or `DM`

Write to `$WORKDIR/evidence/i_shoutouts.md`.

---

## Reconstructing a Slack Message URL

To build a permalink from channel ID + `ts`:
```python
def ts_to_url(channel_id: str, ts: str, workspace: str = "yourorg") -> str:
    digits = ts.replace(".", "")     # "1771934396271209"
    return f"https://{workspace}.slack.com/archives/{channel_id}/p{digits}"
```

Pass the workspace slug as a parameter — do not hardcode.

---

## Auth Note

If Slack MCP returns auth errors:
```python
mcp__claude_ai_Slack__slack_authenticate()
```
Complete with the returned URL. Re-run harvest after successful auth.
