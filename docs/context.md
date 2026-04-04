# context

## Summary

`context` provides a compact TUI overview of what Pi currently has loaded and how much context is being used.

## What it adds

- Command: `/context`

## How it works

It builds a live overview of:

- loaded skills
- registered extension commands (best effort)
- project context files such as `AGENTS.md` and `CLAUDE.md`
- approximate token size for loaded context files
- current context window usage
- session totals such as token and cost information when available

It also records skill-load events in session entries so the display can show which skills were actually loaded during the session.

## Usage

Use `/context` when you want to quickly inspect the runtime environment before starting work or when debugging why Pi knows or does not know something.

## Examples

- `/context`

## Files and state

- Reads context files from the global agent directory and from the current project ancestry
- Persists custom session entries under `context:skill_loaded`

## Notes / caveats

- Token counts are estimates for file content size, not exact provider tokenization
- Extension discovery is best effort, based partly on registered commands and available metadata
