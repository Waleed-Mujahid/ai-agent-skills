# ai-agent-skills

A personal library of AI agent skills for Claude Code and other harnesses.

---

## Repository Structure

```
ai-agent-skills/
├── .claude-plugin/
│   └── marketplace.json          Plugin marketplace catalog — lists all installable plugins
├── skills/                       Standalone skills — one per directory
│   └── <skill-name>/
│       ├── <skill-name>.md       Skill definition
│       └── .claude-plugin/
│           └── plugin.json       Plugin manifest
```

---

## Resource Catalog

### Skills

| Skill | File | Description |
|-------|------|-------------|
| `pied-piper` | [skills/pied-piper/README.md](skills/pied-piper/README.md) | Gives Claude a free team of workers on Arbisoft's LiteLLM — **including a browser**. Interactive multi-turn workers (explore/debug/trace/exec/review/security/qa/playwright) Claude drives turn-by-turn; grunt work runs on free models, only findings re-enter Claude's context. Lighter, interactive successor to `delegate`. |
| `delegate` | [skills/delegate/delegate.md](skills/delegate/delegate.md) | Delegates grunt work (search, review, refactor, tests) to opencode running free LiteLLM models. Power-user alternative to `pied-piper` (heavier opencode runtime). |
| `sophia-review` | [skills/sophia-review/sophia-review.md](skills/sophia-review/sophia-review.md) | End-to-end Sophia competency self-review assistant. Phased chat: configures auth + MCPs, harvests a year of evidence (GitHub/Plane/Slack/Calendar/Claude+Cursor sessions) in parallel, builds an evidence map, surfaces next-level rubric differentials, asks targeted gap questions, drafts rubric-aligned answers, and submits + verifies them via the Sophia API. |

---

## Using These Skills

### Claude Code

**Step 1 — Add marketplace (one-time)**

```shell
/plugin marketplace add Waleed-Mujahid/ai-agent-skills
```

**Step 2 — Install a skill**

```shell
/plugin install pied-piper@ai-agent-skills
/plugin install delegate@ai-agent-skills
/plugin install sophia-review@ai-agent-skills
```

**Keep up to date:**

```shell
/plugin marketplace update ai-agent-skills
```

### Cursor

Pull directly into your project:

```bash
mkdir -p .cursor/rules

gh api repos/Waleed-Mujahid/ai-agent-skills/contents/skills/delegate/delegate.md \
  --jq '.content' | base64 --decode > .cursor/rules/delegate.mdc
```

---

## Contributing

### Directory Structure

**Standalone Skill:**
```
skills/
└── my-new-skill/
    ├── my-new-skill.md
    └── .claude-plugin/
        └── plugin.json
```

### plugin.json Format

```json
{
  "name": "my-new-skill",
  "description": "One sentence: what this skill does and when to use it.",
  "version": "1.0.0",
  "author": {
    "name": "First Last (github_username)"
  },
  "commands": ["./my-new-skill.md"]
}
```

### Adding a Skill

1. Create `skills/my-new-skill/` with `my-new-skill.md` and `.claude-plugin/plugin.json`.
2. Add frontmatter to top of `my-new-skill.md`:

```yaml
---
name: my-new-skill
description: "<one sentence describing what this skill does and when to use it>"
---
```

3. Add entry to `.claude-plugin/marketplace.json`.
4. Update Skills table in this README.
