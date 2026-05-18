# reasoning-semiformally

Apply semi-formal certificate reasoning to code analysis — patch verification, fault localization, and patch equivalence.

Use when reviewing patches, hunting bugs across scopes, comparing fixes, or when code reasoning requires tracing execution across files or modules. Triggers on code review, bug localization, patch comparison, name shadowing, scope analysis, and regression checking.

## Install

```
/plugin marketplace add antstanley/skills
/plugin install reasoning-semiformally@skills
```

## Skill content

The skill itself lives at [`skills/reasoning-semiformally/SKILL.md`](skills/reasoning-semiformally/SKILL.md). Model-specific procedural detail is in [`haiku.md`](skills/reasoning-semiformally/haiku.md) (Haiku-class) and [`sonnet.md`](skills/reasoning-semiformally/sonnet.md) (Sonnet/Opus-class).
