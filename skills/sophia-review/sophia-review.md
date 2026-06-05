---
name: sophia-review
description: "End-to-end assistant for writing a Sophia competency self-review — the self-evaluation employees fill out on platformsophia.com against their competency framework. Runs as a phased chat: configures auth + MCPs, fetches your rubric, harvests a year of evidence from GitHub/trackers/Slack/Calendar/Claude+Cursor sessions in parallel, maps it to rubric levels, surfaces next-level (e.g. L2→L3) differentials, drafts rubric-aligned answers, and submits + verifies them via the Sophia API. Use whenever someone needs to write, improve, draft, redo, or fill out their Sophia / competency self-review, performance self-assessment, or annual self-evaluation — even if they don't say the word 'Sophia'. NOT for code review, PR review, document review, or reviewing someone else's work."
argument-hint: "(no args — workdir is always ~/Documents/sophia-review)"
allowed-tools: Bash, Read, Write, Edit, Agent, TaskCreate, TaskUpdate, TaskList, AskUserQuestion, mcp__claude_ai_Slack__slack_read_channel, mcp__claude_ai_Slack__slack_read_thread, mcp__claude_ai_Slack__slack_search_public_and_private, mcp__claude_ai_Slack__slack_search_public, mcp__claude_ai_Slack__slack_read_user_profile, mcp__claude_ai_Slack__slack_get_reactions, mcp__claude_ai_Google_Calendar__list_calendars, mcp__claude_ai_Google_Calendar__list_events, mcp__claude_ai_Google_Calendar__get_event, mcp__plane-arbisoft__list_work_items, mcp__plane-arbisoft__retrieve_work_item_by_identifier, mcp__plane-arbisoft__list_work_item_activities
---

# Sophia Competency Self-Review Assistant

A phased, interactive pipeline. Treat it as **a chat that executes in phases** — at the
end of every phase, stop at the gate, show the user what you have, and wait for "go"
before the next phase. The user can pause/resume across sessions; everything persists to
the workdir.

`SKILL_DIR` below = the directory containing this file (`.../skills/sophia-review`).
Resolve helper paths relative to it: `SKILL_DIR/helpers/<name>`.

## Operating principles

- **Phased chat with gates.** Never blast through all phases silently. Each phase ends with a checkpoint.
- **Gather intel before asking.** Harvest GitHub/Plane/Slack/Calendar/sessions FIRST, then only ask the user about gaps the data can't fill (shoutouts, private context, which project owns which claim).
- **Token discipline.** Sub-agent output is a summary, never raw dumps — never `Read`/`tail` a harvest agent's full output file into context; trust its summary line. Use the `delegate` skill (free models) for mechanical tagging/formatting. Reasoning, drafting, and user-facing text stay with the main model.
- **Every claim needs an artifact.** PR link, Plane ticket, Slack permalink, calendar event, or metric. No vague claims.
- **Confident, never dishonest.** Auditors score against the rubric; admitted weakness lowers the score. Be specific and technical. But never invent evidence — if an atom isn't real, don't cite it.
- **Resumable.** Everything persists to the workdir. A new chat picks up exactly where the last left off (Phase 0.0).

---

## Phase 0.0 — Resume or fresh start (ALWAYS run first)

Before anything else, detect prior progress in the workdir:

```bash
python3 "$SKILL_DIR/helpers/progress.py" --workdir "$HOME/Documents/sophia-review"
```

It prints a ✅/⬜ checklist of every milestone (auth, ids, data, delta, Gate 0 targets,
harvest sources, evidence map, drafts) and a `👉 RESUME AT:` line.

- **Fresh start** (no workdir / nothing done): begin at Phase 0.1.
- **Existing run**: summarize the checklist to the user in plain language ("last time we got
  through the rubric delta; targets aren't confirmed yet"), then **jump straight to the
  RESUME-AT phase** — do NOT re-ask for the token/ids or re-fetch data that already exists.
  Confirm with the user before redoing any completed step.

As you pass each gate, write a marker to `$WORKDIR/.sophia/progress.json` (e.g.
`{"gate0": true, "phase1": true, ...}`) so resume stays accurate even mid-phase.

---

## Phase 0 — Preflight, Auth, Discovery setup

Create the phase checklist with `TaskCreate` so the user sees the whole arc:
`Preflight → Auth → Fetch Sophia data → Brief → Harvest evidence → Evidence map → Differentials & questions → Draft → Unbiased audit → Submit`.

**Ask the user for as little as possible.** Auto-discover everything you can; default the
rest; only the **two things below are genuinely required** (a token and one id). Make every
data source beyond GitHub clearly optional.

### 0.1 — Preflight (auto, no questions)

```bash
WORKDIR="${HOME}/Documents/sophia-review"          # hardcoded — do not ask
mkdir -p "$WORKDIR/evidence" "$WORKDIR/answers" "$WORKDIR/.sophia"
printf '.sophia/\n*.token\n' > "$WORKDIR/.gitignore"
```

- **GitHub**: try `gh auth status` first. If not logged in, ask the user to run
  `gh auth login` (the only GitHub ask). Then auto-discover the username:
  `gh api user --jq .login` — never ask for it. Orgs default to
  `edly-io,openedx,overhangio`; override only if the user offers.
- **Date range**: default silently to the last 12 months
  (`cycle_start = $(date -v-12m +%Y-%m-%d)` / GNU `date -d '12 months ago'`); don't ask.
- **Cursor**: auto-detect `~/Library/Application Support/Cursor/User`. If it exists, harvest
  it (it's local IDE chat history — pairing / cross-repo evidence); if not, skip silently.
  Don't ask about it.
- **delegate skill** (token saver): if not in the available-skills list, offer once —
  `/plugin marketplace add Waleed-Mujahid/ai-agent-skills` then
  `/plugin install delegate@ai-agent-skills`. Proceed without it if declined.
- **Optional MCPs** — note which are connected this session, don't gate on them: Slack
  (channel/DM coordination evidence), Google Calendar (1:1 / mentoring cadence; needs OAuth
  via `/mcp`), Plane or another tracker (delivery evidence). These enrich the evidence pool;
  the review still works with GitHub + Sophia alone.

### 0.2 — Auth + the one required id

Two things only the user can give. Ask for both together:

**(a) Refresh token** — Sophia issues short-lived access JWTs behind a long-lived
`refresh-token` cookie. Get it once. **Always surface these source steps as inline comments
in the command block** (the user may see only the command, not the prose):

```bash
# Where the token comes from:
#   1. Log into Sophia in your browser (https://app.platformsophia.com or your tenant).
#   2. Open DevTools (F12) -> Application tab -> Storage -> Cookies -> the platformsophia.com entry.
#   3. Find the cookie literally named  refresh-token  and copy its Value to your clipboard.
#   4. Run the commands below — pbpaste reads the clipboard, so the token is never typed in chat.
WORKDIR="$HOME/Documents/sophia-review"
pbpaste > "$WORKDIR/.sophia/refresh_token" && chmod 600 "$WORKDIR/.sophia/refresh_token"
```

**(b) UCF id** — `user_competency_framework_id`, unique per person+framework, not
discoverable from the token:
> DevTools → **Network** → reload your self-review page → find a request to
> `…/competencies/framework/?user_competency_framework_id=XXXX` → give me `XXXX`.

Everything else is derived. The **Sophia user id** is decoded from the refresh-token JWT —
no need to ask:

```bash
echo '{"user_competency_framework_id": <UCF>}' > "$WORKDIR/.sophia/config.json"
chmod 600 "$WORKDIR/.sophia/config.json"
python3 "$SKILL_DIR/helpers/sophia_auth.py" refresh --workdir "$WORKDIR"   # cookie -> access token
python3 "$SKILL_DIR/helpers/sophia_auth.py" userid  --workdir "$WORKDIR"   # auto-decoded user id
```

Write the decoded user id + UCF id into `.sophia/config.json`. **If refresh fails**, the
helper prints exact re-paste steps — relay them (cookie expired → grab a fresh one). First
real run: confirm the refresh-exchange shape (helper sends the refresh token as the Bearer;
the error block flags a tenant that rejects it).

### 0.3 — Fetch Sophia data + auto-fill config

The rubric is fetched from the API (see `metadata.csv` for the endpoint map) — never ask the
user for a `framework_details.json` path or a `draft_eval_id`:

```bash
python3 "$SKILL_DIR/helpers/sophia_api.py" --workdir "$WORKDIR"
```

Writes `framework_details.json` (core rubric + last year's answers), `progress_overview.json`,
`summary_dashboard.json`, history files. Now auto-derive the rest of the config from those —
**don't ask for any of it**: `framework_name` (`framework_details.json → framework`),
`draft_eval_id` (`progress_overview.json → draft_evaluation.id`), `due_date`
(`summary_dashboard.json → current_phase_deadline`), `primary_auditor`, current score/level.
Fill `.sophia/config.json` (from `templates/config_template.json`) and write
`$WORKDIR/CLAUDE.md` from `templates/session_context_template.md`.

### 0.4 — Optional enrichment sources (offer, never require)

After the core is working, offer (don't require) the extras that make answers richer. Frame
each as optional and skippable:
- "Want me to scan Slack for coordination / mentoring evidence? Paste channel and/or DM ids, or skip." → `slack_channels`, `slack_dms`.
- "Any shoutouts/kudos this cycle? Paste the **Slack message URLs** — that's all I need (no channel id)." → `shoutout_urls`. (A channel id is optional, only to auto-scan for more.)
- "Harvest Google Calendar for 1:1 / mentoring / training cadence? (needs the Calendar MCP OAuth'd via `/mcp`)." If yes, ask teammate names for the attendee filter → `teammates`.
- **Trackers (ask for ALL of them, of any kind).** Don't assume one tool or one board —
  people on multiple projects have multiple boards, and different teams use different
  trackers (Plane, **Jira**, **GitHub Projects**, Linear, Trello…). Ask plainly: "Which
  issue trackers / project boards did you work on this cycle? Link **everything relevant** —
  list every board across every project, and tell me which tool each is (Plane / Jira /
  GitHub Projects / other)." For each, capture what's needed to reach it:
  - **Plane**: if the MCP is connected, list projects and let the user multi-select → `plane_projects` (list of `{id, name}`).
  - **Jira**: project key(s) + site/base URL (and board ids if they have them) → `jira_boards`.
  - **GitHub Projects**: org/user + project number(s) — harvest via `gh project item-list` → `github_project_boards`.
  - **Anything else**: ask how to reach it (URL / API / export) → `other_trackers`.
  Store each as a **list** — never a single id. Skipped trackers are simply not harvested.

Persist whatever the user gives into `.sophia/config.json`. Skipped sources are simply not harvested.

### 0.5 — Rubric delta + "where you stand"

```bash
python3 "$SKILL_DIR/helpers/rubric_delta.py" "$WORKDIR/framework_details.json" \
  --history "$WORKDIR/person_competency_history.json" \
  --out "$WORKDIR/evidence/00_rubric_delta.md" --json "$WORKDIR/.sophia/delta.json"

# Dump each subcat's FULL previous-cycle answer (not the 600-char snippet) — the drafter
# improves on these, and "hold" subcats carry them forward so nothing blanks out.
python3 "$SKILL_DIR/helpers/prev_answers.py" "$WORKDIR/framework_details.json" \
  --out "$WORKDIR/answers/_prev"
```

**Generate and present the table yourself.** After `rubric_delta.py` compiles the data, read
`00_rubric_delta.md` and **render its Markdown table into the chat** (terminal renders
GitHub-flavored Markdown — a real table, not a list). Columns: Category · Subcategory · Cat%
· Now · Proposed · Action · Prev. Then state the headline (overall level + score) and call out
the **MUST-FILL** subcats (no prior answer) and any **N/A** ones (mobile criteria for a
backend engineer).

**Refer to subcategories by NAME, never by bare id.** The user can't read `1170, 1174` — say
"Code Architecture (L2→L3)". IDs are tooling-only (`.sophia/delta.json`).

**Targets are the user's self-evaluation — they choose, the tool only proposes.** Walk the
user through it: the `Proposed`/`Action` columns are the realistic default, not a mandate.
For each subcategory the user decides which level they're claiming this cycle, reading the
per-subcat rubric gap (the "Now vs Next" text in `00_rubric_delta.md`). Defaults follow this
logic so the user has a sane starting point:
- **≤ L2 → next level** (`raise`): good margin — L3 is typically "owns modules / go-to person *in the team*".
- **L3 → L4** (`stretch`): **held by default.** L4 means recognition *beyond* the team / an org-wide standard. Pursue only where the Phase 2 evidence map earns it — usually 1–3 across the whole review, re-decided after harvest.
- **No prior answer** (`fill`) / **unrated** (`baseline`): aim for a solid L2–L3 baseline.

The user confirms or overrides **by name** (e.g. *"Code Architecture L3, hold Effective
writing, push Self-Discipline to L4, mark both mobile N/A"*) — they may aim higher or lower
than the proposal; it's their self-assessment. Capture every subcat's decision and **persist
it** to `$WORKDIR/.sophia/targets.json`:

```json
{ "<subcat_id>": {"name": "...", "current": 2, "target": 3, "decision": "raise"} }
```
`decision` ∈ `raise | stretch | hold | hold_redraft | fill | baseline | na | skip`. **Every
downstream phase reads `targets.json`** — only subcats the user chose to target get
harvested-against, drafted, and submitted; `hold`/`na`/`skip` are left alone (holds still carry
forward in Phase 4). Use **`hold_redraft`** when the user wants to keep the *level* but rewrite
the answer fresh with this cycle's evidence (distinct from `hold` = carry `_prev` verbatim) —
common for soft-skill subcats where last year's text is thin but the level isn't changing.

> **Core Values needs the organisation's actual values doc.** If the framework has a "Core
> Values" subcat, ask the user to paste their company's core-values document, then structure
> the answer around the *named* values, mapping a concrete evidence atom to each one (on a real
> run: Trust/Effort/Value/Collaboration/Excellence, each backed by a specific PR, shoutout or
> award). A generic "I live the values" answer scores low.

> **Existing answers are read, not ignored.** Last year's full answer per subcat is in
> `answers/_prev/<id>_<slug>.html`. Raise/stretch targets improve on it; hold subcats carry it
> forward (Phase 4); MUST-FILL subcats are written from scratch. An existing
> `answers/<id>_<slug>.html` from an earlier run is resumed, not overwritten.

**Gate 0:** `targets.json` written from the user's self-evaluation; auth + data fetch
confirmed. Write `{"gate0": true}` to `.sophia/progress.json`. Then Phase 0.6.

### 0.6 — Your achievements brief (user brain-dump, BEFORE harvest)

The harvest only surfaces what's in the tools. It can't know which work *you* consider
critical, the context behind a PR, the fire you put out verbally, or the impact a ticket
title doesn't convey. **Give the user an explicit place to tell their own story first** — it
both fills gaps the tools miss and *steers* the harvest (project names, repos, teammates,
dates to dig into).

Prompt the user, framed as a free-form dump (no template pressure — you'll structure it
later):

> Before I go digging, tell me in your own words what you actually did this cycle. Don't
> worry about format or the rubric — just brain-dump. Especially:
> - **Biggest things you shipped** — modules, features, migrations, launches (with project/repo names if you remember).
> - **Critical saves** — production fires, urgent debugging, a release you unblocked, an outage you caught.
> - **Work you're proud of** that a ticket title wouldn't capture — a redesign, an R&D spike, a tricky integration.
> - **People you helped** — onboarded, unblocked, mentored, reviewed for (even informally).
> - **Anything off-tool** — verbal decisions, whiteboard architecture, cross-team coordination, on-call.
> Names of projects, repos, teammates, and rough dates help me harvest the proof.

Capture the raw answer verbatim to `$WORKDIR/evidence/00_user_brief.md` (one section per
theme; keep the user's own wording). This file is a **first-class evidence source**: Phase 1
uses the project/repo/teammate names in it to target the harvest; Phase 2 reads it alongside
the harvested atoms (the user's claims become atoms to find proof for); Phase 3 turns any
claim it *couldn't* find a tool artifact for into a targeted "got a link for this?" question.

Accept it incrementally — the user may add more across sessions; append, don't overwrite.
Skippable, but strongly encouraged ("even three bullets makes the answers much sharper").
Write `{"brief": true}` to `.sophia/progress.json` once captured. Then Phase 1.

---

## Phase 1 — Parallel evidence harvest (background agents)

Spawn harvest agents **in parallel, in the background** (`Agent` with `run_in_background:
true`, or `Explore` for read-only sweeps). Each writes ONE file to `$WORKDIR/evidence/` and
reports back a one-line summary. **Never read the full output files into context.**

**⚠ RE-CHECK MCP AVAILABILITY HERE (not just at preflight).** Slack/Plane/Calendar MCPs that
were "deferred" or absent at Phase 0 often become available once the user reconnects one
mid-session (a `claude mcp add`, an OAuth via `/mcp`). Before deciding a source is
unharvestable, try a cheap probe (your tracker MCP's whoami — e.g. `mcp__plane-arbisoft__get_me`
on Arbisoft's Plane; substitute your own MCP name — a 1-event calendar list, a
1-message channel read). If it now works, harvest it — don't carry forward a stale "deferred"
note from a prior run.

**⚠ PAGINATION CONTRACT (critical):** every harvest agent paginates to the cycle START or
an empty page — never stop after N pages. Stopping early skews evidence to recent months
and produces a wrong level assessment. Applies to A–J (every dated source); H/I/J
(Cursor / Calendar / shoutouts) are paginated to cycle-start but are sparse by nature.

**⚠ LARGE MCP RESULTS → FILE, NEVER INTO CONTEXT.** Plane `list_work_items` and Calendar
`list_events` over a 12-month range routinely exceed the tool-result token cap and get spilled
to a `tool-results/*.txt` file. Do **not** Read that file into context — process it with
`jq`/`python` (probe structure, then extract slices) and write only the distilled markdown to
`evidence/`. Plane/Calendar JSON often contains unescaped control characters that break `jq` →
parse with `python3 -c "json.load(open(f), strict=False)"` instead.

| Agent | Source | Output | Tool |
|-------|--------|--------|------|
| A | GitHub authored PRs (config orgs) | `a_github_edly_prs.md` | `gh` + delegate to tag |
| B | GitHub upstream PRs (non-org) | `b_github_upstream_prs.md` | `gh` + delegate |
| C | GitHub reviews & PR comments | `c_github_reviews.md` | `gh` |
| D | Tracker work items + activity (**every board the user linked, across all tools**) | `d_tracker_tickets.md` | Plane MCP / `gh project` / Jira API |
| E | Slack channels | `e_slack_channels.md` | Slack MCP (direct) |
| F | Slack DMs | `f_slack_dms.md` | Slack MCP (direct) |
| G | Claude Code sessions | `g_claude_sessions.md` | Bash + delegate to tag |
| H | Cursor sessions | `h_cursor_sessions.md` | `helpers/harvest_cursor.py` |
| I | Google Calendar events | `i_calendar_meetings.md` | Calendar MCP |
| J | Slack shoutouts | `j_shoutouts.md` | Slack MCP |
| K | **Code-artifact deep-dives** (flagship modules the user named in the brief) | `k_<artifact>_deepdive.md` | `Agent` (general-purpose, sonnet) reading the local repo + its PRs via `gh` |

**Agent K is the single highest-value addition** (proven on a real run). For each flagship
module the user calls out in `00_user_brief.md` (a plugin they own, a migration engine, a
feature shipped across repos), spawn one background `general-purpose` sonnet agent to **read
the actual code** in the local repo plus its PRs (`gh pr view`), and return a structured file:
`## Architecture / ## Security-correctness design / ## Scale numbers (LOC, files, commands,
tables, tenants) / ## Tests / ## Rubric mapping (subcat | concrete evidence | artifact)`. It
returns only a 4-6 line summary; the file feeds Phase 2/4. This is what turns "I own the
migration plugin" into "21,346 LOC, 15 commands, ~346 tables, 12+ tenants, AST-based
cross-tenant security tests" — the concrete, scannable detail auditors reward. Run 2-4 of
these in parallel for the user's top modules.

Recipes:
- GitHub: `helpers/harvest_github.sh` (authored/upstream/reviews) — use `gh` CLI, never the GitHub MCP.
- Trackers (one agent, **every board the user linked, across all tools** → merged into
  `d_tracker_tickets.md` with `tool` + `board` columns so sources are distinguishable; never
  harvest just the first board):
  - **Plane**: `helpers/harvest_plane.py` — loop over every id in `plane_projects`, paginate
    each to empty, pull `list_work_item_activities` for comment evidence. **Known quirks
    (self-hosted Plane, proven on a real run):**
    - `list_work_items` **with filter args** (`assignee_ids`, `state_ids`, …) hits the
      advanced-search endpoint and returns **HTTP 403**. Fall back to the plain list
      (`project_id` + `per_page` + `order_by` only) and **filter client-side**.
    - The MCP wrapper **drops `next_cursor`**, so you can't paginate a full year through the
      MCP. For a complete cycle, harvest via the **REST API with a PAT**:
      `curl -H "X-Api-Key: <PLANE_TOKEN>" "https://<host>/api/v1/workspaces/<ws>/projects/<proj>/issues/?per_page=100&cursor=<c>"`
      following `next_cursor`/`next_page_results` until done.
    - With `expand=assignees` the assignee field is **objects** (`email`/`display_name`);
      without it, bare UUIDs. Filter by the user's **email** to be robust to either shape.
    - **SSL:** macOS system Python 3.8 fails cert verification against the self-hosted host,
      and disabling TLS verification (`CERT_NONE`) is **blocked by the sandbox**. Use `curl`
      (system cert store) for the fetch, then parse the saved pages with python.
  - **GitHub Projects**: for each in `github_project_boards`,
    `gh project item-list <number> --owner <org> --format json` (filter to the user's items + cycle dates).
  - **Jira**: for each in `jira_boards`, query the REST search API
    (`/rest/api/3/search?jql=assignee=<user> AND updated>=<cycle_start>`) with the user's site + token.
  - **Other**: harvest per whatever access the user gave in `other_trackers`.
  Paginate every source to the cycle start.
- Slack channels/DMs: `helpers/harvest_slack.md` — `mcp__claude_ai_Slack__*` only; paginate via `oldest=<cycle_start_epoch>` + cursor.
- Calendar: `helpers/harvest_calendar.md` — auth first; filter to teammate attendees + AI/mentoring/1:1/training keywords; capture `htmlLink`; drop standing recurring noise (standup, sprint review, retro). **Caveats from a real run:** `list_events` with `fullText` caps around 50 results and matches broadly (title/desc/attendees), so per-person recurring-1:1 *counts* are unreliable — do **not** assert a precise cadence number (e.g. "52 1:1s with X"). Use the calendar for **headline, verifiable events** instead: the org-wide training with its **guest headcount** (a strong Speaking/Mentorship/Continuous-Learning atom — screenshot the attendee count), and a soft "regular 1:1/pairing cadence with multiple teammates". Round-number attendee counts must come from the event itself, not an estimate.
- Shoutouts: `helpers/harvest_shoutouts.md` — resolve supplied URLs (`p<ts>` → `<ts>` dotted), capture author + reactions + replies; also search the channel for the user's name.
- Cursor: `python3 "$SKILL_DIR/helpers/harvest_cursor.py" "<cursor_base>" "$WORKDIR/evidence/cursor_sessions.jsonl"` then tag into `h_cursor_sessions.md`.
- Claude sessions: `find ~/.claude/projects -name '*.jsonl' -newermt <cycle_start> -not -newermt <cycle_end>`; per file extract first user message + turn count + mtime; keep high-signal (≥30 turns OR keywords huddle/help/debug/migration/upstream/mentor); delegate tagging in batches ≤10.

**delegate tagging contract** (when offloading PR/session tagging to opencode): closed enum
for the `impact`/`type` column, pre-supply the data (never let opencode fetch), output
contract "ONLY the markdown table starting with `|`", strip `<think>…</think>`, batch ≤10,
retry once if row count ≠ input count.

**Gate 1:** Report a one-line count per agent (e.g. "A: 200 PRs, D: 88 tickets, J: 11 shoutouts"). Then Phase 1.5.

---

## Phase 1.5 — Coverage audit + backfill

```bash
python3 "$SKILL_DIR/helpers/coverage_audit.py" "$WORKDIR/evidence" \
  --cycle-start <cycle_start> --cycle-end <cycle_end> --min 3
```

Any `[SPARSE]` file (excluding shoutouts/upstream, sparse by nature) means an agent stopped
early — re-run that agent paginating to cycle start before Phase 2.

**URL backfill:** Plane URLs are constructible from sequence id
(`<plane_host>/<plane_workspace_slug>/browse/<SEQ>/` — both from `.sophia/config.json`;
defaults `https://projects.arbisoft.com` / `arbisoft`). For Slack atoms missing
permalinks, re-read the ±1-day epoch window, match by excerpt, build
`https://<team>.slack.com/archives/<channel>/p<ts_no_dot>`. Claude/Cursor sessions aren't
URL-shareable — mark Tier B (Drive screenshot during draft).

---

## Phase 2 — Evidence map + AI-mentoring cross-cut

Main-model pass (reasoning — do NOT delegate). Read all `evidence/*.md`, **including
`00_user_brief.md`** — each claim the user wrote there is an atom you must try to back with a
harvested artifact (PR/ticket/Slack link). A brief claim with a matched tool artifact is
strength-3; one you can't link yet becomes a Phase 3 question ("you mentioned X — got a link
for it?"). For each level-up subcategory, find matching atoms and write
`$WORKDIR/evidence/10_evidence_map.md`:

```
| subcat_id | subcat_title | rubric_quote | atom_source | atom_link | strength | tier |
```

- **strength**: 3 = directly proves the rubric line, 2 = strong indirect, 1 = supporting.
- **tier**: A = public shareable URL (PR/ticket/Slack permalink/calendar link/shoutout), B = private (DM/session — needs screenshot), C = metric/perf claim (needs supporting screenshot).
- **raise** targets: aim **≥5 strength-3 Tier-A atoms.** If short, flag for a Phase 3 question.
- **stretch** (L3→L4) targets: the bar is higher — L4 needs **evidence of recognition beyond the team or a standard others adopted** (out-of-team shoutout, an upstream/cross-team artifact, a pattern the org took up). If that class of evidence isn't in the map, **drop the stretch back to hold** — don't force an L4 claim the rubric won't support.

Then build `$WORKDIR/evidence/11_ai_mentoring_map.md` (schema in
`templates/ai_mentoring_map.md`): cross-cut of AI usage + mentoring evidence
(`| date | atom_ref | type | mentee | topic | outcome | subcat_tags |`). This angle feeds
Initiative, Mentorship, Coding Workflow, Continuous Learning, Core Values.

**Gate 2 — re-decide targets in BOTH directions here.** Show per-subcategory atom counts
(strength-3 / total). Then:
- Confirm each `raise` has enough evidence.
- For each provisional `stretch`, decide go/hold on whether out-of-team recognition exists.
- **Re-decide UP, not only down.** When the harvest turns up *more* than the Gate-0 plan
  assumed, propose raising the target. Real examples from a run: Mentorship planned as an L1
  baseline but the harvest showed onboarding a teammate to independent PRs + an org-wide
  training + cross-team help → raised to L3; Core Values planned L2 but an org "Team Champ"
  award explicitly citing collaboration/excellence → raised to L3. The Gate-0 plan is a floor,
  not a ceiling.

Finalize the target list (update `.sophia/delta.json` / `targets.json`). Then Phase 3.

---

## Phase 3 — Differentials & targeted questions (interactive)

This is the conversational core. For each level-up subcategory, in **weight-descending
order** (Technical Execution → Maturity → Communication → Teamwork):

1. **Show the differential.** Print the verbatim **L_current vs L_target** rubric text from `00_rubric_delta.md` — the literal gap between where they are and the next level ("L2→L3 differential").
2. **Show what the harvest already proves** — the strength-3 Tier-A atoms from the evidence map.
3. **Ask targeted gap questions** only where evidence is thin or the rubric needs human context the data can't supply. Use `AskUserQuestion`. Examples generated from the gap:
   - "L3 Code Architecture wants an *owned module*. The harvest shows the data-migrations plugin PRs — were you the sole owner? Anyone else commit design?"
   - "Mentorship L_target wants you helping others — who did you onboard/unblock this cycle, and is there a PR/Slack thread?"
4. **Chase the unproven brief claims.** For every claim in `00_user_brief.md` the harvest couldn't link to an artifact, ask the user for the proof: "You mentioned [the X migration / unblocking Y] — is there a PR, ticket, or Slack thread I can cite?" A claim with no artifact can't anchor a rubric line.
5. **Always ask about shoutouts** explicitly (people forget them; they're strength-3 by definition): "Any kudos/shoutouts this cycle — Slack, email, a manager mention? Paste links or names."
6. Fold the answers back into `10_evidence_map.md` as new atoms.

**Gate 3:** Confirm every level-up subcat now has enough evidence (or the user accepts holding it). Then Phase 4.

---

## Phase 4 — Draft answers

Walk subcats in weight-descending order. Slug = lowercase name with non-alphanumeric runs
→ `_` (e.g. `1162_self_discipline`). For each subcat:

**Step 0 — Resume / reuse check (do this BEFORE drafting):**
- If `$WORKDIR/answers/<id>_<slug>.html` already exists (a prior run's draft), **load and show it**, then ask keep / revise / redraft (`AskUserQuestion`). Never silently overwrite.
- Read the **full** previous-cycle answer from `$WORKDIR/answers/_prev/<id>_<slug>.html` (if present). This is last year's complete text — the drafter improves on it, never starts blind when a prior answer exists.

**Then branch on the subcat's status from `00_rubric_delta.md`:**

- **Level-up target** (current < target): draft an improved answer.
  1. Print the rubric delta (L_current vs L_target) + the atoms being used + the full `_prev` answer.
  2. **Write to the LITERAL target-level rubric phrase.** Quote the exact target sentence and
     make the answer satisfy *those words*, not the adjacent idea. Level definitions can be
     counterintuitive — on a real run, Breadth **L4** = "experience either on the frontend OR
     the backend with multiple (>2) frameworks" (depth on *one* side), while the both-sides
     framing is actually the **L3** definition; a draft written to "I do frontend AND backend"
     scores L3, not L4. Read the target phrase literally before drafting and again after.
  3. Draft with the **mandatory template** (`templates/answer_template.md`):
     > During [period/project], I [action], which [result]. This outcome aligns with [goal].
     - 2–4 paragraphs, varied lengths; each paragraph = one concrete atom + impact.
     - HTML (`<p>`, `<strong>`, `<a href>`, `<code>`, `<ul>`). Prefer bulleted `<ul>` when citing multiple PRs/repos — bullets are scannable evidence that save the auditor time.
     - **Hyperlink EVERY artifact, and name what each one did.** The auditor reads the answer, not your Drive — so every PR/doc/issue/shoutout goes inline as an `<a href>`, and for upstream/external PRs say *which problem each one solved* (e.g. "removed the `parsel` dependency that broke the XBlock on Sumac, resolving help-wanted issue #197"). A bare "I contributed to 5 repos" with two links is weaker than five named, linked, problem-described bullets. Two answers in a category with **zero links** stand out as the weakest — give every answer ≥2 inline links.
     - **De-jargon — write verbose, plain explanations, not insider shorthand.** An impartial auditor stumbles on un-explained internals. Explain the *what and why*, not the mechanism name: say "the same code runs across dev/stage/prod because it reads its database connections from config" — not "`plugin_settings()` injects 11 aliases into `settings.DATABASES` at load time". Define a term the first time ("idempotent: re-running skips data already written, so a cutover resumes safely"). Split any sentence over ~30 words.
     - **Don't recycle the same unlinked claim across answers**, and **don't carry forward unverifiable precise numbers** from `_prev`. A claim repeated verbatim in three answers with no link (real run: "X and Y consult me on LTI" appeared 3×) amplifies auditor doubt instead of reinforcing — link a shared claim **once** (or to its Drive screenshot) and vary the evidence per answer. If `_prev` asserts exact counts you can't re-verify this cycle ("43 sessions", "52 1:1s"), soften to a defensible range or cite the artifacts you *can* link. Trim unverifiable self-praise tails ("the VP replied 'Nice.'", "caught by me before anyone flagged it") — they read as padding.
     - Cite **Tier A** links inline. Tier B/C (private DMs, IDE/Claude/Cursor sessions, calendar headcount, git terminal) can't be public-linked → reference them with the single `DRIVE_FOLDER_URL` placeholder + an `SS-NN` code (see the Drive section below), and the user swaps one URL at the end.
     - **VOICE:** drop banned words (leverage, utilize, robust, seamlessly, transformative, furthermore, moreover, proven track record, …). No Oxford comma. Don't open with "I am writing to…". Be confident and technical; surface architecture decisions, scale numbers, production impact. **Never admit weakness** (auditors score against the rubric).
- **MUST-FILL** (no `_prev` file, e.g. a brand-new subcategory): draft from scratch with the same template + atoms. If the subcat is genuinely not applicable (e.g. a mobile-dev criterion for a backend engineer), ask the user before writing — they may want to leave it blank.
- **Hold** (already at/above target, not being raised): **carry the `_prev` answer forward** so it isn't lost (see policy note below). Offer a light refresh — fold in any new strength-3 atom from this cycle — but keep the substance. Default action: reuse `_prev` verbatim unless the user wants the refresh.
- **`hold_redraft`** (keep the level, rewrite fresh): the user wants the same level but a new answer built on this cycle's evidence — draft it like a level-up target (template + atoms + hyperlinks), just aimed at holding the current level rather than raising it. Don't reuse `_prev` verbatim.

3. Show the draft (or the carried-forward text). **Wait for confirmation** (unless the user said "draft all, I'll review at the end").
4. On approval, save to `$WORKDIR/answers/<id>_<slug>.html`.

> **Hold-subcat carry-forward policy.** Default = re-submit last year's answer for hold
> subcats, because we don't assume Sophia retains an answer you don't re-submit in a new
> cycle. If you've confirmed the platform keeps prior answers for untouched subcats, you can
> skip holds instead — set that decision at Gate 4 and note it in `.sophia/config.json`
> (`"resubmit_holds": false`).

### Drive evidence — ONE flat folder, and proof lives IN the answer

The auditor reads the **answer**, never your Drive. So the goal is to put as much proof as
possible *inline as public hyperlinks*, and use Drive only for what genuinely can't be linked.
**Do not build per-subcategory Drive folders** (over-engineered — a real run found nobody
opens 23 subfolders). Instead:

- Maintain **one** flat folder `$WORKDIR/drive_evidence/` with a `_INDEX.md` screenshot
  checklist. Each row = an `SS-NN` code, what to capture, the source to screenshot from (e.g.
  the Slack DM URL), and which answers reference it.
- Only these go to Drive (un-hyperlinkable): **private Slack DMs, Claude/Cursor session
  transcripts, the calendar event's guest headcount, a git terminal showing rebase/stash**.
  Everything else (PRs, docs, public Slack shoutout permalinks, GitHub `reviewed-by:` search)
  is linked inline and needs **no** screenshot.
- In answers, reference a screenshot as `<a href="DRIVE_FOLDER_URL">… (SS-NN)</a>`. The user
  uploads the one folder, shares its URL, and you do a **single global replace** of
  `DRIVE_FOLDER_URL` across `answers/*.html`. The `SS-NN` in the link text tells the auditor
  which file to open.

**Gate 4:** Every subcat is either drafted/approved (level-up + MUST-FILL), carried-forward (hold), or explicitly skipped. Then Phase 4.5.

---

## Phase 4.5 — Unbiased auditor pass (do this BEFORE submitting)

Drafts written by the same context that gathered the evidence are biased — they read as
complete to their author and hide jargon, over-claims and rubric-fit misses. **Spawn one
impartial auditor subagent** (`Agent`, opus, fresh context) that has NOT seen the harvest, and
have it score the drafts like a real Sophia auditor who *lowers* scores for vague,
unsupported, or confusingly-written claims. Give it only: the rubric file
(`evidence/00_rubric_delta.md`) and the answer files with their target levels. Ask for, per
answer: **verdict** (CLEARS / BORDERLINE / FALLS SHORT vs the target), **rubric-fit** (does the
text satisfy the *literal* target phrase?), **clarity problems** (quote jargon/mumbo-jumbo a
non-author would stumble on), **unsupported claims** (asserted numbers with no link), **the one
evidence gap to close**, and **cross-cutting issues** (recycled claims, asserted precision,
link-less answers, unverifiable self-praise).

This pass caught real, material defects on its run: an L4 answer written to the wrong rubric
phrase, the same unlinked claim recycled across three answers, two answers with zero links, and
several run-on jargon sentences. Fold its feedback back into the drafts, then re-run it if the
changes were large. Only then go to Phase 5.

---

## Phase 5 — Submit & verify

Submit **every approved file in `answers/`** (level-up + MUST-FILL + carried-forward holds
unless `resubmit_holds` is false) — `<id>` is the leading number in each filename. Exclude
the `answers/_prev/` reference dir. **Never hand-roll curl.** One subcat at a time:

```bash
python3 "$SKILL_DIR/helpers/submit_answer.py" <category_id> \
  "$WORKDIR/answers/<id>_<slug>.html" --workdir "$WORKDIR"
```

Reads UCF id from `.sophia/config.json`, token + auto-refresh via `sophia_auth`. POSTs, then
GETs the framework and asserts the stored `assessment_comments` length > 0 (Sophia silently
drops some malformed payloads — the verify step catches it). Exit 0 = stored & verified.

Show a dry-run (list the `answers/*.html` files + html lengths, `_prev/` excluded) and get an
explicit "submit" before sending.

**Before submitting:** grep the `answers/*.html` for a leftover `DRIVE_FOLDER_URL` placeholder.
If any remain, the user hasn't shared the Drive folder yet — get the URL and do the global
replace first, or those links submit broken.

**Final validation pass** after all submissions:
1. Re-fetch the framework (`sophia_api.py --workdir "$WORKDIR"`).
2. Assert **every subcat you submitted** has non-empty stored `assessment_comments` (catches silent drops).
3. Cross-check each stored answer has ≥2 Tier-A artifact links and follows the template.
4. Report a table: subcat | status (level-up / must-fill / hold) | submitted? | stored len | artifact count.

---

## Phase 6 — Skill maintenance

After a real run, fold learnings back here: new working/broken API payload shapes, the
verified refresh-exchange shape (0.5), new calendar noise-drop patterns, sparse-month
calibration. Bump the changelog.

---

## Constraints

- **GitHub**: `gh` CLI only — never the GitHub MCP.
- **Slack**: `mcp__claude_ai_Slack__*` only.
- **Tracker (Plane/Jira/…)**: call your own tracker MCP directly (MCP unavailable inside
  opencode subagents). The reference setup uses Arbisoft's Plane (`mcp__plane-arbisoft__*`);
  other users substitute their MCP name and add it to this skill's `allowed-tools` (or accept a
  one-time permission prompt). Host/workspace come from `plane_host`/`plane_workspace_slug` in
  config — not hardcoded.
- **delegate / opencode**: provider+model per the `delegate` skill; pass `directory` = the workspace root, not a subfolder; strip `<think>…</think>`; batch ≤10.
- **Tokens/secrets**: refresh + access tokens live only in `$WORKDIR/.sophia/` (chmod 600, gitignored) or env vars. Never paste a token into chat, never commit one, never log one in full.
- **Sub-agents**: summaries only — never read a harvest agent's full file into context.
- **Commits**: never add a `Co-Authored-By: Claude` / AI co-author trailer.
- **Honesty**: confident and rubric-aligned, but every cited atom must be real.

## Changelog

| Version | Date | Delta |
|---------|------|-------|
| v1.6 | 2026-06-03 | Folded in lessons from a full real run. **New Phase 4.5 — unbiased auditor pass**: a fresh-context opus subagent scores the drafts against the rubric and flags jargon / unsupported claims / rubric-fit misses before submit (caught an L4 answer written to the wrong rubric phrase, recycled unlinked claims, link-less answers). **New harvest Agent K — code-artifact deep-dives**: background sonnet agents read the user's flagship local repos + PRs and return scale/architecture/security/rubric-mapped evidence (turns "I own the plugin" into "21k LOC, 15 commands, 346 tables, 12 tenants"). **Drive simplified to ONE flat folder** (`drive_evidence/` + `_INDEX.md` SS-codes) — proof lives inline in answers as hyperlinks; only un-linkable DMs/sessions/headcount/git-terminal get a screenshot, referenced via a single `DRIVE_FOLDER_URL` placeholder swapped at the end. **Drafting rules hardened**: write to the *literal* target rubric phrase (level defs can be counterintuitive); hyperlink every artifact and name the problem each solved; de-jargon into plain verbose prose; never recycle the same unlinked claim across answers or carry forward unverifiable precise counts; trim self-praise tails. **Gate 2 re-decides targets UP too** (Mentorship L1→L3, Core Values L2→L3 when evidence exceeds the plan). **Plane/Calendar harvest quirks documented**: filtered `list_work_items`→403 (use plain list + client filter or REST PAT; MCP drops cursor; control-char JSON needs python `strict=False`; curl for self-hosted TLS); calendar `fullText` caps ~50 and can't give reliable 1:1 counts → use headline events + headcounts. **Re-check MCP availability at Phase 1** (deferred MCPs come online mid-session). New `hold_redraft` decision; Core Values needs the org values doc. |
| v1.5 | 2026-06-02 | New **Phase 0.6 — user achievements brief**: the user brain-dumps their own critical work / proud work / people helped before harvest, captured verbatim to `evidence/00_user_brief.md`. It steers the harvest and its claims become atoms Phase 2 must back with artifacts (unproven ones → Phase 3 questions). **Multi-tracker harvest**: trackers are no longer assumed to be a single Plane board — Phase 0.4 asks the user to link *all* relevant boards across *all* tools (Plane / Jira / GitHub Projects / other), stored as lists (`plane_projects`, `jira_boards`, `github_project_boards`, `other_trackers`); agent D loops every board across every tool into `d_tracker_tickets.md`. `progress.py` tracks the brief milestone. |
| v1.4 | 2026-06-02 | Realistic targets, not blanket +1: `rubric_delta.py` proposes `raise` (≤L2→next), `stretch` (L3→L4, held by default, evidence-gated at Gate 2), `fill`/`baseline`. Self-explanatory **Action** column + default-plan summary line. Gate 0 is now an explicit **self-evaluation**: user sets the target level per subcat (by name), persisted to `.sophia/targets.json`; every downstream phase reads it. |
| v1.3 | 2026-06-02 | Resumable across chats: `progress.py` inspects the workdir (✅/⬜ milestones) and prints `RESUME AT:`; new Phase 0.0 runs it first and jumps to the right phase without re-asking. Gates write `.sophia/progress.json` markers. |
| v1.2 | 2026-06-02 | Existing answers no longer ignored. `prev_answers.py` dumps each subcat's FULL last-cycle answer to `answers/_prev/`; Phase 4 reads it so the drafter improves on the complete prior text (not the 600-char snippet). Resume guard: existing `answers/<id>_<slug>.html` is loaded + keep/revise/redraft, never silently overwritten. Hold-subcat carry-forward (default `resubmit_holds=true`) so untouched subcats don't blank out; Phase 5 submits all approved files in `answers/` (excl. `_prev/`). |
| v1.1 | 2026-06-02 | Slimmer onboarding: only the refresh-token cookie + UCF id are asked. Auto-discover sophia_user_id (decoded from refresh-token JWT via `sophia_auth.py userid`), github_username (`gh api user`), framework_name/due_date/auditor (from fetched JSON), cycle dates (default 12mo), Cursor path (auto-detect). Workdir hardcoded to `~/Documents/sophia-review`. Slack/Calendar/shoutouts/tracker reframed as optional enrichment; shoutouts need only message URLs. GitHub uses `gh auth status` (prompt `gh auth login` if needed). |
| v1 (repo) | 2026-06-02 | Publishable, generalized rewrite for ai-agent-skills. Phased interactive chat; refresh-token bootstrap auth (`sophia_auth.py`); per-user `config.json`; `sophia_api.py` data fetch; `rubric_delta.py` + `coverage_audit.py`; MCP preflight + delegate offer; discovery/differential + targeted-question phase; background harvest agents; submit + final validation. Derived from the internal `sophia-review` v3 + Revision-2 plan. |
