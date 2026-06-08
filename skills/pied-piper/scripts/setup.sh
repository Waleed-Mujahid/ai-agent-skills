#!/usr/bin/env zsh
# pied-piper setup — make pi.dev a batteries-included delegation backend that
# inherits THIS machine's Claude Code MCP servers + skills, running on arbisoft LiteLLM.
#
# Portable & idempotent. Re-run any time; converges to the same state.
#
# Usage:  setup.sh [--fast-model <id>] [--reason-model <id>] [--include-project] [--no-lsp]
set -uo pipefail

PROVIDER="arbisoft-llm"
PROVIDER_BASE_URL="https://litellm.arbisoft.com/v1"
FAST_MODEL="groq/qwen/qwen3-32b"        # search, review (verified working)
REASON_MODEL="groq/openai/gpt-oss-120b" # debug, build (reasoning, verified working)
PI_AGENT="$HOME/.pi/agent"
MCP_JSON="$PI_AGENT/mcp.json"
SKILLS_LINK="$PI_AGENT/skills"
ENV_FILE="$PI_AGENT/piedpiper.env"
CLAUDE_SKILLS="$HOME/.claude/skills"
GLOBAL_CLAUDE_MD="$HOME/.claude/CLAUDE.md"

FAST_OV=""; REASON_OV=""; INCLUDE_PROJECT=0; WANT_LSP=1
while [[ $# -gt 0 ]]; do case "$1" in
  --fast-model)   FAST_OV="$2"; shift 2 ;;
  --reason-model) REASON_OV="$2"; shift 2 ;;
  --include-project) INCLUDE_PROJECT=1; shift ;;
  --no-lsp)       WANT_LSP=0; shift ;;
  *) shift ;;
esac; done

say(){ print -r -- "$@"; }; ok(){ print -r -- "  ✓ $*"; }
warn(){ print -r -- "  ⚠ $*"; }; die(){ print -r -- "  ✗ $*"; exit 1; }

say "═══ pied-piper setup (arbisoft LiteLLM) ═══"
command -v jq >/dev/null || die "jq required (brew install jq)"
command -v pi >/dev/null || die "pi not installed (npm i -g @earendil-works/pi-coding-agent)"
ok "pi $(pi --version 2>/dev/null)"
mkdir -p "$PI_AGENT"

# ── API key ───────────────────────────────────────────────────────────────────
if [[ -z "${LIBRE_CHAT_API_KEY:-}" ]]; then
  say ""
  say "  LIBRE_CHAT_API_KEY not set — needed to call arbisoft LiteLLM."
  printf "  Enter your LibreChat API key: "
  read LIBRE_CHAT_API_KEY
  [[ -z "$LIBRE_CHAT_API_KEY" ]] && die "API key required"
  print -r -- "\nexport LIBRE_CHAT_API_KEY=\"$LIBRE_CHAT_API_KEY\"" >> "$HOME/.zshrc"
  export LIBRE_CHAT_API_KEY
  ok "saved LIBRE_CHAT_API_KEY to ~/.zshrc"
else
  ok "LIBRE_CHAT_API_KEY set"
fi

# ── register arbisoft-llm provider in pi models.json ─────────────────────────
MODELS_JSON="$PI_AGENT/models.json"
PROVIDER_ENTRY='{
  "baseUrl": "https://litellm.arbisoft.com/v1",
  "api": "openai-completions",
  "apiKey": "${LIBRE_CHAT_API_KEY}",
  "models": [
    {"id": "cerebras/gpt-oss-120b",                          "name": "GPT-OSS 120B Cerebras (reasoning)", "reasoning": true, "compat": {"requiresReasoningContentOnAssistantMessages": false}},
    {"id": "cerebras/zai-glm-4.7",                           "name": "GLM 4.7 (fast)"},
    {"id": "groq/openai/gpt-oss-120b",                       "name": "GPT-OSS 120B Groq (reasoning)",    "reasoning": true},
    {"id": "groq/openai/gpt-oss-20b",                        "name": "GPT-OSS 20B (reasoning)",          "reasoning": true},
    {"id": "groq/llama-3.1-8b-instant",                      "name": "Llama 3.1 8B (fastest)"},
    {"id": "groq/llama-3.3-70b-versatile",                   "name": "Llama 3.3 70B (general)"},
    {"id": "groq/qwen/qwen3-32b",                            "name": "Qwen 3 32B (code+math)"},
    {"id": "groq/meta-llama/llama-4-scout-17b-16e-instruct", "name": "Llama 4 Scout (vision)", "input": ["text", "image"]}
  ]
}'
EXISTING="{}"; [[ -f "$MODELS_JSON" ]] && EXISTING="$(cat "$MODELS_JSON")"
print -r -- "$EXISTING" | jq --argjson entry "$PROVIDER_ENTRY" \
  '.providers["arbisoft-llm"] = $entry' > "$MODELS_JSON"
ok "registered arbisoft-llm provider → $MODELS_JSON"

# ── verify provider is now visible ────────────────────────────────────────────
pi --list-models 2>&1 | grep -q "^$PROVIDER " \
  && ok "arbisoft-llm visible to pi" \
  || warn "provider not visible yet — restart shell if this persists"

# ── write env file (config source of truth) ─────────────────────────────────
# Precedence: --flag override > existing piedpiper.env value (user edits preserved) > default.
if [[ -f "$ENV_FILE" ]]; then
  EXIST_PROVIDER="$(sed -n 's/^PIPER_PROVIDER="\{0,1\}\([^"]*\)"\{0,1\}/\1/p' "$ENV_FILE" | head -1)"
  EXIST_FAST="$(sed -n 's/^PIPER_FAST_MODEL="\{0,1\}\([^"#]*\).*/\1/p' "$ENV_FILE" | head -1 | tr -d ' ')"
  EXIST_REASON="$(sed -n 's/^PIPER_REASON_MODEL="\{0,1\}\([^"#]*\).*/\1/p' "$ENV_FILE" | head -1 | tr -d ' ')"
  [[ -n "$EXIST_PROVIDER" ]] && PROVIDER="$EXIST_PROVIDER"
  [[ -n "$EXIST_FAST" ]]     && FAST_MODEL="$EXIST_FAST"
  [[ -n "$EXIST_REASON" ]]   && REASON_MODEL="$EXIST_REASON"
fi
[[ -n "$FAST_OV" ]]   && FAST_MODEL="$FAST_OV"      # explicit flags always win
[[ -n "$REASON_OV" ]] && REASON_MODEL="$REASON_OV"

cat > "$ENV_FILE" <<EOF
# pied-piper config — edit to swap models/provider; setup preserves these unless you pass flags.
# Source this before calling pi directly. List available models: pi --list-models
PIPER_PROVIDER="$PROVIDER"
PIPER_FAST_MODEL="$FAST_MODEL"       # search, review (fast)
PIPER_REASON_MODEL="$REASON_MODEL"   # debug, trace, exec (reasoning model)
EOF
ok "models — fast: $FAST_MODEL | reason: $REASON_MODEL  (→ $ENV_FILE, edits preserved on re-run)"

# ── pi-mcp + pi-lsp ───────────────────────────────────────────────────────────
pi list 2>/dev/null | grep -q "pi-mcp" || { say "Installing @spences10/pi-mcp…"; pi install npm:@spences10/pi-mcp >/dev/null 2>&1; }
pi list 2>/dev/null | grep -q "pi-mcp" && ok "pi-mcp installed" || warn "pi-mcp not installed — MCP bridge won't load"
if [[ $WANT_LSP -eq 1 ]]; then
  pi list 2>/dev/null | grep -q "pi-lsp" || pi install npm:@spences10/pi-lsp >/dev/null 2>&1
  pi list 2>/dev/null | grep -q "pi-lsp" && ok "pi-lsp installed"
fi

# ── bridge Claude MCP servers → pi mcp.json ───────────────────────────────────
SRC=(); [[ -f "$HOME/.claude.json" ]] && SRC+=("$HOME/.claude.json")
[[ $INCLUDE_PROJECT -eq 1 && -f "$PWD/.mcp.json" ]] && SRC+=("$PWD/.mcp.json")
while IFS= read -r f; do SRC+=("$f"); done < <(find "$HOME/.claude/plugins" -name '.mcp.json' 2>/dev/null)
if (( ${#SRC[@]} )); then
  SERVERS="$(jq -s 'map(.mcpServers // {}) | add // {}' "${SRC[@]}" 2>/dev/null)"
  # whitelist: only bridge servers useful for coding tasks and known to work in pi
  # exclude: plane-arbisoft (110+ tools → Groq 128 cap), bun-based servers (EPIPE), oauth servers
  SERVERS="$(print -r -- "$SERVERS" | jq '{context7: .context7, playwright: .playwright} | with_entries(select(.value != null))')"
  # ensure playwright is present even if not in Claude config
  SERVERS="$(print -r -- "$SERVERS" | jq 'if has("playwright") then . else . + {"playwright":{"command":"npx","args":["@playwright/mcp@latest"]}} end')"
  print -r -- "$SERVERS" | jq '{mcpServers: .}' > "$MCP_JSON"
  ok "bridged $(print -r -- "$SERVERS" | jq 'length') MCP servers → $MCP_JSON"
  say "    ($(print -r -- "$SERVERS" | jq -r 'keys|join(", ")'))"
else warn "no Claude MCP configs found to bridge"; fi

# ── inherit Claude skills via symlink ─────────────────────────────────────────
if [[ -d "$CLAUDE_SKILLS" ]]; then
  [[ -e "$SKILLS_LINK" || -L "$SKILLS_LINK" ]] && ok "skills link present" \
    || { ln -s "$CLAUDE_SKILLS" "$SKILLS_LINK" && ok "skills symlinked → $CLAUDE_SKILLS"; }
else warn "no $CLAUDE_SKILLS to inherit"; fi

# ── inject CLAUDE.md delegation rules (idempotent) ───────────────────────────
PI_BLOCK_MARKER="# pi.dev direct calls"
if [[ -f "$GLOBAL_CLAUDE_MD" ]] && grep -q "$PI_BLOCK_MARKER" "$GLOBAL_CLAUDE_MD"; then
  ok "CLAUDE.md already has pi delegation block — skipping"
else
  # Remove old agent-based block if present
  if grep -q "# pi.dev delegation agents" "$GLOBAL_CLAUDE_MD" 2>/dev/null; then
    # Strip the old block (from the heading to the last line of the block)
    perl -i -0pe 's/\n# pi\.dev delegation agents.*?Single known file path.*?\n//s' "$GLOBAL_CLAUDE_MD"
    ok "removed old agent-based pi block from CLAUDE.md"
  fi
  cat >> "$GLOBAL_CLAUDE_MD" <<'MD'

# pi.dev direct calls (pied-piper) — run grunt work on arbisoft LiteLLM free models
Backend set up once via `/pied-piper`. Call `pi -p` directly via Bash for grunt work.

```bash
source ~/.pi/agent/piedpiper.env
pi -p "EXECUTE IMMEDIATELY. Use grep/search/read tools NOW — do NOT suggest, do NOT ask questions, do NOT speculate. Report ONLY evidence found: exact file paths, line numbers, code snippets. If nothing found, say so explicitly.

TASK: <task with absolute paths and exact symbol/pattern to search for>

Output format: file:line — <code snippet>" \
  --provider "$PIPER_PROVIDER" --model "$PIPER_FAST_MODEL" \
  --mode text --tools "read,bash,grep,find,ls" \
  --no-extensions --no-skills
```

Use explicit `--tools` allowlist — NOT `--exclude-tools`. Allowlist prevents extension tools (pi-mcp etc.) from loading and hanging on init.

Task routing:
- Search / "where is X" / find code → `$PIPER_FAST_MODEL` + `--tools "read,bash,grep,find,ls"`
- Trace flow / root-cause bug → `$PIPER_REASON_MODEL` + `--tools "read,bash,grep,find,ls"`
- Review diff / PR / branch → `$PIPER_FAST_MODEL` + `--tools "read,bash,grep,find,ls"`
- Refactor / test-gen / scaffolding → `$PIPER_REASON_MODEL` + `--tools "read,bash,grep,find,ls,edit,write"`

**Prompt rules for pi tasks:**
- Always include: exact symbol/pattern to grep, absolute root dir, expected output format
- Never ask pi open-ended questions — give it a concrete grep target
- If tracing a call chain: list the entry point symbol AND the suspected sink symbol

**Self-check before grinding:** "About to grep a large tree, read many files, or review a diff?" → yes → call pi directly. Keep on main model: architecture, security, final approve/merge, user-facing writing. Single known file path → just `Read` it.

**Playwright tasks** (browser automation, scraping, UI testing) — **ALWAYS use pi for playwright, never native MCP tools directly.** Drop `--no-extensions`, use `mcp__playwright__*` tool names:
```bash
source ~/.pi/agent/piedpiper.env
pi -p "EXECUTE IMMEDIATELY. Use mcp__playwright__browser_navigate then mcp__playwright__browser_snapshot. Do NOT guess or answer from memory — call the tools.

TASK: <navigate URL, interact, extract content>

Quote tool output verbatim in your response." \
  --provider "$PIPER_PROVIDER" --model "$PIPER_REASON_MODEL" \
  --mode text --tools "mcp__playwright__browser_navigate,mcp__playwright__browser_snapshot,mcp__playwright__browser_click,mcp__playwright__browser_type,mcp__playwright__browser_take_screenshot" \
  --no-skills
```
Note: omit `--no-extensions` so pi-mcp loads playwright MCP. Browser WILL open.

**Pi agents (interactive)** — pi workers Claude drives turn-by-turn, OMC-style (zero Claude tokens).
Each worker keeps a persistent pi session; Claude sends a turn, reads the reply, sends the next.
```bash
pa <agent> <session> "<turn instruction>"     # `pa` is a shell fn added by setup; or call the full path:
~/.claude/skills/pied-piper/agents/piagent.sh <agent> <session> "<turn instruction>"
# agents: explore(ex) debug(debugger) trace(tracer) exec(executor) review(reviewer) security(sec) qa(tmux) playwright(pw)
# <session> = any name; same name reuses the worker's context. First call creates it.
# Single-turn call == a one-shot. Multi-turn (same session) == an interactive worker.
# playwright keeps the browser open across turns; omits --no-extensions automatically.
```
MD
  ok "injected pi direct-call block → $GLOBAL_CLAUDE_MD"
fi

# ── ensure piagent driver is executable + install `pa` shell function ─────────
AGENTS_DIR="${0:A:h}/../agents"
PIAGENT="$AGENTS_DIR/piagent.sh"
if [[ -f "$PIAGENT" ]]; then
  chmod +x "$PIAGENT" 2>/dev/null
  ok "piagent driver executable → $PIAGENT"
  # `pa` shell function so workers are callable from anywhere (no full path, no sudo)
  if grep -q 'pied-piper piagent' "$HOME/.zshrc" 2>/dev/null; then
    ok "pa() already in ~/.zshrc"
  else
    print -r -- "\n# pied-piper piagent — interactive pi.dev workers (call \`pa <agent> <session> <msg>\`)\npa() { $PIAGENT \"\$@\"; }" >> "$HOME/.zshrc"
    ok "added pa() to ~/.zshrc — run 'source ~/.zshrc' or open a new shell"
  fi
else
  warn "piagent.sh not found at $PIAGENT — run from skill directory"
fi

# ── smoke test ────────────────────────────────────────────────────────────────
say ""; say "═══ smoke test ═══"
# --no-session: throwaway one-shot checks, no reason to persist them.
# stderr NOT suppressed — a silent failure here is usually an unexpanded API key or dead model;
# you want to see the actual error, not a blank line.
smoke(){  # $1=label $2=model
  local out
  out="$(pi -p "Reply with exactly: OK" --provider "$PROVIDER" --model "$2" --no-session --mode text 2>&1)"
  if print -r -- "$out" | grep -q "OK"; then
    ok "$1 model ($2) responded"
  else
    warn "$1 model ($2) did NOT respond — output below:"
    print -r -- "$out" | sed 's/^/      /'
    warn "common cause: LIBRE_CHAT_API_KEY unset/unexpanded, or model id dead. Check: pi --list-models"
  fi
}
smoke "fast" "$FAST_MODEL"
sleep 2
smoke "reason" "$REASON_MODEL"
say ""; say "Done. Search/review → \$PIPER_FAST_MODEL ($FAST_MODEL). Debug/build → \$PIPER_REASON_MODEL ($REASON_MODEL)."
say "Call pi directly: source ~/.pi/agent/piedpiper.env && pi -p '<task>' --provider \"\$PIPER_PROVIDER\" --model \"\$PIPER_FAST_MODEL\" --no-session --mode text"
