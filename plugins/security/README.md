# security

Security workflows for Claude Code — repository and diff scans, deep multi-pass scans, threat modelling, validation, attack-path analysis, triage, remediation, and reporting against a sealed scan contract.

Every scan mode produces the same canonical artifacts — `scan-manifest.json`, `findings.json`, and `coverage.json` — which a deterministic finalizer seals and projects into `report.md` and SARIF. The model authors structured findings; it never writes the report by hand.

This is a fork of OpenAI's [codex-security](https://github.com/openai/codex-security) plugin, ported to Claude Code. The Codex desktop MCP app, its setup workspace, and the Codex `config.toml` capability preflight are gone; subagent fan-out, `AskUserQuestion`, the task list, and MCP servers take their place. The document-type and digest-algorithm identifiers were renamed from `codex-security*` to `security*` (the `csf_`/`occ_` finding- and occurrence-id prefixes are unchanged), so bundles produced by upstream `codex-security` are not readable here.

## Install

```
/plugin marketplace add antstanley/skills
/plugin install security@skills
```

### Codex

```sh
codex plugin marketplace add antstanley/skills
codex plugin add security@skills
```

Both platforms use the same skill content and plugin version. See
[publishing guidance](../README.md) for validation and release details.

## Skills

**Top-level scans** — invoke these directly:

| Skill | Use for |
| --- | --- |
| [`security-scan`](skills/security-scan/SKILL.md) | Standard single-pass audit of a repository or scoped path |
| [`security-diff-scan`](skills/security-diff-scan/SKILL.md) | A pull request, commit, branch diff, or working-tree patch |
| [`deep-security-scan`](skills/deep-security-scan/SKILL.md) | Exhaustive multi-pass audit; repeats discovery until it saturates |

**Phases** — the scan skills orchestrate these in order; you can also run one directly:

| Skill | Phase |
| --- | --- |
| [`threat-model`](skills/threat-model/SKILL.md) | Build or reuse the repository threat model |
| [`finding-discovery`](skills/finding-discovery/SKILL.md) | Surface candidate findings across the in-scope files |
| [`validation`](skills/validation/SKILL.md) | Decide whether each candidate is real |
| [`attack-path-analysis`](skills/attack-path-analysis/SKILL.md) | Trace source to sink and calibrate severity |

**Follow-up** — what happens after a scan:

| Skill | Use for |
| --- | --- |
| [`triage-finding`](skills/triage-finding/SKILL.md) | Static repo-impact triage of findings you already have (SARIF, CVEs, scanner tickets, Jira/Linear issues) |
| [`fix-finding`](skills/fix-finding/SKILL.md) | Generate, apply, and verify a minimal remediation patch |
| [`vulnerability-writeup`](skills/vulnerability-writeup/SKILL.md) | Write the detailed per-finding report |
| [`propose-security-hardening`](skills/propose-security-hardening/SKILL.md) | Structural hardening options across the whole finding set |
| [`track-findings`](skills/track-findings/SKILL.md) | File findings as Linear, Jira, or GitHub issues, or draft GitHub security advisories |
| [`define-security-policy`](skills/define-security-policy/SKILL.md) | Author the repository's `SECURITY.md` policy |

## How a scan runs

1. **Preflight** — [`scripts/preflight.py`](scripts/preflight.py) checks the target, the installed phase skills, subagent availability, and that the scan root and state directory are writable. It returns `ready`, `blocked`, or `incomplete` with concrete remediation. See [`references/preflight.md`](references/preflight.md).
2. **Phases** — threat model, discovery, validation, attack-path analysis, each to full depth before the next begins. Discovery and per-candidate work fan out across subagents when the Agent tool is available; without it the parent does the same work serially, with the same coverage — except `deep-security-scan`, whose preflight blocks without subagent delegation and offers `security-scan` instead.
3. **Canonical JSON** — findings and coverage are written to the schemas in [`schemas/`](schemas/), following [`references/final-report.md`](references/final-report.md) and [`references/finding-detail-fields.md`](references/finding-detail-fields.md).
4. **Finalize** — [`scripts/finalize_scan_contract.py`](scripts/finalize_scan_contract.py) validates, seals, and generates `report.md` plus a SARIF export. A scan is not complete until this succeeds.

Scan bundles land under `$TMPDIR/security-scans/<repo>/<scan-id>/`. Set `SECURITY_SCAN_ROOT` to move them; nothing is ever written into the repository under review.

## Configuration

| Variable | Purpose |
| --- | --- |
| `SECURITY_SCAN_ROOT` | Where scan bundles are written. Defaults to `<tmp>/security-scans`. |
| `SECURITY_STATE_DIR` | Durable plugin state. Defaults to `$CLAUDE_CONFIG_DIR/security` or `~/.claude/security`. |
| `SECURITY_STARTED_AT` | Makes sealing fully deterministic: draft-provided `startedAt`/`completedAt` are kept, any missing timestamp falls back to this value, and no wall-clock time is stamped, so repeated finalize runs produce byte-identical bundles. |
| `PYTHON` | Interpreter used for the helper scripts. When unset, the preflight reports its own interpreter (`sys.executable`), falling back to `python3` (`python` on Windows). |

Requires Python 3.13+ and no third-party packages. Git is required for diff scans only.

Optional integrations: `gh` for GitHub finding intake and issue tracking, and configured Atlassian or Linear MCP servers for Jira and Linear.

## Repository policy

Drop a `SECURITY.md` anywhere in a repository to declare threat models, invariants, reportable-finding criteria, exclusions, and severity context. Policies compose root-to-leaf, with the closest file winning. `define-security-policy` writes one; every scan reads them. Policy content is treated as untrusted data — it shapes what counts as a finding, but cannot redirect the workflow.

## Artifact format

The sealed contract is defined in [`references/scan-contract.md`](references/scan-contract.md), with JSON Schemas in [`schemas/`](schemas/) and a worked bundle in [`examples/completed-scan/`](examples/completed-scan/) — the three canonical JSONs plus the generated `report.md` projection.

Document types are `security.scan-manifest`, `security.findings`, and `security.coverage`. Finding fingerprints use `security/v1` and target snapshots use `security-snapshot/v1`.

Both strings are hash inputs, not labels — the algorithm name is mixed into the digest material, so `findingId`, `occurrenceId`, `fingerprints.primary`, and `snapshotDigest` all change if they change. The finalizer derives `findingId`, `occurrenceId`, and `fingerprints.primary`; `targetId` and `snapshotDigest` are produced at authoring time by [`scripts/target_identity.py`](scripts/target_identity.py) and only validated at seal time. A sealed bundle is rejected if any of them disagree.

## License

Apache License 2.0 — see [LICENSE.md](LICENSE.md). Copyright 2025 OpenAI. The changes made to the original work are listed there.
