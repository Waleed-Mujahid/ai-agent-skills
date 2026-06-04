---
description: >-
  Delegate grunt work to opencode (free LiteLLM/zen models) instead of spending Claude tokens.
  Use this whenever a task is high-token but low-reasoning — code review of a PR/branch/diff,
  "where is X / how does Y work" codebase search, file/symbol hunting, test generation,
  refactoring, formatting, git log/diff analysis, running tests, or any multi-file exploration.
  Reach for this even when the user doesn't say "delegate": if you're about to grep a large tree,
  read many files to answer a search question, or review a diff, route it here first. Do NOT use
  for reasoning, architecture decisions, security calls, user-facing writing, or work needing
  Plane/Slack MCP — those stay on the main model.
allowed-tools: mcp__opencode__opencode_health, mcp__opencode__opencode_fire, mcp__opencode__opencode_wait, mcp__opencode__opencode_check, mcp__opencode__opencode_review_changes, mcp__opencode__opencode_ask, mcp__opencode__opencode_permission_list, mcp__opencode__opencode_session_permission, mcp__opencode__opencode_command_execute, Bash
---

# Delegate to opencode

Dispatch a task to an opencode worker running free models. opencode compute = $0 (free key). The
only cost is Claude reading the result back as input tokens — so the whole game is **minimize what
comes back**. Push reasoning down to the worker, pull back a tight structured answer.

## Task
$ARGUMENTS

## Should this be delegated?

Delegate when the task is **high-token, low-reasoning** — the worker does the grinding, you read a
summary:

- Code review (PR / branch / commit / uncommitted diff)
- Codebase search — "where is X", "how does Y work", find files/symbols/usages
- Test generation, refactoring, formatting, docstrings
- Git/`gh` log & diff analysis, running tests
- Multi-step exploration or impact analysis across many files

Keep on the main model (do **not** delegate): architecture/design decisions, security judgments,
user-facing writing (PR descriptions, comments, Plane/Slack messages), anything needing MCP tools
the worker lacks, and GitHub *write* ops. When in doubt about reasoning quality, keep it.

If the user already gave you the exact file path, just `Read` it — delegation is for open-ended or
bulky work, not a single known-file lookup.

## Step 0: Make sure the server is up (best-effort — never let this block)

Firing before the server is ready is a common dispatch failure, so try to confirm it first. But this
check is **best-effort, not a gate**: if `opencode_health` is unavailable or its permission is denied,
do **not** stop — just proceed to dispatch. A dead server makes `opencode_fire` fail fast and clearly,
so the dispatch itself is the real health signal. (An over-strict "must pass health first" rule caused
total failures in testing when the health call was denied — don't reintroduce it.)

Order of preference, stopping at the first that works:
1. Call `opencode_health`. Healthy → continue to Step 1.
2. If that tool is denied/unavailable, probe via Bash: `curl -fsS http://127.0.0.1:4096/app`.
3. If neither is available to you, **skip straight to Step 1 and just fire** — let the dispatch tell you.

Only if you have positive evidence the server is **down** (health errored *or* curl refused the
connection), start it and wait until it answers:

```bash
pgrep -f "opencode serve" >/dev/null 2>&1 || (nohup opencode serve --port 4096 >/tmp/opencode-serve.log 2>&1 &)
for i in $(seq 1 20); do
  curl -fsS http://127.0.0.1:4096/app >/dev/null 2>&1 && { echo "opencode ready"; break; }
  sleep 1
done
```

If the server is confirmed down and won't start (tail `/tmp/opencode-serve.log`), report the error and
STOP — do not do the task manually. But never STOP merely because the *health check* was denied.

## Step 1: Route — pick agent + command

opencode has specialized agents and built-in commands that beat a raw prompt. Classify first.

| Task shape | Route | Agent / command | Model tier |
|------------|-------|-----------------|------------|
| Review a diff/PR/branch/commit | **A** | `/review` command | Code |
| "Find X" / "where is Y" / "how does Z work" | **B** | `explore` agent | Simple |
| 2+ independent subtasks (parallelizable) | **C** | `general` agent | Complex |
| Planning / impact / architecture (read-only) | **D** | `plan` agent | Complex |
| Everything else (code gen, refactor, tests) | **E** | `build` agent | by tier |

### Route A — `/review` (code review)
Built-in optimized review workflow; better than a hand-written review prompt. Set the model on the
`opencode_fire` call; the command runs in that session and **inherits its model**. Do **not** pass
`providerID`/`modelID` to `opencode_command_execute` — the endpoint rejects them with a 400.
```
sid = opencode_fire(prompt="placeholder", directory=<project_dir>, providerID="opencode", modelID="deepseek-v4-flash-free")
opencode_command_execute(sessionId=sid, command="review",
  arguments="<target>")   # "" = uncommitted | "commit abc123" | "branch feature-x" | "pr owner/repo#123"
```

### Route B — `explore` agent (search)
```
opencode_fire(prompt="<search task>", agent="explore", directory=<project_dir>,
  providerID="opencode", modelID="deepseek-v4-flash-free", title="search: <topic>")
```
Set depth in the prompt: "quick search for…" vs "thorough analysis of…".

### Route C — `general` agent (multi-step / parallel)
```
opencode_fire(prompt="<multi-step task>", agent="general", directory=<project_dir>,
  providerID="litellm", modelID="groq/qwen/qwen3-32b", title="analysis: <topic>")
```

### Route D — `plan` agent (read-only planning)
Edit tools disabled → guaranteed no writes. Safe for analysis.
```
opencode_fire(prompt="<planning task>", agent="plan", directory=<project_dir>,
  providerID="litellm", modelID="groq/qwen/qwen3-32b", title="plan: <topic>")
```

### Route E — `build` agent (default)
```
opencode_fire(prompt="<task>", agent="build", directory=<project_dir>,
  providerID=<tier>, modelID=<tier>, title="<topic>")
```

## Step 2: Select model

Confirm the model exists before relying on it — the free roster changes. List with
`opencode_provider_models(providerId="opencode")` if a dispatch returns empty.

| Tier | Use case | providerID | modelID |
|------|----------|------------|---------|
| Simple / Medium / Code | search, review, refactor, tests, docs, code gen | `opencode` | `deepseek-v4-flash-free` |
| Code (alt) | if deepseek is empty/slow | `opencode` | `minimax-m3-free` |
| Easy reasoning | trace a flow, "are these two consistent", what does this branch do | `litellm` | `groq/qwen/qwen3-32b` |
| Complex | architecture, multi-file analysis, hard bugs | `litellm` | `groq/qwen/qwen3-32b` |
| Complex (fallback) | if qwen3-32b fails/empty | `litellm` | `groq/llama-3.3-70b-versatile` |

`qwen3-32b` is the only free model with usable light-reasoning (it has a thinking mode); `llama-3.3-70b`
is a weaker single-hop fallback. The flash/coding models (`deepseek-v4-flash`, `minimax-m3`) are
pattern-matchers — they hallucinate on anything multi-step, so keep them to search/extract/format.
This "easy reasoning" tier is the gray zone of the never-delegate-reasoning rule: *mechanical-with-a-
little-thinking* goes to qwen3; if a wrong answer is costly (architecture, security, "should we"), keep
it on the main model.

Other live `opencode` free models (verify before use): `mimo-v2.5-free`, `nemotron-3-super-free`,
`big-pickle`.

**Dead — do not use:** `opencode/minimax-m2.5-free` (replaced by `minimax-m3-free`),
`litellm/groq/openai/gpt-oss-120b` (empty), `litellm/groq/meta-llama/llama-4-scout-17b-16e-instruct`
(empty), `litellm/cerebras/*` (payment lapsed).

## Step 3: Craft the prompt (Routes B–E; skip for A)

Always prepend this preamble, then append the task:

```
You are a worker agent. Your output is consumed by an orchestrating AI that pays per input token.

Read any project instruction files present in the working directory before starting:
CLAUDE.md, AGENTS.md, GEMINI.md, .cursorrules, .cursor/rules/*.mdc, .github/copilot-instructions.md

You have read-only `gh` and `git`: gh pr/issue view|list|diff|checks, gh api (GET only),
git diff|log|show|status|branch. Use them freely.

GROUND YOUR ANSWER IN THE ACTUAL CODE: open and read every file the task references this session —
do not answer from prior knowledge or guesses about what a file "probably" contains. If you could not
open a file, say so explicitly rather than fabricating its contents.

OUTPUT FORMAT (mandatory):
<answer>
RESULT: [one-line conclusion]
DETAILS:
- [bullet, max 5]
FILES: [affected files, or "none"]
</answer>

RULES:
- All reasoning/thinking goes BEFORE the <answer> tag.
- Inside <answer>: only the structured answer, under 200 words.
- No greetings, no "let me…", no preamble, no trailing summary.
---
TASK:
```

Include absolute paths for any files the task references.

## Step 4: Dispatch — token-efficient pattern

`<project_dir>` = the current Claude session's project root. **Never** pass a subfolder — that
disorients the worker and returns empty. Put subfolder paths in the prompt text instead.

- **Never `opencode_run`** (returns full reasoning) and **never `opencode_conversation`** (full
  history). Both blow the input-token budget.

**Routes B–E:**
1. `opencode_fire` → session ID (~50 tokens). Tell the user the session ID immediately.
2. `opencode_wait(sessionId, timeout=180)` → blocks until done (one call, no polling loop).
3. While waiting / between retries → run Step 5 (permission triage).
4. `opencode_check(sessionId, detailed=true)` → fetch the final message only after wait completes.

**Route A:** `opencode_fire` (minimal prompt) → `opencode_command_execute(...)` → `opencode_wait` →
triage between retries.

**Never fall back to doing it yourself.** On timeout/empty: retry once with the alt model, then
report the session ID and STOP.

## Step 5: Permission triage

Workers pause for permission. Approve safe ops fast, escalate the rest. Check with
`opencode_permission_list(directory=<project_dir>)`, then reply via
`opencode_session_permission(id, permissionID, reply=...)` — `"always"` for safe patterns (so the
worker stops re-asking), `"once"` for one-offs, `"reject"` to deny.

**Auto-approve (`"always"`) — read-only / non-destructive:**
- git: `status`, `diff`, `log`, `show`, `branch`, `remote`
- gh (reads): `pr view|list|diff|checks|status`, `issue view|list`, `run view|list`, `api repos/…` (GET — no `-X POST/PUT/DELETE/PATCH`)
- fs/inspect: `ls`, `find`, `cat`, `head`, `tail`, `wc`, `sort`, `uniq`, `grep`
- read-only exec: `python3 -c …`, `pip show|list`
- tests: `pytest`, `make test|lint|check`, `docker exec … pytest …`
- tools: `read`, `glob`, `grep`, `webfetch`, `todowrite`, `skill`

**Escalate to the user (quote the exact command, then wait):**
- `write` / `edit` tools (any file mutation)
- destructive bash: `rm`, `git push|reset|checkout --|clean`
- write ops: `gh pr create|merge|close`, `gh issue create`, `curl -X POST/PUT/DELETE`
- installs: `pip install`, `npm install`, `brew install`
- `task` tool (sub-agents), or anything you're unsure about

Escalation line: ``opencode wants to run: `<command>`. Approve? (always / once / reject)``

## Step 6: Handle the response

1. From `opencode_check(detailed=true)`, extract the `<answer>` block.
2. Found → report to the user in ≤3 sentences.
3. No tags → grab the `RESULT:` line. Still nothing → report the gist briefly.
4. Status `pending` (permission wait) → go to Step 5.
5. Timeout/empty after one retry → report session ID for TUI tracking, STOP.

## Step 7: Code changes

If the worker edited files, call `opencode_review_changes(sessionId)` and summarize the diff — don't
echo raw diffs unless asked.

## Anti-patterns
- Never `opencode_run` / `opencode_conversation` — token blowout.
- Never do the task yourself when opencode fails — report the session ID and stop.
- Never pass a subfolder as `directory` — use the project root.
- Never delegate reasoning, architecture, security, or user-facing writing.
- Never auto-approve write/edit/destructive bash — escalate.
- Don't escape backticks with `\` in heredocs — use raw backticks.
