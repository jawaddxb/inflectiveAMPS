# AMPS Adoption Roadmap

> "You don't promote a standard. You promote the experience the standard enables."

The experience: **migrate your agent in 30 seconds.** AMPS is the infrastructure underneath.

---

## The Core Insight

Standards that win share one trait: **adoption precedes consensus.**
Nobody voted for the S3 API. Nobody ratified JSON. Markdown had no formal spec for years.
They won through ubiquity.

Standards that die launch as a spec, hold a committee, write a blog post, and wait.

AMPS takes the first path. Working code ships on day one. PRs before proposals.
Adoption is the path of least resistance.

---

## The 7 Heartbeats

### Heartbeat 1 — Ship code, not a proposal (Week 1)

Day one, AMPS is not a "proposed standard." It is:

- `inflectiv/amps` on GitHub: MIT, spec as README, JSON schema, validator
- `amps-agent-zero` — native, lossless, ships with Inflectiv Vault
- `amps-autogpt` — importable today
- `amps-crewai` — importable today
- `amps-langgraph` — importable today
- `amps-llamaindex` — importable today

Someone discovers AMPS, runs `pip install amps-crewai`, exports their agent,
imports into Agent Zero — in under five minutes. **That experience is the launch.**

**Launch artifact:** Not a blog post about portability.
A demo: *"I migrated my AutoGPT agent to Agent Zero in 30 seconds."*

### Heartbeat 2 — The migration story goes viral (Week 1)

First content is not about AMPS. It is:

> "I trained an AutoGPT agent for 3 months on DeFi research.
> Today I migrated it to Agent Zero in 30 seconds. Zero data loss. Here's how."

That is a tweet. A YouTube video. A Reddit post in every framework's subreddit.
It demonstrates the problem and the solution in one concrete story.

Nobody cares about "memory portability standards."
Everyone cares about "I can switch frameworks without losing my agent's brain."

**AMPS is the implementation detail. The migration story is the marketing.**

### Heartbeat 3 — Framework maintainers adopt because it solves their ticket (Week 1-2)

Every framework gets the same support request:
*"How do I export my agent's memory?"*
*"I'm switching from X — can I bring my data?"*
Currently: no answer.

AMPS gives them one. The pitch to maintainers is not "adopt our standard."
It is: *"Here is a working, MIT-licensed adapter that closes the memory portability
ticketsyour users keep filing. 200 lines. Drop it in. We built it."*

**Link to their three existing issues.** PR, not proposal.

Maintainers adopt things that reduce support burden with zero effort.
A working PR does that. A spec proposal does not.

### Heartbeat 4 — OpenClaw Foundation submission creates political safety (Week 2)

If AMPS is "Inflectiv's format," competitors won't touch it.
If AMPS is "an OpenClaw Foundation standard that Inflectiv contributed," it is neutral infrastructure.

Submit the same week as code launch. Not before — you need working code to be taken seriously.
Not months later — you lose the window.

Governance story: *"AMPS is community-governed. Anyone can propose changes.
Inflectiv built v1 but doesn't own it."* Docker/OCI playbook.
Give away governance of the spec. Keep the best implementation.

### Heartbeat 5 — Monthly compatibility reports (Month 2+)

Every month: **AMPS Compatibility Report.**

- Which frameworks support import/export
- Losslessness % between each framework pair
- New community adapters
- Migration case studies

This does three things:
1. Recurring content keeps AMPS visible
2. Competitive pressure — if CrewAI scores 95% and LangGraph 60%, LangGraph's
   community pushes for better support
3. Positions Inflectiv as the authority on agent memory interoperability
   without claiming ownership of the spec

### Heartbeat 6 — AMPS score becomes a framework quality signal (Month 3)

Once 3-4 frameworks support AMPS, introduce the AMPS compatibility score:

*"This framework has an AMPS score of 94 — 94% of agent memory transfers
losslessly through AMPS."*

Frameworks will compete on this metric because users care about it.
Every time someone checks an AMPS score, they encounter Inflectiv's ecosystem.
**The score is a distribution channel.**

### Heartbeat 7 — Enterprise wants audit trails (Month 6+)

Enterprises running agent fleets need to answer:
*"What does this agent know, how did it learn it, and can we prove it?"*

AMPS with `contributions_history` and `migration_notes` is an audit log
for agent intelligence. Framework migrations produce a verifiable record:
what transferred, what was lost, what the agent's knowledge lineage is.

This is why AMPS matters beyond the crypto-native audience.
It is the compliance layer for agent memory that regulated industries will require.

---

## Adoption Sequence

```
Week 1
  Ship inflectiv/amps — spec + 5 adapters + validator
  Launch demo — "30-second agent migration" video
  Open PRs on: AutoGPT, CrewAI, LangGraph, LlamaIndex repos
  (Use pr_templates/ — find their 3 related issues, link them)

Week 2
  Submit AMPS_SPEC.md to OpenClaw Foundation
  Framework maintainer DMs — solve their support tickets
  Developer tutorials: "export from X, import to Y" — one per framework

Month 2
  Publish first AMPS Compatibility Report
  Community adapters appear for frameworks not covered
  Vault users are AMPS-native by default — flywheel begins

Month 3
  AMPS score concept introduced
  Enterprise interest — audit trail angle
  Second wave of framework PRs from community contributors

Month 6
  AMPS is the assumed default for agent memory interchange
  Inflectiv Vault is the reference implementation everyone benchmarks against
  New frameworks launch with AMPS support because that's what users expect
```

---

## The Memory Outlives Frameworks Pitch

For enterprises nervous about framework lock-in:

> *"Your agent memory is stored in an open standard.
> Whatever framework you use next year, your agents keep their context."

An agent trained over six months does not lose its intelligence
when a better framework launches. Export to AMPS. Import into the new framework.
Keep the brains.

This is not a launch story. It is a six-month story.
But it is why AMPS matters beyond the immediate audience.

---

## What You Never Say

Never say: *"Please adopt the AMPS standard."*
Say instead: *"Here is working code that solves your users' problem."*

Never say: *"AMPS is the future of agent memory."*
Say instead: *"I migrated my agent in 30 seconds. Here's the demo."*

AMPS succeeds when nobody talks about AMPS and everyone talks about
how easy it is to move their agent between frameworks. That is when you have won.
