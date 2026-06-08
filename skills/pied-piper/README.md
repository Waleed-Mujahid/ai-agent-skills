# pied-piper — give Claude a free team (and a browser)

> Claude can now **drive a real browser** — navigate, click, fill forms, screenshot, scrape,
> reproduce UI bugs — and run a whole crew of specialized workers besides. All on Arbisoft's
> free LiteLLM models, all orchestrated turn-by-turn by Claude. Your Opus tokens stay for the
> thinking; the grunt work runs for $0.

pied-piper turns [pi.dev](https://pi.dev) (a tiny headless coding agent) into a delegation
backend wired to **your** Claude Code setup. After a one-command install, Claude has a team of
interactive workers it talks to like teammates — sending a task, reading the reply, sending the
next instruction — while the expensive file-reading and browser-driving happen on free models.
Only the distilled findings ever re-enter Claude's context.

---

## Why you want this

Claude Opus is precious. But most agent work isn't thinking — it's **grunt work**:

- sweeping a big repo for "where is X / how does auth flow"
- reading 40 files to answer one question
- reviewing a diff or a whole PR
- **clicking through a web app to reproduce a bug or scrape a page**
- scaffolding boilerplate, generating tests, running them

Every one of those burns your Opus budget on low-reasoning token churn. pied-piper offloads it to
free workers and pulls back a tight summary. You get **OMC-style multi-agent orchestration for $0**,
and your Claude budget lasts far longer.

### The standout: a browser worker

The `playwright` worker is the headline. Claude drives a **real, visible browser** through a
persistent session:

```bash
pa playwright login "navigate https://apps.stage.example.com and snapshot the login form"
pa playwright login "fill the email field with qa@example.com, click Next"     # same browser, same page
pa playwright login "fill password from my prompt, submit, snapshot the dashboard"
```

The browser stays open across turns — Claude walks a flow step by step, snapshotting to confirm
each step, never guessing. Perfect for UI bug repro, smoke tests, and scraping behind a login.

---

## Quick start (Arbisoft)

**1. Install the plugin** (one-time):

```
/plugin marketplace add Waleed-Mujahid/ai-agent-skills
/plugin install pied-piper@ai-agent-skills
```

**2. Run setup** — Claude runs it, or you do:

```
/pied-piper
```

Setup is interactive-free and idempotent. It will:

- prompt for your **`LIBRE_CHAT_API_KEY`** (your LibreChat / LiteLLM key) and save it to `~/.zshrc`
- register the `arbisoft-llm` provider and a verified model pair
- bridge **your** Claude MCP servers (context7, playwright, …) into pi
- symlink **your** Claude skills into pi
- install the **`pa`** shell function so you can call workers from anywhere
- inject delegation rules into `~/.claude/CLAUDE.md` so Claude auto-delegates

**3. Use it.** Either let Claude delegate automatically (the injected rules tell it to), or call a
worker yourself:

```bash
pa <agent> <session> "<instruction>"
```

That's it. No daemon, no TUI, no polling — pi runs, answers, exits; the session lives on disk.

---

## The workers

One driver (`agents/piagent.sh`, aliased to `pa`). Each worker keeps a **persistent pi session**,
so the same `<session>` name continues the same conversation with full context retained.

| Worker | Alias | Model tier | Tools | Use for |
|--------|-------|-----------|-------|---------|
| `explore` | `ex` | fast | read/grep/find | find files, symbols, patterns, relationships |
| `debug` | `debugger` | reason | read/grep/find | root-cause analysis (3-failure circuit breaker) |
| `trace` | `tracer` | reason | read/grep/find | causal tracing with competing hypotheses |
| `exec` | `executor` | reason | read/grep/find/**edit/write** | minimal-diff implementation |
| `review` | `reviewer` | fast | read/grep/find | severity-rated code review |
| `security` | `sec` | reason | read/grep/find | OWASP Top-10 audit + secrets scan |
| `qa` | `tmux` | reason | read/bash | interactive CLI testing via tmux |
| `playwright` | `pw` | reason | playwright MCP | **browser automation, UI testing, scraping** |

**Single turn = a one-shot. Multiple turns on one session = an interactive worker** Claude drives.
That's the whole model — no separate one-shot vs. interactive scripts.

### Examples

```bash
# Codebase onboarding — explore worker, two turns, second builds on the first
pa explore auth "find every caller of get_current_site in /repo"
pa explore auth "now narrow to the ones inside middleware"

# Bug root-cause — feed the debugger evidence across turns
pa debug npe "NoneType at lms/views.py:142 after SSO login — root cause?"
pa debug npe "git blame says line 142 changed in abc123 — does that explain it?"

# PR review — reviewer reads the diff; Claude verifies the findings before you post
pa review pr42 "review the diff: git diff origin/main...HEAD in /repo"

# List active worker sessions
pa --list
```

---

## Configuration

The single source of truth is **`~/.pi/agent/piedpiper.env`** — edit it to swap models or provider,
no script changes needed:

```bash
PIPER_PROVIDER="arbisoft-llm"             # LiteLLM provider registered in ~/.pi/agent/models.json
PIPER_FAST_MODEL="groq/qwen/qwen3-32b"    # search, review (tool-calling verified)
PIPER_REASON_MODEL="groq/openai/gpt-oss-120b"  # debug, trace, exec (reasoning verified)
```

- **Sensible defaults** ship verified-working — you don't have to touch anything.
- **Swap models** by editing the file, or at setup time: `/pied-piper --fast-model <id> --reason-model <id>`.
- **Re-running setup preserves your edits** unless you pass override flags.
- See verified-vs-dead models in [SKILL.md](./SKILL.md); list everything with `pi --list-models`.

### Requirements

- `pi` **pinned to 0.78.1**: `npm i -g @earendil-works/pi-coding-agent@0.78.1` — this is the
  verified version. Newer versions have changed behavior silently (e.g. env-var expansion in
  `models.json`); setup warns if a different version is installed.
- `jq` installed: `brew install jq`
- A LibreChat / LiteLLM API key (`LIBRE_CHAT_API_KEY`) with access to `litellm.arbisoft.com`
- **macOS + zsh only.** Scripts target zsh and write to `~/.zshrc`. Linux/bash is not supported yet.

---

## pied-piper vs. delegate

Both push grunt work to free LiteLLM models. They differ in the runtime:

| | **pied-piper** (default) | **delegate** (power user) |
|---|---|---|
| Backend | pi.dev — tiny headless CLI, no daemon | opencode — full agent runtime via MCP server |
| Workers | 8 interactive personas Claude drives turn-by-turn | opencode sessions |
| Browser | ✅ first-class playwright worker | via opencode tools |
| Weight | minimal — runs, answers, exits | heavier — long-lived server |
| Reach for it when | most delegation, anything interactive, browser work | you want opencode's deeper autonomy/toolset |

**Newcomers: start with pied-piper.** delegate remains for opencode power users.

---

## How it works (the mechanism)

Each `pa` call is one turn. pi's `--session-id <id>` reuses the worker's session if it exists
(creating it if missing), so message history persists across independent process invocations —
that's what makes the worker remember. The persona (role/rules/output format) is re-injected each
turn via `--append-system-prompt`, since pi doesn't store the system prompt between turns.

No tmux panes, no inbox files (that's how OMC does it) — state lives entirely in pi's session
store. Claude is the orchestrator on the other end of every conversation.

---

## Troubleshooting

See [references/troubleshooting.md](./references/troubleshooting.md). Common ones:

- **A turn comes back empty** — the gpt-oss reason model occasionally emits only tool calls with no
  final text after heavy tool use. The work still landed in the session; re-send "summarize what you
  just found" on the same session.
- **`pa: command not found`** — run `source ~/.zshrc` or open a new shell (setup adds the function).
- **MCP/playwright not loading** — re-run `/pied-piper` to re-bridge; the playwright worker omits
  `--no-extensions` on purpose so pi-mcp can connect.

---

_Lighter, interactive successor to `delegate`. Built for Arbisoft engineers on Claude Code._
