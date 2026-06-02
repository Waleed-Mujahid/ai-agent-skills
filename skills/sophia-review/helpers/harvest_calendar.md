# Google Calendar Harvest — MCP Tool Recipe

Use `mcp__claude_ai_Google_Calendar__*` tools directly from Claude. Do NOT delegate to opencode (MCP unavailable in subagents).

## Prerequisites — OAuth

Google Calendar MCP requires OAuth authentication before use. If not yet authorized:

1. Go to `https://claude.ai` in a browser
2. Open the MCP panel (`/mcp` in the sidebar or settings)
3. Authorize "Google Calendar" integration
4. Re-run this skill after auth completes

**If any Calendar tool returns an auth error, stop and prompt the user to complete OAuth before proceeding.**

---

## Step 1 — List Calendars

```python
mcp__claude_ai_Google_Calendar__list_calendars()
```

Identify the primary calendar ID (usually the user's email address). Note any team/shared calendars to include.

---

## Step 2 — Paginated Event Fetch

Google Calendar MCP returns events with a `nextPageToken`. **CRITICAL: paginate until the response has no `nextPageToken` OR all events are before `date_from`. Never stop after a fixed number of pages.**

```python
# Inputs (parameterize — do not hardcode):
CALENDAR_ID    = "<user_email_or_calendar_id>"
DATE_FROM      = "<YYYY-MM-DD>"          # cycle start
DATE_TO        = "<YYYY-MM-DD>"          # cycle end (today or review date)
TEAMMATE_NAMES = ["<name1>", "<name2>"]  # attendee filter list
PAGE_TOKEN     = None

all_events = []

while True:
    result = mcp__claude_ai_Google_Calendar__list_events(
        calendar_id=CALENDAR_ID,
        time_min=DATE_FROM + "T00:00:00Z",
        time_max=DATE_TO   + "T23:59:59Z",
        max_results=250,
        page_token=PAGE_TOKEN   # omit on first call
    )

    events = result.get("items", [])
    all_events.extend(events)

    PAGE_TOKEN = result.get("nextPageToken")
    if not PAGE_TOKEN:
        break
```

---

## Step 3 — Filter & Classify Events

Keep events where:
- User is an attendee AND `responseStatus` is `accepted` or `tentative` (not `declined`)
- Event has at least one other attendee (not solo blocks)
- Duration ≥ 10 minutes

Apply tag types using this priority list (first match wins):

| Signal | Tag |
|--------|-----|
| Attendee list intersects `TEAMMATE_NAMES` AND title contains "1:1" or is exactly two people | `1:1` |
| Title contains "mentor", "coaching", "office hours", "pair" | `mentoring` |
| Title contains "AI training", "AI workshop", "claude", "cursor", "copilot" (case-insensitive) | `ai-training` |
| Title contains "sprint review", "retrospective", "retro", "planning" | `sprint-review` |
| Title contains "kickoff", "kick-off", "kick off" | `kickoff` |
| Title contains "deploy", "release", "rollout", "cutover" | `deploy-coord` |
| Title contains "client", "demo", "presentation", "stakeholder" | `client-meet` |
| Any attendee in `TEAMMATE_NAMES` | `1:1` (if 2 people) or `mentoring` (if attendee is junior) |
| Fallback | `other` |

---

## Step 4 — Build Output Table

```markdown
| date | time | title | attendees | duration_min | tag | event_id |
|------|------|-------|-----------|--------------|-----|----------|
| YYYY-MM-DD | HH:MM | <summary> | <comma-list> | <N> | <tag> | <id> |
```

**Attendees**: list display names only (not emails). Omit the reviewing user. Truncate to first 4 names + "…+N more" if >4.

**Duration**: compute from `start.dateTime` → `end.dateTime`. For all-day events, set `duration_min = 480` (assumed 8h) and note `(all-day)` in title.

Write to `$WORKDIR/evidence/h_calendar_events.md`.

---

## Teammate-Attendee Filter — Parameterized Inputs

Pass teammate names as a list at harvest time. Example invocation context:

```
TEAMMATE_NAMES = [
    "Abdullah Rafiq",
    "Ahmad Bilal",
    "<add teammates here>"
]
```

The filter is used to:
1. Detect 1:1 meetings (exactly 2 people, one is a teammate)
2. Detect mentoring meetings (teammate is junior/QA)
3. Tag `deploy-coord` when teammates + "deploy" in title

---

## Single Event Lookup

To fetch details for a specific event (e.g., from a shoutout URL):

```python
mcp__claude_ai_Google_Calendar__get_event(
    calendar_id=CALENDAR_ID,
    event_id="<event_id>"
)
```

---

## Auth Errors During Harvest

If a tool call returns `401` or `"unauthorized"`:
```python
# Do NOT retry in a loop. Stop and ask user to re-authenticate via /mcp in claude.ai.
```
