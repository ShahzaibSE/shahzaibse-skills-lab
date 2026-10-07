# Upstream

- Repository: https://github.com/nextlevelbuilder/ui-ux-pro-max-skill
- Path: `.claude/skills/ui-ux-pro-max/`
- Commit: `477bcb2`
- Version: 2.13.0
- License: MIT (see upstream repository; no attribution changed)

## Local changes

1. `SKILL.md`: 11 script invocations changed from
   `${CLAUDE_PLUGIN_ROOT}/.claude/skills/ui-ux-pro-max/scripts/...` to
   `${CLAUDE_SKILL_DIR}/scripts/...`.
2. `scripts/tests/` omitted (not used at runtime; cannot run outside the upstream repo).

Everything else is byte-identical to upstream.

## Why

`${CLAUDE_PLUGIN_ROOT}` is substituted only in plugin skills. This skill is installed as a
personal Skills Lab skill (exposed via `~/.claude/skills/`), where that variable is unset and
the original commands resolve to `/.claude/skills/...`. `${CLAUDE_SKILL_DIR}` is the
documented Claude Code substitution for a skill's own directory in personal, project and
plugin skills.

## Future upstream updates

Re-check whether upstream still uses `${CLAUDE_PLUGIN_ROOT}` in `SKILL.md`. If so, re-apply
the substitution above; if upstream has switched to a skill-relative form, drop this
workaround and this note's item 1.
