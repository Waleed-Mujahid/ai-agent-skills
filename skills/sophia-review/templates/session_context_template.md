# Sophia Competency Self-Review — Context

> Per-run context file. The skill writes this into `<workdir>/CLAUDE.md` at Phase 0 so
> any resumed session has the facts. Replace every `<...>`.

## Goal
Improve <NAME>'s self-review answers on Sophia for the <CYCLE_YEAR> cycle.
Every answer rewritten with the mandatory template. Aim: move each targeted
subcategory up one level per the rubric.

## User
- **Name**: <full name>
- **Email**: <email>
- **Sophia User ID**: <sophia_user_id>
- **Framework**: <framework_name>
- **User Competency Framework ID**: <user_competency_framework_id>
- **Draft Evaluation ID**: <draft_eval_id>
- **Due Date**: <due_date>
- **Primary Auditor**: <auditor email>
- **Current Score**: <score> → <level / sub-level>

## Answer Template (MANDATORY for all answers)
> During [time period or project name], I [describe your key action or contribution], which [explain the result, improvement, or impact]. This outcome aligns with [specific competency area, organizational goal, or personal development objective].

2–4 paragraphs. Each paragraph = one concrete example. Every statement needs a
specific project, outcome, or artifact (PR link, metric, ticket). No vague claims.

## Sophia data files (fetched by `helpers/sophia_api.py`)
| File | Purpose |
|------|---------|
| `framework_details.json` | THE core file. Full rubric (L1–L5) + last year's answers per subcategory. |
| `progress_overview.json` | Draft eval state, current selections. |
| `summary_dashboard.json` | High-level dashboard, deadlines. |
| `person_competency_history.json` | Evidence history per criteria (last self-ratings). |

## Key data structure
- `framework_details.json → categories[].subcategories[].content_format.format_content.options[]` = rubric (rank 1–5).
- `…subcategories[].previous_selection.competency_choice_value` = last level (int).
- `…subcategories[].previous_selection.assessment_comments` = last year's answer (HTML).

## Evidence files (Phase 1 harvest → `evidence/`)
`a_github_*`, `b_github_upstream_*`, `c_github_reviews`, `d_plane_tickets`,
`e_slack_channels`, `f_slack_dms`, `g_claude_sessions`, `h_cursor_sessions`,
`i_calendar_meetings`, `j_shoutouts`, plus `00_rubric_delta.md`,
`10_evidence_map.md`, `11_ai_mentoring_map.md`.

## Auth
Access token bootstrapped from the browser `refresh-token` cookie via
`helpers/sophia_auth.py`. Refresh token in `<workdir>/.sophia/refresh_token`
(chmod 600, gitignored). Auto-refresh on 401.

## Submission
`python3 <skill>/helpers/submit_answer.py <category_id> answers/<id>_<slug>.html --workdir <workdir>`
Reads UCF id from `.sophia/config.json`. POSTs, then GETs framework and verifies
stored length > 0. Exit 0 on verified success.
