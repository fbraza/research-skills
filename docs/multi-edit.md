# multi-edit

## Summary

`multi-edit` replaces Pi's built-in `edit` tool with a more capable version that supports batch edits and Codex-style patches.

## What it adds

- Tool override: `edit`

## How it works

The extension keeps the standard exact-replacement behavior and adds:

- top-level single edit support
- `multi` edit arrays for multiple replacements across one or more files
- `patch` support for Codex-style `*** Begin Patch` payloads
- preflight validation on a virtual workspace before any real file mutation
- diff output and first changed line metadata for tooling/UI integration

## Usage

Use the `edit` tool exactly as usual, but with the added `multi` and `patch` options when needed.

## Examples

- single edit with `path`, `oldText`, `newText`
- batched replacements with `multi`
- patch-based file updates with `patch`

## Files and state

- No persistent state
- Works directly on project files after virtual preflight succeeds

## Notes / caveats

- Exact-match replacements still require the source text to match precisely
- Patch mode is mutually exclusive with the classic edit fields
- Preflight reduces accidental corruption but does not replace careful review
