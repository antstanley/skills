# Model & effort policy — recommended model for the planning roles

Unlike spec-builder, spec-planner does **not** fan out sub-agents — it and its companion
`done-certificates` run **inline**, in the same session that invoked them. There is no
dispatch call to attach a model to, so this policy is **advisory**: it states the model and
reasoning effort each role is intended to run at. If the current session is on a weaker
model or lower effort, switch before proceeding — the quality of a plan is set by the
reasoning that produced it, and a shallow decomposition is expensive to discover downstream.

| Role | Model | Effort | Why |
|---|---|---|---|
| **Decomposition** (the `spec-planner` skill) | `opus` | `high` | Reading a whole spec set + code, slicing it into reviewable task packages, building and ordering the dependency DAG for reviewability — the load-bearing reasoning the whole build inherits. |
| **Done-certificate authoring** (the `done-certificates` skill) | `opus` | `high` | Translating each task's definition of done into precise proof obligations with named evidence and checks — structured reasoning a later validator depends on. |

Notes:

- **`spec-reviewer` in Phase 1** (invoked to learn what is already built) ships in the
  spec-creator plugin and runs under *its* policy — `fable` at `high`, the reviewer tier.
- **Enforcement is out of scope here by design.** These roles are inline; making them
  enforced would mean dispatching them as sub-agents, which trades away the shared context
  that makes inline planning coherent. Only spec-builder, which already fans out, enforces
  model/effort. If you *do* want an enforced planning pass on Claude Code, run it as a
  `Workflow` `agent()` with `{ model: 'opus', effort: 'high' }`.
- An explicit request overrides the table ("plan this at max effort").
