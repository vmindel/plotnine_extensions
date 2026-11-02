# Claude Code skill

plotnine-extensions ships an
[Agent Skill](https://docs.claude.com/en/docs/claude-code/skills) for
[Claude Code](https://claude.com/claude-code). It teaches the agent each
feature's arguments, defaults, and the mistakes that give a wrong figure
without an error.

## Install

Claude Code does not look inside installed Python packages for skills, so
copy it once:

```bash
plotnine-extensions-install-skills
```

This installs to `~/.claude/skills/plotnine-extensions/`, available in
every project from the next session on.

| command | effect |
|---|---|
| `plotnine-extensions-install-skills` | install to `~/.claude/skills/plotnine-extensions` |
| `plotnine-extensions-install-skills --dest .claude/skills/plotnine-extensions` | install into the current project only |
| `plotnine-extensions-install-skills --force` | overwrite, e.g. after upgrading |
| `plotnine-extensions-install-skills --print-path` | print where the bundled copy is |

Then ask in plain language: "label the top genes on this volcano plot
without overlaps", "add Holm-corrected t-test brackets against WT",
"raincloud of expression by condition, horizontal", "logo of these
contribution scores for this sequence", "make this 200k-point scatter a
small PDF".

## What's inside

A short router, `SKILL.md`, sends the agent to one reference file, which
it reads only when the task needs it.

| file | covers |
|---|---|
| `references/repel.md` | `geom_text_repel`, `geom_label_repel` |
| `references/rasterise.md` | `rasterise` |
| `references/signif.md` | `stat_compare_means`, `geom_bracket`, `p_adjust`, `format_p` |
| `references/distributions.md` | `stat_halfeye`, `geom_raincloud`, `stat_pointinterval`, `position_jitternudge` |
| `references/logo.md` | `geom_logo`, `logo_data`, palettes |
| `references/geoms.md` | `geom_curve`, `geom_hex`, `stat_bin_hex`, `hex_bins` |

The test suite checks that:

- every reference file is routed;
- every `pnx.` name in the skill exists;
- every public function is covered;
- every keyword in its signature blocks is a real parameter;
- the install command works.
