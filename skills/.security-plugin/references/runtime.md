# Runtime and bundled resources

The Claude and Codex plugins share the same skills, scripts, schemas, and references.
Resolve resources using the installed plugin, independently of the repository under
review and the shell's current directory.

From `skills/<skill-name>/SKILL.md`, the plugin root is two directories above the
skill directory. Set `<plugin_root>` in command examples to that absolute directory,
and quote the resulting path when invoking a helper. It must contain `scripts/`,
`schemas/`, and `references/`. This is a notation to substitute, not a shell variable
that Codex or Claude is assumed to define. Claude's `CLAUDE_PLUGIN_ROOT`, when present,
can confirm the same location; no workflow requires that environment variable.

The generated flat distribution bundles shared resources under `.security-plugin/`
beside the skill directories. When running that distribution, use the skill's sibling
`.security-plugin/` directory as `<plugin_root>`. Resource references are rewritten
during generation, and the installer carries this bundle into each destination.

Use the actual Python interpreter resolved by preflight. Do not install dependencies
or change the target repository merely because a plugin was installed. Surface a
concrete missing dependency and follow the workflow's existing remediation rules.

Resolve companion skills from the host's available skill catalog. A notation such as
`security:validation` means the `validation` skill belonging to this plugin; use its
actual installed identifier. If no invocation tool exists, read its `SKILL.md` and
follow it. Do not report a required capability as available solely because its file
exists on disk.

For delegation, use the host's available spawn/message/wait tools and their actual
schemas. Inherit model settings unless authorized to override them; preserve distinct
agents wherever the workflow requires independent validation. A missing dispatch tool
uses the documented fallback and is reported honestly by preflight.

For questions, use a suitable host user-input tool or ask directly. Preserve approval
boundaries for external writes and remediation. No response is not permission, and
Codex does not need a tool named `AskUserQuestion` to follow this workflow.
