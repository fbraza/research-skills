---
name: install-bioskills
description: "Install all bio-skills (skills + knowhows) from github.com/fbraza/bio-skills to ~/.claude/skills/ for global availability in any project."
---

# Install Bio-Skills

Install **all** scientific analysis skills and knowhow guides from the **fbraza/bio-skills** GitHub repository to `~/.claude/skills/`. Skills installed here are globally available in every Claude session and every project.

**Source repository:** `https://github.com/fbraza/bio-skills`
**Install target:** `~/.claude/skills/`

## How This Works

1. Clone the bio-skills repo to a temporary directory (shallow clone)
2. Copy all skills and knowhows into `~/.claude/skills/`
3. Existing skills are overwritten silently (re-running = updating to latest)
4. Clean up the temp directory

No arguments needed — always installs everything.

## Instructions

### Step 1: Clone the repo

```bash
BIOSKILLS_TMP=$(mktemp -d)
gh repo clone fbraza/bio-skills "$BIOSKILLS_TMP/bio-skills" -- --depth 1
```

Verify the clone worked:
```bash
ls "$BIOSKILLS_TMP/bio-skills/skills/"
```

If `gh` fails, fall back to:
```bash
git clone --depth 1 https://github.com/fbraza/bio-skills.git "$BIOSKILLS_TMP/bio-skills"
```

### Step 2: Ensure global skills directory exists

```bash
mkdir -p ~/.claude/skills/
```

### Step 3: Install all skills

List all skill directories from the repo, excluding `knowhows/`:

```bash
ls -d "$BIOSKILLS_TMP/bio-skills/skills/*/ | xargs -I{} basename {}
```

For each skill (excluding `knowhows`):

```bash
cp -R "$BIOSKILLS_TMP/bio-skills/skills/<skill-name>" ~/.claude/skills/
```

**Always overwrite** existing skills — this keeps the global installation in sync with the repo.

### Step 4: Install knowhows

```bash
mkdir -p ~/.claude/skills/knowhows
cp -R "$BIOSKILLS_TMP/bio-skills/skills/knowhows/." ~/.claude/skills/knowhows/
```

### Step 5: Verify installation

```bash
ls ~/.claude/skills/*/SKILL.md 2>/dev/null | wc -l
```

The count should match the number of skills in the repo (excluding knowhows).

Also verify knowhows were copied:
```bash
ls ~/.claude/skills/knowhows/ | wc -l
```

If any SKILL.md is missing, warn the user and continue.

### Step 6: Cleanup and report

```bash
rm -rf "$BIOSKILLS_TMP"
```

Print a summary:
```
============================================================
Bio-Skills Installation Complete
============================================================
  Skills installed: <count>
  Knowhows: <count> guides
  Location: ~/.claude/skills/
  Scope: global (available in all projects)
============================================================
```

## Important Notes

- **No CLAUDE.md handling.** This skill only installs skills and knowhows. To set up a project with CLAUDE.md, use `/init-bioproject`.
- **Always overwrites.** Re-running this skill updates all skills to the latest version from the repo. No prompting, no confirmation needed.
- **Global scope.** Skills are installed to `~/.claude/skills/` and are available in every Claude session and project.
- **Do NOT touch project-local files** (no `.claude/` in the current working directory, no `CLAUDE.md`).
- **Requires `git`** and internet connection.
- **Shallow clone** (`--depth 1`) for speed.
- **Clean up** the temp directory after installation, even if errors occur.
