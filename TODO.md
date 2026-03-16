# TODO

## Architecture — Subagents vs. Skills

- [ ] Extract `knowhows/` folder out of `.claude/skills/` and give it its own dedicated location under `.claude/`?
- [ ] Are any of the 9 subagents currently redundant with each other, or do you feel some roles are underused in practice?
- [ ] Should the subagent definitions reference their corresponding skill guides directly (e.g., The Analyst explicitly loads `scrnaseq-scanpy-core-analysis` when relevant)?
- [ ] Create a visual map of how Aria orchestrates the subagents and when each skill gets loaded, to validate the current design?
