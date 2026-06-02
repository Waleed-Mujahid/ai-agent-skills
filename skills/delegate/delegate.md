---
description: Delegate task to opencode (free models via LiteLLM) — saves Claude tokens
allowed-tools: mcp__opencode__opencode_fire, mcp__opencode__opencode_wait, mcp__opencode__opencode_check, mcp__opencode__opencode_review_changes, mcp__opencode__opencode_ask, mcp__opencode__opencode_permission_list, mcp__opencode__opencode_session_permission, mcp__opencode__opencode_command_execute, Bash
---

# Delegate to opencode

Dispatch task to opencode worker running free models via LiteLLM. opencode cost = $0 (free API key). Only cost = Claude reading the result as input tokens. Therefore: minimize what comes back.

## Task
$ARGUMENTS

## Step 0: Ensure opencode Server Running

Before dispatching, verify opencode server is up:

```bash
pgrep -f "opencode serve" > /dev/null 2>&1 || (opencode serve --port 4096 &) && sleep 3
```

If `opencode_fire` returns a connection error, run the above in background shell and retry.

## Step 1: Route — Pick the Right Agent + Command

First, classify the task and pick the optimal dispatch method. opencode has specialized agents and built-in commands that outperform raw prompts.

### Route A: `/review` command — Code Review Tasks
**Use when:** reviewing diffs, PRs, commits, uncommitted changes
**Why:** Built-in optimized review workflow. Better than crafting a manual review prompt.

```
# First fire a session to get sessionId
opencode_fire(prompt="placeholder", directory=<project_dir>, providerID=..., modelID=...)

# Then execute /review command in that session
opencode_command_execute(
    sessionId="ses_xxx",
    command="review",
    arguments="<target>",    # "pr owner/repo#123" | "branch feat-x" | "" (uncommitted)
    providerID="opencode",
    modelID="deepseek-v4-flash-free"
)
```

Targets for `/review`:
- `""` (empty) — reviews uncommitted changes
- `commit abc123` — reviews specific commit
- `branch feature-x` — reviews branch diff vs main
- `pr owner/repo#123` — reviews a pull request

### Route B: `explore` agent — Codebase Search
**Use when:** finding files, searching code, answering "where is X?" or "how does Y work?"
**Why:** Specialized search agent — faster and more targeted than `build` agent doing grep.

```
opencode_fire(
    prompt="<search task>",
    agent="explore",
    directory=<project_dir>,
    providerID="opencode",
    modelID="deepseek-v4-flash-free",
    title="search: <topic>"
)
```

Specify thoroughness in prompt: "quick search for...", "thorough analysis of..."

### Route C: `general` agent — Multi-Step / Parallel Tasks
**Use when:** task has multiple independent subtasks that can run in parallel
**Why:** `general` agent can parallelize internally — one session does work of many.

```
opencode_fire(
    prompt="<multi-step task>",
    agent="general",
    directory=<project_dir>,
    providerID="litellm",
    modelID="groq/qwen/qwen3-32b",
    title="analysis: <topic>"
)
```

### Route D: `plan` agent — Planning / Architecture (Read-Only)
**Use when:** need a plan, architecture analysis, or impact assessment. No edits needed.
**Why:** `plan` agent has edit tools disabled — guaranteed read-only. Safe for analysis.

```
opencode_fire(
    prompt="<planning task>",
    agent="plan",
    directory=<project_dir>,
    providerID="litellm",
    modelID="groq/qwen/qwen3-32b",
    title="plan: <topic>"
)
```

### Route E: `build` agent — General Tasks (Default)
**Use when:** none of the above fit. Standard code gen, refactoring, test writing.

```
opencode_fire(
    prompt="<task>",
    agent="build",
    directory=<project_dir>,
    providerID=<from model tier table>,
    modelID=<from model tier table>,
    title="<topic>"
)
```

### Decision Tree

```
Task is code review?
  → Route A: /review command + deepseek-v4-flash-free

Task is "find X" / "where is Y" / "how does Z work"?
  → Route B: explore agent + deepseek-v4-flash-free

Task has 2+ independent subtasks?
  → Route C: general agent + groq/qwen/qwen3-32b

Task is planning / impact analysis / architecture?
  → Route D: plan agent + groq/qwen/qwen3-32b

Everything else?
  → Route E: build agent + model from tier table
```

## Step 2: Select Model

| Complexity | Use Case | providerID | modelID |
|------------|----------|------------|---------|
| Simple | grep, search, list files, format | `opencode` | `deepseek-v4-flash-free` |
| Medium | review, refactor, test gen, docs | `opencode` | `deepseek-v4-flash-free` |
| Code-heavy | code gen, code review, debug | `opencode` | `deepseek-v4-flash-free` |
| Complex | architecture, multi-file analysis, hard bugs | `litellm` | `groq/qwen/qwen3-32b` |
| Complex fallback | if qwen3-32b fails/empty | `litellm` | `groq/llama-3.3-70b-versatile` |

**Dead models (do not use):**
- `opencode/minimax-m2.5-free` — no longer available (replaced by m3)
- `litellm/groq/openai/gpt-oss-120b` — returns empty
- `litellm/groq/meta-llama/llama-4-scout-17b-16e-instruct` — returns empty
- `litellm/cerebras/*` — inaccessible (payment lapsed)

## Step 3: Craft Prompt (for Routes B-E)

Skip this for Route A (`/review`) — it has its own prompt.

ALWAYS prepend this preamble:

```
You are a worker agent. Your output is consumed by an orchestrating AI that pays per input token.

Before starting, read any project instruction files that exist in the working directory:
- CLAUDE.md
- AGENTS.md
- GEMINI.md
- .cursorrules
- .cursor/rules/ (any .mdc files)
- .github/copilot-instructions.md

You have access to `gh` CLI for GitHub operations (read-only). Use it freely for:
- gh pr view, gh pr diff, gh pr list, gh pr checks
- gh issue view, gh issue list
- gh api (GET requests only)
- git diff, git log, git show, git status, git branch

OUTPUT FORMAT (mandatory):
<answer>
RESULT: [one-line conclusion]
DETAILS:
- [bullet 1]
- [bullet 2, max 5 bullets]
FILES: [affected files, or "none"]
</answer>

CRITICAL RULES:
- Put ALL reasoning/thinking BEFORE the <answer> tag
- Put ONLY the final structured answer inside <answer> tags
- The <answer> section must be under 200 words
- No greetings, no preamble, no "let me...", no summaries
---
TASK:
```

Then append the actual task. If the task references specific files, include their absolute paths.

## Step 4: Dispatch

`<project_dir>` = the current working directory of the Claude Code session (the project root Claude is running in).

ALWAYS use these fixed params:
- `directory`: `<project_dir>` — the current Claude session working directory
- `providerID`: from Step 2
- `modelID`: from Step 2
- `title`: short descriptive title (for TUI tracking)

### CRITICAL: Token-Efficient Pattern

**NEVER use `opencode_run`** — returns full reasoning, wastes input tokens.

**For Routes B-E — fire + wait pattern:**

1. **`opencode_fire`** → session ID (~50 tokens). Tell user the session ID immediately.
2. **`opencode_wait(sessionId, timeout=180)`** → blocks until done (single call, no polling loop)
3. Between wait retries, run **Step 5 (Permission Triage)**
4. **`opencode_check(sessionId, detailed=true)`** → fetch last message only after wait completes

**For Route A — command execute pattern:**

1. **`opencode_fire`** with minimal prompt → session ID
2. **`opencode_command_execute(sessionId, command="review", arguments=...)`**
3. **`opencode_wait(sessionId, timeout=180)`** → blocks until done
4. Between wait retries, run **Step 5 (Permission Triage)**

**CRITICAL: Never fall back.** If opencode times out or returns empty — retry once with a different model, then report the session ID to the user and STOP. Do NOT do the task manually under any circumstances.

## Step 5: Permission Triage

After firing and between wait retries, call:
```
opencode_permission_list(directory=<project_dir>)
```

### AUTO-APPROVE (reply: "always"):

**Safe bash commands** (pattern match):
- `git status`, `git diff`, `git log`, `git show`, `git branch`, `git remote`
- `gh pr view`, `gh pr list`, `gh pr diff`, `gh pr checks`, `gh pr status`
- `gh issue view`, `gh issue list`
- `gh api repos/` (GET — no `-X POST/PUT/DELETE/PATCH`)
- `gh run view`, `gh run list`
- `ls`, `find`, `cat`, `head`, `tail`, `wc`, `sort`, `uniq`
- `python3 -c` (read-only)
- `pip show`, `pip list`, `pip3 show`
- `pytest`, `make test`, `make lint`, `make check`
- `docker exec ... pytest ...` (container test runs)

**Safe tools**: `read`, `glob`, `grep`, `webfetch`, `todowrite`, `skill`

### ESCALATE TO USER:

- `write` or `edit` tool
- `bash` with: `rm`, `git push`, `git reset`, `git checkout --`, `git clean`
- `bash` with: `gh pr create`, `gh pr merge`, `gh pr close`, `gh issue create`
- `bash` with: `pip install`, `npm install`, `brew install`
- `bash` with: `curl -X POST/PUT/DELETE`
- `task` tool (sub-agents)
- Anything uncertain

**How to escalate:** Tell user: "opencode wants to run: `<command>`. Approve?"
Then `opencode_session_permission(id, permissionID, reply=<user's answer>)`

Use `"always"` for safe patterns, `"once"` for one-offs, `"reject"` for denials.

## Step 6: Handle Response

1. From `opencode_check(detailed: true)`, look for `<answer>` tags
2. If found: extract, report to user in ≤3 sentences
3. If not: scan for RESULT line
4. If neither: report gist briefly
5. If status = "pending" (permission wait): go to Step 5
6. On timeout: report session ID for TUI tracking, STOP — do not do the task manually

## Step 7: For Code Changes

If opencode made file changes, call `opencode_review_changes(sessionId)` for diffs. Summarize, don't echo raw diffs unless asked.

## Anti-patterns (DO NOT)
- **NEVER `opencode_run`** — returns full reasoning
- **NEVER `opencode_conversation`** — full message history
- **NEVER do the task yourself if opencode fails** — report session ID and stop
- **NEVER pass a subfolder as `directory`** — always use the project root. Put subfolder paths in the prompt text instead.
- Do NOT delegate reasoning/architecture decisions — use the main model directly
- Do NOT auto-approve write/edit/destructive bash — escalate
- Do NOT escape backticks with `\` in heredoc strings — use raw backticks directly
