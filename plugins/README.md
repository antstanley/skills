# Plugin publishing

`catalog.json` is the source of truth for plugin names, versions, descriptions,
authors, catalog order, and presentation metadata. Skill content remains in
`<plugin>/skills/`; shared security resources remain in `security/`.

Run `uv run python scripts/sync-plugins.py` from the repository root after editing
the catalog. It generates both platform manifests for each plugin and both catalogs:

- `plugins/<name>/.claude-plugin/plugin.json`
- `plugins/<name>/.codex-plugin/plugin.json`
- `.claude-plugin/marketplace.json`
- `.agents/plugins/marketplace.json`

Do not edit generated publishing files. Both platforms receive the same plugin name
and semver version; Codex adds interface metadata and an explicit `./skills/` path.
Catalog paths resolve from the repository root. The Codex catalog exposes each plugin
as available with authentication policy `ON_INSTALL`; these skill-only packages declare
no app, MCP server, or credentials. Installation does not grant execution permissions.

## Updating and testing

1. Edit canonical skills and metadata. Increment the affected plugin's version once
   in `catalog.json`; a compatible new capability uses a minor bump and a fix uses a
   patch bump. New dual-platform distribution is a minor release for all six plugins.
2. Run `uv run python scripts/sync-plugins.py` and `scripts/sync-skills.sh`.
3. Run `scripts/check.sh`. It validates catalog shape, generated-file parity, shared
   identities, archive contents, formatting, typing, and the test suite.
4. Register this checkout for Codex with `codex plugin marketplace add /absolute/path/to/skills`.
   Install a plugin with `codex plugin add spec-creator@skills` and try it in a new thread.
   Avoid simultaneously installing the same skills through `install.sh` in that test profile.
5. Test the same behaviors in Claude Code using its marketplace installation. Validate
   discovery, relative resources, user interaction, and independent agent gates; loading
   a manifest alone does not establish behavioral compatibility.

The generator defines this repository's supported skills-only metadata subset, not
the entire upstream plugin schema. Adding hooks, MCP servers, or app integrations
requires an explicit extension and separate runtime testing.

## Release

Merge a reviewed PR with green CI, then create one GitHub release targeting the merged
commit. The marketplace tag is independent of plugin versions. Publishing the release
runs `.github/workflows/release.yml`, which checks that tagged tree and uploads one
`<plugin>-<version>.tar.gz` per plugin plus `SHA256SUMS`. Each archive includes both
manifests and the same skills/resources; caches, eval fixtures, and symlinks are excluded
(resource symlinks fail packaging). The source archive retains the full marketplace and
flat installer. No public-directory submission is performed by the release workflow.

To inspect archives locally:

```sh
uv run python scripts/sync-plugins.py --check --archive-dir /tmp/skills-archives
```

Delete task-specific archives after testing. The security archive preserves its
Apache-2.0 license and bundled scripts, schemas, references, examples, and assets.

## Runtime portability

Use provider-neutral instructions for shared behavior and host-specific instructions
only for actual tool differences. Spec-builder documents Codex dispatch in its
`references/portability.md`; security documents resource resolution and user-input tools
in `references/runtime.md`. Never assume installing a plugin creates an agent-spawn
tool, Python environment, or permission to write externally.

The flat tree still uses real copies. Its security skills reference the generated
`skills/.security-plugin/` bundle, which `install.sh` carries alongside installed skills.
The bundle has an ownership marker; the installer refuses to overwrite an unowned
directory at that path.

References: [OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins)
and [Claude conversion guidance](https://developers.openai.com/plugins/guides/submit-claude-plugin).
