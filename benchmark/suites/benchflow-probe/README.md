# benchflow-probe — throwaway BenchFlow substrate probe

This directory is a **substrate probe**, not a benchmark suite. It exists so a
reviewer can confirm, on a clean checkout, that the BenchFlow `bench` SDK named
in [`.specs/benchmark/specs/05-harness-architecture.md`](../../../.specs/benchmark/specs/05-harness-architecture.md)
§Substrate is wired and that its task-authoring gate works:

```
uv run bench tasks check benchmark/suites/benchflow-probe/trivial-probe
# ✓ trivial-probe — valid
```

`trivial-probe/` was generated with `uv run bench tasks init` (BenchFlow's own
scaffolder) and is the minimal task layout `bench tasks check` validates:
`task.toml` + `instruction.md` + `environment/Dockerfile`, with a `tests/`
verifier and a `solution/` oracle. It carries no benchmark logic and is not a
real `TaskInstance` — the benchmark's schema lives in
`benchmark.harness.domain`, and the substrate finding (what `bench` provides vs.
what the benchmark's own backend seam provides) is recorded in
[`benchmark/harness/substrate.py`](../../harness/substrate.py).
