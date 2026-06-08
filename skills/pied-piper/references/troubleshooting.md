# pied-piper troubleshooting

## API key issues (401 / "Invalid proxy server token")

pi reads `LIBRE_CHAT_API_KEY` from your env at request time. The `~/.pi/agent/models.json`
stores the reference as `"$LIBRE_CHAT_API_KEY"` — not the literal key.

If you see 401 errors or the smoke test warns "model silent":
```zsh
echo $LIBRE_CHAT_API_KEY          # check what's in the current shell
grep LIBRE_CHAT_API_KEY ~/.zshrc  # check what ~/.zshrc exports
source ~/.zshrc                   # re-apply zshrc if values differ
```
The current session can have a stale value that overrides `~/.zshrc` — `source ~/.zshrc`
fixes it. Then re-run setup to re-verify.

## Provider not visible ("arbisoft-llm not found")
Setup writes the provider config to `~/.pi/agent/models.json`. If the provider isn't
visible after setup:
```bash
pi --list-models | grep '^arbisoft-llm '   # should list models
jq '.providers["arbisoft-llm"].apiKey' ~/.pi/agent/models.json  # should be "$LIBRE_CHAT_API_KEY"
```
Re-run `/pied-piper` to re-register the provider.

## Want different models
Edit `~/.pi/agent/piedpiper.env` directly (`PIPER_FAST_MODEL`, `PIPER_REASON_MODEL`),
or pass overrides to setup:
```bash
~/.claude/skills/pied-piper/scripts/setup.sh --fast-model groq/openai/gpt-oss-20b --reason-model cerebras/gpt-oss-120b
```
Browse available models: `pi --list-models | grep '^arbisoft-llm'`

**Known-good arbisoft-llm models (tested 2026-06-08):**

| Model | Size | Thinking | Tier |
|-------|------|----------|------|
| `groq/llama-3.1-8b-instant` | 8B | no | fast |
| `groq/openai/gpt-oss-20b` | 20B | yes | fast/reason |
| `groq/qwen/qwen3-32b` | 32B | no | fast |
| `groq/llama-3.3-70b-versatile` | 70B | no | reason |
| `cerebras/gpt-oss-120b` | 120B | yes | reason (default) |
| `groq/openai/gpt-oss-120b` | 120B | yes | reason |
| `groq/meta-llama/llama-4-scout-17b-16e-instruct` | 17B | no | fast |
| `cerebras/zai-glm-4.7` | ? | no | fast |

**Dead models (do not use):**
- `cerebras/llama3.1-8b` — 404
- `cerebras/qwen-3-235b-a22b-instruct-2507` — 404

## pi lists no MCP tools
- pi-mcp does not connect servers at startup; the agents prefix
  `MY_PI_MCP_EAGER_CONNECT=1`. Set it too when testing by hand.
- Confirm the bridge file: `jq '.mcpServers | keys' ~/.pi/agent/mcp.json`.
- If tools are still missing, pi-mcp may expect the global config at a different path
  on your build — try copying to `~/.pi/mcp.json`, or run `/mcp connect <server>` in an
  interactive `pi` session to see connection errors.
- **http/SSE MCP servers** (`"type":"http"`, e.g. context7, plane): pi-mcp's stdio path
  is best-supported; remote servers may not connect. stdio servers (github, jenkins,
  slack-stdio, playwright) are the reliable set. Expected, not a bug.
- **oauth claude.ai servers** (Slack/Gmail/Drive with an `oauth` block) are skipped on
  purpose — pi can't run their browser oauth headless.

## "Cannot find module" / install failed
```bash
pi list                       # installed extensions
pi install npm:@spences10/pi-mcp
pi update                     # refresh installed extensions
```

## Re-syncing after changing your Claude setup
Installed a new MCP server or skill in Claude? Re-run the installer — it's idempotent
(overwrites `mcp.json`, refreshes the provider extension, leaves the skills symlink).

## Agents not auto-dispatching
Auto-routing is driven by the `pi.dev delegation` rule in `~/.claude/CLAUDE.md` plus the
agents' `description` fields. Confirm the rule is present and `~/.claude/agents/pi-*.md`
exist. Confirm `~/.pi/agent/piedpiper.env` exists (agents source it for provider+models).
