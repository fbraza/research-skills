# audit-enforcer

## Summary

`audit-enforcer` helps run the `scientific-audit` skill, parses its verdict and issue list, and syncs findings into the todo system.

## What it adds

- Commands:
  - `/audit`
  - `/audit-resolve`
- Footer status updates showing the latest audit verdict and open audit todo count
- Session hooks for restoring and persisting audit state

## How it works

- `/audit` sends a prompt that asks Pi to run `/skill:scientific-audit`
- Before doing that, it checks whether the `scientific-audit` skill is installed locally
- If the skill is missing, it offers to install it using the manager extension cache, reloads Pi, and retries `/audit`
- After the audit response arrives, it parses:
  - `**Verdict**: PASS|REVIEW|FAIL`
  - a simplified `## Issues` list
  - or structured sections such as critical issues, warnings, and suggestions
- Each issue is fingerprinted and synced into `.pi/todos` (or `PI_TODO_PATH`)
- `/audit-resolve` lets the user select open audit todos and mark them done

## Usage

Use this when you want a repeatable audit workflow around the `scientific-audit` skill and want issues tracked as actionable todos.

## Examples

- `/audit`
- `/audit normalization and duplicate handling`
- `/audit-resolve`

## Files and state

- Persists runtime state in a custom session entry: `audit-enforcer-state`
- Writes audit findings into:
  - `.pi/todos`
  - or the directory pointed to by `PI_TODO_PATH`

## Notes / caveats

- Depends on the `scientific-audit` skill
- Depends on the manager extension install path for automatic skill installation
- Assumes audit responses follow one of the expected verdict/issue formats
- Integrates with the same todo file layout used by the `todos` extension
