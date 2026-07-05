# Model & effort — spec-creator runs on the session model

The spec-creator plugin does **not** fan out sub-agents — its three skills (`spec-creator`,
`development-guidelines`, `spec-reviewer`) run **inline** and hand off to each other in the
same session. There is no dispatch call to attach a model to, so there is no per-role table to
enforce: the skills run on **whatever model the session is on**.

The roles differ in how much they ask of the model, which is worth keeping in mind when you
pick what to run the session on:

- **Spec authoring** (`spec-creator`) — investigative reading of the code, deciding the layered
  file set, writing precise canonical/change specs. The most reasoning-heavy role; give it a
  capable model.
- **spec-reviewer** — analytical verification: tracing references, running the semi-formal
  certificate templates, producing a divergence verdict. Also reasoning-heavy; a capable model
  earns its keep.
- **development-guidelines** — templated assembly (detect languages/VCS/style, merge base files
  with style overlays). More mechanical than creative; it does not need the ceiling.

These are considerations for choosing what to run the session on, not fixed defaults, and an
explicit request overrides ("write this spec at max effort"). If you want `spec-reviewer`
enforced on a specific model, it is self-contained enough (spec + code → verdict) to dispatch
as a `Workflow` `agent()` with the model and effort you choose — the authoring roles rely on
shared session context and do not isolate as cleanly. Only spec-builder, which fans out,
selects a model per sub-agent as a matter of course.
