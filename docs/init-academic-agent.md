# init-academic-agent

## Summary

`init-academic-agent` downloads or updates a project `AGENTS.md` file from a GitHub repository.

## What it adds

- Command: `/init-academic-agent`

## How it works

- Infers the target GitHub repository from `git remote.origin.url` if no repository is passed explicitly
- Defaults to downloading `agent-context/AGENTS.md`
- Writes the result to `AGENTS.md` at the project root unless another destination is provided
- Uses the GitHub API first, then falls back to `gh api`
- Asks for confirmation before overwriting an existing file unless `--force` is used

## Usage

Use this when bootstrapping a project with the repository's academic `AGENTS.md` guidance or when refreshing an existing local copy.

## Examples

- `/init-academic-agent`
- `/init-academic-agent fbraza/research-skills`
- `/init-academic-agent fbraza/research-skills agent-context/AGENTS.md`
- `/init-academic-agent fbraza/research-skills agent-context/AGENTS.md docs/ACADEMIC-AGENTS.md`
- `/init-academic-agent --force`

## Files and state

- Reads git metadata from the current repository
- Writes a destination markdown file, usually `AGENTS.md`
- Uses GitHub credentials from `GITHUB_TOKEN`, `GH_TOKEN`, or `GITHUB_PAT` when available

## Notes / caveats

- For private repositories, GitHub access must be configured
- If repo inference fails, you must pass `owner/repo` explicitly
- This extension updates files in the current project, so review overwrite prompts carefully
