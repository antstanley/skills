# Voice and the Decisions pattern

Worked examples of the rules in `SKILL.md §Voice and tone` and `§Decisions pattern`. Read this when phrasing feels awkward — concrete examples beat abstract rules.

---

## Voice — what to write, what to cut

The default is **declarative present tense, short sentences, no marketing voice.**

### Good

> The editor app is client-only for the editing surface. The single server-side concession is `/api/opengraph` — a SvelteKit endpoint that fetches a URL server-side, parses the OpenGraph / Twitter / `<meta>` tags with `linkedom`, and returns structured metadata for the OpenGraph link card node.

Why it works:
- Present tense ("is", "fetches", "returns").
- Concrete: names the endpoint, the library, what's parsed.
- One non-obvious choice ("server-side concession") is acknowledged but the *why* lives in the Decisions block.
- No "easily", "simply", "powerful".

### Bad

> The editor app uses a powerful and easy-to-use server-side endpoint to seamlessly fetch beautiful OpenGraph data. This makes link previews work perfectly!

Why it doesn't:
- "Powerful", "easy-to-use", "seamlessly", "beautiful", "perfectly" — marketing voice.
- Exclamation point.
- "This makes ... work" — vague; what specifically does it do?

### Cuts

- **"easily" / "simply" / "just"** — these mean nothing in a spec.
- **"powerful" / "robust" / "scalable"** — adjectives that signal nothing measurable.
- **"seamlessly"** — never. If a seam is invisible, say where it is, not that it's invisible.
- **Exclamation points.**
- **"In order to"** → just "to".
- **"It should be noted that"** / "It is important to" → drop the throat-clearing.

---

## Tense

| Section | Tense | Example |
|---|---|---|
| Body (what exists) | Present | "The autosave loop debounces dirty events by 500 ms." |
| Decisions (what was chosen) | Past or present | "*Autosave debounce.* **500 ms.** We chose this because…" |
| Open questions | Question form | "*Migration strategy.* When `tags` joins `StoredDocument`, the `onupgradeneeded` callback is the right place — open: in-place rewrite or v2 store + copy?" |

### Watch for

- **"will be"** in the body — rewrite to "is" if it exists, or move to Open questions if it doesn't.
- **"would"** — same as above. "The validator would reject..." → "The validator rejects..." (if it does).
- **"may"** — context-dependent. "May" describing user choice is fine ("the user may collapse the sidebar"); "may" describing system possibility is fuzzy ("the system may fail" — under what conditions?).

---

## The Decisions pattern

Every spec page closes with three blocks: Assumptions, Decisions, Open questions. The **Decisions** block is the most valuable; it captures *why* the spec describes what it describes.

### Format

```markdown
- *<short label>.* **<the choice>.** <one or two sentences explaining the rationale>
```

Three parts, in this order, with this punctuation. The label is italic and short — what the decision is about. The choice is bold — what was decided. The rationale is plain prose — why.

### Worked examples

```markdown
- *Persistence layer.* **IndexedDB via `idb`.** Simpler than raw IndexedDB; mature; small; well-typed. localStorage is a non-starter (size limit, sync API).

- *Editor framework.* **Lexical.** Mature, framework-agnostic, well-typed. ProseMirror and Tiptap bring heavier dependencies and weaker SSR stories.

- *Bootstrap-token lifetime.* **300 seconds** (`BOOTSTRAP_TOKEN_TTL_SECONDS`). Balances slow-AMI boot against leak window.

- *Heavy lint/test gate.* **Pre-push, never pre-commit.** Pre-commit is friendlier for typo-sized commits; pre-push is faster for iterative jj workflows and keeps commits cheap.
```

### Anti-patterns

- ❌ `*Database.* **DynamoDB.** Team agreed.` — "Team agreed" is not a rationale.
- ❌ `*Caching.* **Yes.** We need caching.` — restates the choice as the rationale.
- ❌ `*Authentication.* **OIDC.** It's the best.` — superlative without comparison.
- ❌ `*Theme.* **Dark mode supported.** Modern apps need dark mode.` — vague appeal to fashion.

### Decisions vs Assumptions vs Open questions

| Block | What goes here | Example |
|---|---|---|
| Assumptions | Facts about the world the spec depends on but doesn't control | "IndexedDB is available", "the user has a desktop browser" |
| Decisions | Choices we made, with rationale | "*Persistence.* **IndexedDB.** Local-first…" |
| Open questions | Choices we haven't yet made, or facts we haven't yet learned | "*Codegen tool.* JSON Schema → Valibot has no chosen tool. Open until the second consumer arrives." |

If something is in Decisions but reads like an Assumption ("we assume IndexedDB is available"), it's mis-categorised. Move it.

If something is in Open questions but is actually decided ("*Quota exhaustion handling.* No defined behaviour at MVP."), it's a Decision in disguise. Phrase it as a question or move it to Decisions.

---

## When the spec contradicts the code

Sometimes investigation reveals the code does X but a previous doc says Y. Two options:

1. **Spec the code.** Describe what's there, write a Decision recording why X (if you know), and add an Open question if you don't.
2. **Flag the divergence to the user.** "The code does X but the previous doc says Y; which is canonical?" The user can either: confirm X and update the spec, or open a separate plan to bring the code to Y.

Don't invent a third reality that's neither code nor previous doc. The spec describes one thing.

---

## Length and rhythm

Specs are read top to bottom. Help the reader by:

- Using a **short intro paragraph** at the top of every page that names what the page covers and points at related pages.
- Using `---` between major sections to give the eye breaks.
- Using **tables** for any list with parallel structure (routes, tokens, fields, limits).
- Using **ASCII diagrams** for shapes and flows.
- Using **single-purpose code blocks** — JSON for schema, TypeScript for type signatures, shell for commands. Don't mix in one block.

Long paragraphs are a code smell in specs. If a paragraph is more than 4 sentences, it's probably two paragraphs or a list.
