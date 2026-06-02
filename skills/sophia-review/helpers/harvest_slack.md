# Slack Harvest — MCP Tool Recipe

Use `mcp__claude_ai_Slack__*` tools directly from Claude. Do NOT delegate to opencode (MCP unavailable in subagents).

## Agent E — Channel Messages

For each channel ID in the user's list:

```python
# Step 1: Read channel messages
mcp__claude_ai_Slack__slack_read_channel(
    channel_id="<channel_id>",
    limit=200
)

# Step 2: For each message with reply_count > 0, fetch thread
mcp__claude_ai_Slack__slack_read_thread(
    channel_id="<channel_id>",
    thread_ts="<message_ts>"
)
```

**Filter criteria for substantive messages:**
- Message from the target user (match `user` field to known Slack user ID)
- Length > 100 characters, OR contains code blocks (`` ` ``), OR contains URLs
- Excludes: bot messages, join/leave notifications, simple acknowledgements ("ok", "done", "thanks")

**Type classification (pick ONE):**
| Keyword signals | Type |
|----------------|------|
| "kindly test", "kindly run", SQL queries | `db-ops` |
| root cause explanation, "the issue is", "I investigated" | `root-cause-analysis` |
| "we deployed", "we completed", "going to prod" | `prod-deployment` |
| reviewing PRs, "kindly review", "LGTM" | `code-review-request` |
| "the fix is", "I fixed", CORS/bug resolution | `bug-diagnosis` |
| huddle invite, meet.google.com, zoom.us | `huddle` |
| "Kindly note", summarizing for client | `client-update` |
| AI tools, Claude Code, skill references | `ai-tooling` |
| log analysis, "from the logs", "I can see in logs" | `log-analysis` |
| release coordination, "builds are complete", tagging teammates | `release-coordination` |
| ops commands, management commands, deploy scripts | `ops-command` |

**Output table:**
```markdown
| date | channel | excerpt (first 120 chars) | permalink | type |
|------|---------|---------------------------|-----------|------|
```

Write to `$WORKDIR/evidence/e_slack_channels.md`.

---

## Agent F — DM Messages

For each DM channel ID in the user's list:

```python
# Read DM history
mcp__claude_ai_Slack__slack_read_channel(
    channel_id="<dm_channel_id>",
    limit=200
)
```

**Filter for high-signal DM exchanges:**
1. Find "help-ask" messages: questions containing `?`, error messages, "can you", "please help", "stuck"
2. Find Waleed's replies: messages immediately after help-asks (> 80 chars, or contain code)
3. Find huddle signals: "huddle?", meet.google.com, zoom.us links
4. Waleed-initiated outreach: first message in a sequence that isn't a help-ask response

**To identify who the DM is with:**
```python
mcp__claude_ai_Slack__slack_read_user_profile(user_id="<other_user_id>")
```

**Direction classification:**
- `ask`: other person asking Waleed something
- `answer`: Waleed answering the other person
- `waleed-initiated`: Waleed starting the conversation

**Output table:**
```markdown
| date | dm_with | direction | excerpt | type |
|------|---------|-----------|---------|------|
```

Write to `$WORKDIR/evidence/f_slack_dms.md`.

---

## Authentication Note

If Slack MCP returns auth errors, run:
```python
mcp__claude_ai_Slack__authenticate()
```
Then complete with the returned URL. Re-run harvest after successful auth.
