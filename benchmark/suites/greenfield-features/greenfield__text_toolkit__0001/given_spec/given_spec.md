# Given Spec — `text_toolkit`

> **Frozen A2/A3 asset.** This spec is the ready-made specification handed to
> arms **A2** (plan + build, gates on) and **A3** (build without gates). It is
> authored ONCE to the fixed quality bar documented in
> `benchmark/harness/arms/a2_a3.py` (`GIVEN_SPEC_QUALITY_BAR`) and is consumed
> **identically** by both arms, so that spec variance never leaks into the
> A1−A2 or A2−A3 deltas. It is the spec-creator stage's output, replaced by a
> fixed authored artifact; the only difference between A2 and A3 is the gates.
> Do not regenerate per run.

## 1. Overview

`text_toolkit` is a small text-processing library with four interlocking
components that compose into one summarisation pipeline. The package's
`__init__` re-exports `tokenize`, `normalize`, `word_counts`, `top_terms`, and
`summarize`. Every component uses only the Python standard library. The
dependency graph (each component consumes the one above it):

```
tokenizer ──► normalizer ──► frequency ──► pipeline
    └────────────────────────────────────► (pipeline also calls tokenizer)
```

## 2. Domain model and invariants

- **Token.** A maximal run of alphanumeric characters drawn from the input.
- **Stop-word set.** The fixed set `{a, an, the, of, and, to, in}`, matched
  against the lowercased token.
- **Data-flow invariants.**
  1. `tokenize` never returns an empty string as a token.
  2. `normalize`'s output is a subsequence of the lowercased tokens (order
     preserved, no reordering, only stop-word removal).
  3. `frequency` and `pipeline` count NORMALIZED terms (tokenizer → normalizer),
     never raw tokens.

## 3. Components (contracts)

### Component 1 — `tokenizer.tokenize(text: str) -> list[str]`

Split `text` into word tokens on any run of non-alphanumeric characters,
preserving original case and dropping empty tokens.

- `tokenize("Hello, World!") == ["Hello", "World"]`
- `tokenize("it's a test") == ["it", "s", "a", "test"]`
- `tokenize("one1two2three") == ["one1two2three"]`
- `tokenize("---") == []` and `tokenize("") == []`
- Case and digits are preserved (`tokenize("Hello WORLD") == ["Hello", "WORLD"]`).

### Component 2 — `normalizer.normalize(tokens: list[str]) -> list[str]`

Consumes the tokenizer's output. Lowercase each token and remove the stop words,
preserving the order of survivors.

- `normalize(["The", "Cat", "and", "THE", "dog"]) == ["cat", "dog"]`
- `normalize([]) == []`
- Output is a subsequence of the lowercased input (invariant 2).

### Component 3 — `frequency.word_counts(text) -> dict[str, int]` and `frequency.top_terms(text, limit) -> list[tuple[str, int]]`

Compose tokenizer + normalizer. `word_counts` counts normalized terms.
`top_terms` returns the `limit` most-frequent `(term, count)` pairs sorted by
count descending, ties broken by term ascending.

- `word_counts("the the cat") == {"cat": 1}` (stop words dropped before counting).
- `word_counts("") == {}`.
- `top_terms` ordering: count descending, then term ascending; respects `limit`.

### Component 4 — `pipeline.summarize(text, limit) -> dict`

Orchestrates all three. Returns
`{'tokens': <raw token count>, 'terms': <distinct normalized term count>, 'top': top_terms(text, limit)}`.

- `tokens` is the count of RAW tokens (`len(tokenize(text))`).
- `terms` is the count of DISTINCT normalized terms (`len(word_counts(text))`).
- `top` is `top_terms(text, limit)`.
- `summarize("", 3) == {'tokens': 0, 'terms': 0, 'top': []}`.

## 4. Definition of done (acceptance bar)

- Every public function is implemented (no `NotImplementedError`), standard
  library only.
- The package `__init__` re-exports all five callables.
- Each component honours its contract and the data-flow invariants above.
- The existing `test_smoke.py` continues to pass (public API importable).
- A withheld acceptance suite (never shown to the arms) decides resolution.
