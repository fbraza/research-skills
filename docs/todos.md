# todos

## Summary

`todos` provides file-based todo management for Pi, with both an LLM-callable tool and an interactive TUI command.

## What it adds

- Tool: `todo`
- Command: `/todos`

## How it works

- Stores each todo as a standalone markdown file
- Uses a JSON front matter block followed by markdown body text
- Supports locking to reduce concurrent edit conflicts
- Provides tool actions for:
  - `list`
  - `list-all`
  - `get`
  - `create`
  - `update`
  - `append`
  - `delete`
  - `claim`
  - `release`
- Provides a TUI todo browser and action menu via `/todos`

## Usage

Use this when you want persistent task tracking inside a Pi project or when another extension needs structured todo storage.

## Examples

- `/todos`
- `todo({ action: "create", title: "Add tests", body: "..." })`
- `todo({ action: "claim", id: "TODO-deadbeef" })`

## Files and state

- Default todo directory: `.pi/todos`
- Override with: `PI_TODO_PATH`
- Settings file: `settings.json` inside the todo directory
- Uses `.lock` files for active edits

## Notes / caveats

- Todo IDs are file-backed and shown as `TODO-<hex>`
- Closed todos may be garbage-collected based on settings
- Other extensions, such as `audit-enforcer`, can integrate with the same todo storage
