# sophia-review

End-to-end Sophia competency self-review assistant. Runs as a **phased chat** — see
[`sophia-review.md`](./sophia-review.md) for the full pipeline. This README documents the
helper scripts and the auth model.

## Phases

```
0 Preflight + Auth + Discovery   MCP checklist, delegate offer, workdir, ID discovery,
                                 refresh-token bootstrap, fetch Sophia data, rubric delta,
                                 link all trackers (Plane/Jira/GitHub Projects/…)
0.6 User achievements brief      user brain-dumps own critical/proud work → steers harvest
1 Harvest (parallel bg agents)   GitHub / trackers (all boards) / Slack / Calendar / sessions
1.5 Coverage audit + backfill    month histogram catches early-stopped pagination
2 Evidence map + AI cross-cut    atoms -> rubric lines, strength + proof-tier
3 Differentials + questions       show L_current vs L_target, ask targeted gap questions
4 Draft                          rubric-aligned HTML answers, template enforced
5 Submit + verify                POST via API, GET-verify persistence, final validation
6 Skill maintenance              fold learnings back
```

## Auth model (refresh-token bootstrap)

Sophia issues short-lived access JWTs plus a long-lived `refresh-token` cookie.

```
browser login -> copy `refresh-token` cookie -> paste into <workdir>/.sophia/refresh_token
              -> sophia_auth.py exchanges it for an access token (cached)
              -> decodes JWT exp clientside, auto-refreshes within 60s of expiry
              -> on failure, prints exact re-paste steps
```

Token files (all chmod 600, gitignored):

| File | Contents |
|------|----------|
| `<workdir>/.sophia/refresh_token` | the `refresh-token` cookie value (you paste this) |
| `<workdir>/.sophia/access_token` | cached access JWT (written by the helper) |
| `<workdir>/.sophia/config.json` | `sophia_user_id`, `user_competency_framework_id`, etc. |

`sophia_user_id` is **auto-decoded from the refresh-token JWT** (`sophia_auth.py userid`),
so the only things the user supplies are the refresh-token cookie and the UCF id. Env
overrides: `SOPHIA_REFRESH`, `SOPHIA_TOKEN`, `SOPHIA_USER_ID`, `SOPHIA_UCF_ID`,
`SOPHIA_API_ROOT`, `SOPHIA_REFRESH_BEARER`.

> **Unverified across tenants:** the refresh exchange POSTs to
> `{API_ROOT}/users/<id>/refresh-token` with body `{"refresh": "<token>"}`, sending the
> refresh token itself as the Bearer (bootstrap). If a tenant rejects that, set
> `SOPHIA_REFRESH_BEARER` to a valid access token; the error block explains the fix. The
> first real run should confirm and the skill changelog updated.

## Helpers

| File | What it does |
|------|--------------|
| `helpers/sophia_auth.py` | Refresh-token bootstrap, JWT-exp decode, token cache. `token` / `refresh` / `whoami`. Importable `get_valid_token(workdir)`. |
| `helpers/sophia_api.py` | Fetches `framework_details.json`, `progress_overview.json`, `summary_dashboard.json`, history files for the configured UCF id. |
| `helpers/rubric_delta.py` | Parses the framework JSON into a where-you-stand table + per-subcat L_current vs L_target sections. |
| `helpers/prev_answers.py` | Dumps each subcat's FULL previous-cycle answer to `answers/_prev/<id>_<slug>.html` — drafter improves on it; hold subcats carry it forward. |
| `helpers/coverage_audit.py` | Month histogram per evidence file; flags sparse months (early-stopped pagination). |
| `helpers/progress.py` | Inspects the workdir and prints a ✅/⬜ milestone checklist + `RESUME AT:` line — lets the skill continue in a fresh chat. |
| `helpers/submit_answer.py` | POSTs one answer, GET-verifies persistence. Reads UCF id from config, auto-refresh on 401. |
| `helpers/harvest_cursor.py` | Extracts Cursor chat/composer history from `state.vscdb` SQLite stores. |
| `helpers/harvest_plane.py` | Paginates Plane work items + activity. |
| `helpers/harvest_github.sh` | `gh`-based authored / upstream / review harvest. |
| `helpers/harvest_calendar.md` | Calendar MCP recipe (attendee + keyword filter, noise drop). |
| `helpers/harvest_shoutouts.md` | Shoutout-channel recipe (URL resolve, reactions). |
| `helpers/harvest_slack.md` | Slack channel/DM pagination recipe. |

## Templates

`config_template.json`, `session_context_template.md` (per-run `CLAUDE.md`),
`answer_template.md`, `rubric_delta_section.md`, `evidence_map_row.md`,
`ai_mentoring_map.md`.

## Requirements

- `gh` CLI authenticated (`gh auth status`).
- Slack / Plane / Google Calendar MCPs connected (Calendar optional; OAuth via `/mcp`).
- Optional: the [`delegate`](../delegate) skill for token-cheap tagging/formatting.
- Python 3 + `curl` (no third-party Python deps).
