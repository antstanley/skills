# Model & effort policy — recommended model for the spec-creator roles

The spec-creator plugin does **not** fan out sub-agents — its three skills (`spec-creator`,
`development-guidelines`, `spec-reviewer`) run **inline** and hand off to each other in the
same session. There is no dispatch call to attach a model to, so this policy is
**advisory**: it states the model and reasoning effort each role is intended to run at. If
the session is on a weaker model or lower effort than a role calls for, switch before
proceeding.

| Role | Model | Effort | Why |
|---|---|---|---|
| **Spec authoring** (the `spec-creator` skill) | `opus` | `high` | Investigative reading of the code, deciding the layered file set, writing precise canonical/change specs — creative, structural reasoning that everything downstream is built from. |
| **spec-reviewer** (R1 / R2 / R3 passes) | `fable` | `high` | Analytical verification: tracing references, running the semi-formal certificate templates, producing a divergence verdict. The reviewer tier (the most capable model) — same as spec-builder's gates. |
| **development-guidelines** | `sonnet` | `medium` | Templated assembly: detect languages/VCS/style, then merge per-language base files with style overlays. More mechanical than creative, so it does not need the top tier. |

Notes:

- **Enforcement is out of scope here by design.** These roles are inline; enforcing a model
  would mean dispatching them as sub-agents and losing the shared investigation context that
  makes the hand-offs coherent. Only spec-builder, which already fans out, enforces
  model/effort.
- **If you want spec-reviewer enforced** on Claude Code, you *can* dispatch it as a
  `Workflow` `agent()` with `{ model: 'fable', effort: 'high' }` — it is the most
  self-contained of the three (it takes a spec + code and returns a verdict), so it survives
  being run as an isolated sub-agent better than the authoring roles do.
- An explicit request overrides the table ("write this spec at max effort").
