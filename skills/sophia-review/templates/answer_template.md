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

## Rubric fit (most common scoring miss)

- **Write to the LITERAL target-level phrase.** Quote the exact target sentence from
  `00_rubric_delta.md` and make the answer satisfy *those words*. Level definitions can be
  counterintuitive — e.g. a "Breadth L4" phrase may reward depth on ONE side with >2
  frameworks, while the both-sides framing is the L3 phrase. A draft aimed at the adjacent
  idea scores one level low. Re-read the target phrase after drafting.

## Evidence & links (the auditor reads the answer, not your Drive)

- **Hyperlink every artifact inline** — PR, doc, issue, public Slack shoutout, GitHub search.
  Every answer gets ≥2 inline links; a link-less answer is the weakest in its category.
- **Name the problem each artifact solved**, especially upstream/external PRs: "removed the
  `parsel` dependency that broke the XBlock on Sumac, resolving help-wanted issue #197" beats
  "contributed to 5 repos".
- **One claim, one place.** Don't repeat the same unlinked assertion across answers — it
  amplifies doubt. Link a shared claim once (or to its Drive screenshot) and vary evidence.
- **No unverifiable precision.** Don't carry forward exact counts from last year you can't
  re-verify ("43 sessions"); soften to a defensible range or cite only what you can link.
- **Un-linkable proof → Drive.** Private DMs, Claude/Cursor sessions, calendar headcount, git
  terminal: reference as `<a href="DRIVE_FOLDER_URL">… (SS-NN)</a>`; the user swaps one URL.

## The grader is an AI — write for one

The score comes from an LLM that sees only the rubric and the answer text. It cannot click
links and knows nothing about the company's internal projects. Consequences:

- **Text must clear the level with every link dead.** The sentence around each `<a href>`
  states what the artifact proves ("merged PR adding 15 management commands (<a>#45</a>)").
  Links exist for the human who spot-checks or appeals — the AI never opens them.
- **Self-contained context.** One clause of explanation the first time an internal name
  appears ("edly-panel, our customer-facing admin dashboard"). An unexplained codename is
  noise to the grader.
- **Echo the target level's own vocabulary** where it's true — "owned the module end to end",
  "go-to person in the team" — so the semantic match to the level phrase is explicit. Echo,
  don't stuff: a keyword-stuffed answer reads worse to the human on appeal.
- **First paragraph carries the strongest level-proving atom.** LLM graders anchor on
  openings.
- **Concrete numbers beat adjectives** — but only artifact-verified numbers (from the
  evidence map's `verified` atoms), never remembered ones.

## De-jargon (write plain, verbose explanations)

- Explain the *what and why*, not the internal mechanism name. Good: "the same code runs
  across dev/stage/prod because it reads its database connections from config". Bad:
  "`plugin_settings()` injects 11 aliases into `settings.DATABASES` at load time".
- Define a term the first time you use it: "idempotent (re-running skips data already written,
  so a cutover resumes safely)".
- Split any sentence over ~30 words. Trim self-praise tails ("the VP replied 'Nice.'",
  "caught by me before anyone flagged it").

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

## Example (Project Delivery, L2→L3) — models hyperlinks, bullets, plain prose, no Oxford comma

```html
<p>During the Koa-to-Ulmo platform upgrade (2025–2026) I designed and shipped the
<a href="https://github.com/edly-io/edlysaas-tutor-internal/pull/45"><code>edlysaas-data-migrations</code></a>
plugin as a full module from an empty repo. It moves a client's entire dataset from the old
Open edX release to the new one across several services:</p>
<ul>
<li><strong>Data layer</strong> — connects to both the old and new MySQL databases plus MongoDB
at once (<a href="https://github.com/edly-io/edlysaas-tutor-internal/pull/26">#26</a>).</li>
<li><strong>15 management commands</strong> covering panel, LMS, CMS, discovery, credentials,
WordPress and S3 assets, with an <a href="https://docs.example.com/runbook">operator runbook</a> I wrote.</li>
</ul>
<p>It is now the standard cutover tool and has migrated 12+ live tenants. The migration
manager's milestone post credited me with handling the majority of the work "while maintaining
high engineering standards and code quality"
(<a href="https://team.slack.com/archives/C0/p1780322519498689">shoutout</a>). This aligns with
designing and shipping full modules for non-trivial production projects.</p>
```

Note: every artifact is a live link, evidence is bulleted and scannable, the prose explains
plainly (no "injects aliases at load time"), and there is no Oxford comma.

## Subcategory-Specific Guidance

**Technical Execution** — Lead with the most complex/impactful project. End with upstream contributions if any.

**Maturity / Initiative** — Show *consistency* across multiple instances, not one-off events. Use time markers ("throughout 2025–2026", "on four separate occasions").

**Collaboration / Mentorship** — Lead with go-to-person evidence (DM help-asks answered). Quantify: "answered 8+ setup questions from Hamza Israr over April 2026".

**Continuous Learning** — Show *diversification* across domains (backend, infra, AI tooling), not depth in one area.

**Self-Discipline** — Show structured workflows, advance planning, zero dropped balls. Reference specific examples of proactive communication.
