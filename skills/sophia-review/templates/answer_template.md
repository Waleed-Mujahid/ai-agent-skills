# Answer Template (MANDATORY)

Every answer paragraph must follow this structure:

> During [time period or project name], I [describe your key action or contribution], which [explain the result, improvement, or impact]. This outcome aligns with [specific competency area, organizational goal, or personal development objective].

## Rules

- 2–4 paragraphs per answer
- Each paragraph = ONE concrete example from evidence atoms
- Every statement needs a specific project name, PR link, metric, or artifact
- No vague claims ("I am good at X", "I always do Y")
- Format as HTML: wrap each paragraph in `<p>...</p>`
- Mention specific dates, PR numbers, ticket IDs, or measurable outcomes

## VOICE Rules (apply at draft time)

**SELF-REVIEW OVERRIDE**: Do NOT admit imperfections or caveats. Auditors score against rubric — any weakness = lower score. Be confident and technical. Surface architecture decisions, scale numbers, cross-stack ownership, production impact.

**Banned words** (never use): leverage, utilize, synergy, impactful, holistic, seamlessly, robust, transformative, groundbreaking, innovative, pivotal, paramount, meticulous, multifaceted, unwavering, delve, embark, tapestry, beacon, resonate, navigate, landscape, furthermore, moreover, consequently, proven track record, detail-oriented, results-driven

**Structure**:
- Do NOT open with: "I am writing to...", "It is my pleasure to...", or any variant
- No Oxford comma
- No prose three-item lists with commas — pick strongest one and cut rest
- **Prefer bulleted / numbered `<ul>`/`<ol>` for evidence**: when a paragraph cites multiple PRs, modules, repos or atoms, render as a bulleted list so the auditor can scan. Keep the lead-in sentence short. Bullets are evidence — not prose padding — and do not count as the banned three-item rule.
- Vary sentence length — no two short declaratives back to back
- No three paragraphs of similar length — vary: one short, one longer, one brief close
- The "aligns with" closer can appear once at end (not every paragraph)
- Target 200-300 words for 4-module answers; 200-word cap is a target not a hard cap

## Example (Project Delivery, L2→L3)

```html
<p>During the Koa-to-Ulmo platform upgrade (2025–2026), I designed and shipped the
<code>edlysaas-data-migrations</code> plugin from scratch, which migrated panel data,
LMS/CMS tables, discovery, credentials, and WordPress assets across seven production
PRs (#4–#12). This outcome aligns with full-module ownership and shipping non-trivial
projects end-to-end.</p>

<p>During the TheologyX client onboarding (April–May 2026), I bootstrapped the
edly-discovery-app plugin from initial commit through invite_only field support (15 PRs),
which delivered a production-grade multi-tenant discovery service used by a live client.
This aligns with designing and shipping modules that are adopted in production.</p>
```

## Subcategory-Specific Guidance

**Technical Execution** — Lead with the most complex/impactful project. End with upstream contributions if any.

**Maturity / Initiative** — Show *consistency* across multiple instances, not one-off events. Use time markers ("throughout 2025–2026", "on four separate occasions").

**Collaboration / Mentorship** — Lead with go-to-person evidence (DM help-asks answered). Quantify: "answered 8+ setup questions from Hamza Israr over April 2026".

**Continuous Learning** — Show *diversification* across domains (backend, infra, AI tooling), not depth in one area.

**Self-Discipline** — Show structured workflows, advance planning, zero dropped balls. Reference specific examples of proactive communication.
