# prompt-editor

## Summary

`prompt-editor` manages reusable prompt modes, including model, provider, thinking level, and optional visual styling.

## What it adds

- Command: `/mode`
- Shortcuts:
  - `Ctrl+Shift+M` — open mode selector
  - `Ctrl+Space` — cycle modes
- Session/model event hooks to keep mode state synchronized

## How it works

- Stores mode definitions in JSON files
- Supports global and project-local mode files
- Tracks a current mode plus a `custom` overlay state when the user manually changes model selection
- Applies mode settings back into the editor/runtime
- Uses file locking and atomic writes to avoid corrupting mode files

## Usage

Use this when you switch between different prompting/model configurations frequently and want named presets.

## Examples

- `/mode`
- `/mode default`
- `/mode store review`
- `Ctrl+Space` to cycle through existing modes

## Files and state

- Global modes: `~/.pi/agent/modes.json`
- Project modes: `.pi/modes.json`
- Uses adjacent lock files during writes

## Notes / caveats

- Manual model changes push runtime state into a temporary `custom` overlay mode
- Behavior depends on the current Pi model registry and available models
- This extension manages both UI behavior and persisted mode configuration
