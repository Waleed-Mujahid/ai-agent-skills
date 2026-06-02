# AI Mentoring Map — Schema & Usage

## Purpose

Cross-cut table that collects all AI-related mentoring, skill-sharing, and teaching evidence from multiple sources (calendar, Slack DMs, shoutouts, channel posts, Cursor sessions, Claude skill builds). Used in Phase 2.5 to populate the "AI mentoring" and "Technical leadership" subcategories.

## Table Schema

```markdown
| date | atom_ref | type | mentee | topic | outcome | subcat_tags |
|------|----------|------|--------|-------|---------|-------------|
```

**Column definitions:**

| Column | Format | Description |
|--------|--------|-------------|
| `date` | `YYYY-MM-DD` | Date of the event or earliest date of the exchange |
| `atom_ref` | `<source_file>#<row_or_id>` | Pointer back to the evidence file row (e.g. `h_calendar_events.md#row-14`, `f_slack_dms.md#row-3`) |
| `type` | see enum below | Interaction type |
| `mentee` | display name or `team` | Person(s) receiving the knowledge; use `team` for public posts |
| `topic` | ≤80 chars | What was taught/shared (e.g. "Claude Code skill authoring", "prompt caching API", "Cursor composer tips") |
| `outcome` | ≤120 chars | Concrete result (e.g. "mentee shipped feature using technique", "team adopted AI tool", "PR merged with technique") |
| `subcat_tags` | comma-separated subcat IDs | Which rubric subcategories this atom supports |

## Type Enum

| Value | When to use |
|-------|-------------|
| `1:1 meet` | Scheduled 1:1 calendar event, AI/tech topic |
| `recurring meet` | Recurring team sync or weekly check-in |
| `slack-DM` | Private DM exchange (from `f_slack_dms.md`) |
| `skill-share PR` | PR review where reviewer taught technique |
| `channel-post` | Public channel message teaching or explaining AI tool |
| `claude-skill-built` | Built a reusable Claude skill / tool for team use |
| `cursor-pairing` | Cursor composer session involving pairing or teaching |
| `AI-training-meet` | Dedicated AI tools training session (from `h_calendar_events.md` tag `ai-training`) |

## Example Rows

```markdown
| date | atom_ref | type | mentee | topic | outcome | subcat_tags |
|------|----------|------|--------|-------|---------|-------------|
| 2026-03-12 | h_calendar_events.md#row-8 | AI-training-meet | team | Cursor composer workflow | 5 engineers adopted Cursor in next sprint | 1184,1187 |
| 2026-04-01 | f_slack_dms.md#row-14 | slack-DM | Abdullah Rafiq | Claude Code slash commands | QA started using /sophia-review skill | 1184 |
| 2026-02-20 | e_slack_channels.md#row-31 | channel-post | team | Prompt caching pattern for Django views | Shared snippet, 3 teammates reacted | 1177,1184 |
| 2026-01-15 | g_claude_sessions.md#row-2 | claude-skill-built | team | /activity-report skill | Skill reused by 2+ teammates | 1184,1187 |
```

## Build Instructions (Phase 2.5)

1. Read `h_calendar_events.md` — extract rows with tag `ai-training`, `mentoring`, or `1:1` where topic involves AI tools
2. Read `f_slack_dms.md` — extract rows with type `mentoring` or `knowledge-transfer`
3. Read `e_slack_channels.md` — extract rows with type `ai-tooling` or `mentoring`
4. Read `i_shoutouts.md` — extract rows that mention AI tools, skills, or teaching
5. Read `g_claude_sessions.md` — extract skill-building sessions (project = `.claude/skills`)
6. Cross-reference Cursor sessions from `harvest_cursor.py` output for pairing evidence
7. For each atom: pick the `type` from the enum, identify `mentee`, write `outcome` based on any follow-up evidence

Write to `$WORKDIR/evidence/11_ai_mentoring_map.md`.

## Subcategory Tag Reference (common AI-mentoring subcats)

Populate `subcat_tags` with IDs from `00_rubric_delta.md`. Common ones:
- Subcats under "Technical Execution" → skills demonstrated through AI tooling
- Subcats under "Communication" → knowledge sharing, documentation
- Subcats under "Teamwork" → mentoring, pair programming, upskilling others

Always verify IDs against the actual framework — do not hardcode subcat IDs.
