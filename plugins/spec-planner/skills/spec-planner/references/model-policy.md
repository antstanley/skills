# Model & effort — spec-planner runs on the session model

Unlike spec-builder, spec-planner does **not** fan out sub-agents — it and its companion
`done-certificates` run **inline**, in the same session that invoked them. There is no
dispatch call to attach a model to, so there is nothing to pin and no per-role table: these
skills run on **whatever model the session is on**, and that is the knob.

Decomposition and done-certificate authoring are the **load-bearing reasoning** the whole
build inherits — a shallow plan is expensive to discover downstream — so run spec-planner on a
model suited to the spec in front of you: a large or subtle spec deserves a capable model at
high effort; a small one does not need the ceiling. That is a judgment call for whoever starts
the session, not a fixed requirement, and an explicit request overrides it ("plan this at max
effort").

If you *do* want an enforced planning pass on Claude Code — a model attached to the reasoning
rather than inherited — dispatch it as a `Workflow` `agent()` with the model and effort you
choose. Only spec-builder, which already fans out, selects a model per sub-agent as a matter of
course; here the session model is the default and the override at once.
