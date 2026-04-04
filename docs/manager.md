# manager

## Summary

`manager` provides an interactive skill manager for installing, updating, and removing skills from the repository skill library.

## What it adds

- Command: `/skills`
- Reusable exported helpers used by other extensions:
  - `listInstalledSkills()`
  - `installManagedSkills()`
  - related cache/path helpers

## How it works

- Clones or refreshes a shallow cache of the skills repository into a temporary cache directory
- Copies selected skills into the project-local skills directory:
  - `.agents/skills`
- Provides a TUI overlay for:
  - install
  - update
  - remove
- Reloads Pi after changes so installed skills become available immediately

## Usage

Use `/skills` when you want to manage project-local skills without doing manual file copies.

## Examples

- `/skills`
- install `scientific-audit` for use with `audit-enforcer`
- update all installed local skills

## Files and state

- Temporary cache: OS temp directory under `bio-skills-cache`
- Local installed skills: `.agents/skills`
- Reads from the repository `skills/` directory on GitHub

## Notes / caveats

- Requires git and GitHub access
- The current command description still references the old repository name in some places and should stay aligned with the configured remote
- Other extensions may depend on these exported helpers for automatic skill installation
