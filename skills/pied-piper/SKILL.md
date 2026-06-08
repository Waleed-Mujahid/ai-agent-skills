---
name: pied-piper
description: >-
  Gives Claude a free team of workers on arbisoft LiteLLM — including a browser. One-command
  setup turns pi.dev into a delegation backend that inherits THIS machine's Claude Code MCP
  servers and skills, then exposes interactive multi-turn workers (explore, debug, trace, exec,
  review, security, qa, playwright) Claude drives turn-by-turn via `pa <agent> <session> <msg>`.
  Run this whenever the user wants to install, set up, configure, repair, or re-sync "pied piper"
  or the pi delegation backend — or asks "why isn't pi working" or "set up pi". After setup,
  delegate grunt work (codebase search, flow tracing, diff review, refactors, browser automation)
  to free models so it never enters Claude's context — lighter, interactive successor to delegate.
trigger: /pied-piper
user_invocable: true
allowed-tools: Bash, Read, Edit
---

# pied-piper — free-model pi.dev delegation backend (arbisoft LiteLLM)

## What this does and why

pi.dev is a minimal headless coding agent (`pi -p "task"` runs, prints, exits — no
daemon, no TUI, no polling). On arbisoft's LiteLLM proxy it's an ideal **worker** for
high-token / low-reasoning grunt work. But pi ships bare — no MCP, no skills. This
skill closes that gap so pi reaches opencode-grade utility, and stays reusable for
anyone: it **inherits the user's existing Claude Code setup** instead of hardcoding
anything. Call `pi -p` directly from Bash — no intermediate Claude agents needed.
The expensive file-reading happens in pi on free models — those tokens never enter
a Claude context.

## API key

Setup reads `LIBRE_CHAT_API_KEY` from the environment. If unset, it prompts for the
key and saves it to `~/.zshrc`. The key is written as a reference (`"$LIBRE_CHAT_API_KEY"`)
in `~/.pi/agent/models.json` — pi expands it at runtime, so the same models.json
works on any machine as long as the env var is exported.

## Run it

The script is executable and safe to run directly — just invoke it via Bash:

```bash
~/.claude/skills/pied-piper/scripts/setup.sh
```

Optional flags: `--fast-model <id>`, `--reason-model <id>`, `--include-project`
(also bridge `./.mcp.json`), `--no-lsp`.

## What it does (no questions)

- **Provider** — fixed to `arbisoft-llm`; verifies pi can see it.
- **Models** — hardcoded tested pair written to `~/.pi/agent/piedpiper.env`:
  - `PIPER_FAST_MODEL=groq/qwen/qwen3-32b` (search, review — tool calling verified)
  - `PIPER_REASON_MODEL=groq/openai/gpt-oss-120b` (debug, build — reasoning verified)
  - Dead models (do NOT use): `groq/llama-3.1-8b-instant`, `groq/llama-3.3-70b-versatile`, `cerebras/*`
  - Override with `--fast-model` / `--reason-model`.
- **pi-mcp** (`@spences10/pi-mcp`) + optional **pi-lsp** installed.
- **MCP servers** — merged from `~/.claude.json`, plugin `.mcp.json` caches, and (with
  `--include-project`) `./.mcp.json`. Playwright added explicitly. The same MCP server
  tokens already in the Claude config get written to `~/.pi/agent/mcp.json`.
- **Skills** — `~/.claude/skills/` symlinked into `~/.pi/agent/skills/`.
- **CLAUDE.md rules** — injects `pi -p` direct-call block into `~/.claude/CLAUDE.md` if
  the block is not already present (idempotent). Replaces old agent-based block if found.

## Verify

The script ends by asking pi to **list its MCP tools** — if it names
Playwright/github/etc., the bridge works. Read that back to the user. Troubleshooting:
`references/troubleshooting.md`.

## Re-sync

Idempotent — re-run any time (after installing a new MCP/skill in Claude, or to
update the bridged MCP server list).

## Pi Agents — interactive workers Claude drives like OMC agents

One driver: `agents/piagent.sh` (shell fn `pa` after setup). Each worker keeps a **persistent pi session**, so Claude orchestrates it turn-by-turn — send a turn, read the reply, send the next. The worker retains full context across calls. Claude is the "person" on the other end. Zero Claude tokens; free models via arbisoft LiteLLM. No tmux panes / inbox files (OMC's mechanism) — state lives in pi's session store, keyed by `--session-id`.

```bash
pa <agent> <session> "<turn instruction>"          # session fn (after `source ~/.zshrc`)
~/.claude/skills/pied-piper/agents/piagent.sh ...   # or full path

# Interactive loop — Claude drives:
pa explore auth "find every caller of get_current_site in /repo"
pa explore auth "now narrow to the ones inside middleware"   # same worker, remembers turn 1
pa --list                                            # list active worker sessions
```

- `<session>` = any name. **Same name reuses the worker's context**; first call creates it.
- **Single turn == a one-shot. Multiple turns (same session) == an interactive worker.** No separate one-shot scripts.
- Persona is re-injected each turn (pi doesn't persist the system prompt); message history persists.

| Agent | Alias | Model | Tools | Use for |
|-------|-------|-------|-------|---------|
| `explore` | `ex` | fast | read/grep/find | find files, symbols, patterns |
| `debug` | `debugger` | reason | read/grep/find | root-cause analysis |
| `trace` | `tracer` | reason | read/grep/find | causal tracing, competing hypotheses |
| `exec` | `executor` | reason | read/grep/find/**edit/write** | minimal implementation |
| `review` | `reviewer` | fast | read/grep/find | severity-rated code review |
| `security` | `sec` | reason | read/grep/find | OWASP audit, secrets scan |
| `qa` | `tmux` | reason | read/bash | interactive CLI testing via tmux |
| `playwright` | `pw` | reason | playwright MCP | browser automation, UI testing |

**Playwright agent** omits `--no-extensions` (pi-mcp must load for playwright MCP). Browser opens visibly and persists across turns — drive a flow step by step.

## After setup

`pi -p` calls route through arbisoft LiteLLM via the rules injected into `~/.claude/CLAUDE.md`.
The next "find where X is" / "trace this flow" / "review this diff" / "refactor this" → call pi directly via Bash.

**Verified working call pattern (Bash timeout: 60s, synchronous):**
```bash
source ~/.pi/agent/piedpiper.env
pi -p "EXECUTE IMMEDIATELY. Use grep/search/read tools NOW — do NOT suggest, do NOT ask questions, do NOT speculate. Report ONLY evidence found: exact file paths, line numbers, code snippets. If nothing found, say so explicitly.

TASK: <task with absolute paths and exact symbol/pattern>

Output format: file:line — <code snippet>" \
  --provider "$PIPER_PROVIDER" --model "$PIPER_FAST_MODEL" \
  --mode text --tools "read,bash,grep,find,ls" \
  --no-extensions --no-skills
```

Key rules:
- No `--no-session` — sessions persist to pi.dev for continuation
- Use `--tools` allowlist (NOT `--exclude-tools`) — prevents extension tools hanging on init
- Do NOT use `run_in_background` in Bash tool — use synchronous call with `timeout: 60000`

**Playwright call pattern — ALWAYS use this via pi, never native MCP playwright tools directly (browser opens — confirmed working):**
```bash
source ~/.pi/agent/piedpiper.env
pi -p "EXECUTE IMMEDIATELY. Use mcp__playwright__browser_navigate then mcp__playwright__browser_snapshot. Do NOT guess — call the tools.

TASK: <navigate URL, interact, extract content>

Quote tool output verbatim." \
  --provider "$PIPER_PROVIDER" --model "$PIPER_REASON_MODEL" \
  --mode text --tools "mcp__playwright__browser_navigate,mcp__playwright__browser_snapshot,mcp__playwright__browser_click,mcp__playwright__browser_type,mcp__playwright__browser_take_screenshot" \
  --no-skills
```
- Omit `--no-extensions` — pi-mcp must load to connect playwright MCP server
- Browser will open visibly; tool names are `mcp__playwright__browser_*`
- Model may misreport result in text — the browser actions still executed (verified)
