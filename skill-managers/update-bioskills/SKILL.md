---
name: update-bioskills
description: "Update installed bio-skills from github.com/fbraza/bio-skills to their latest version."
argument-hint: "[--all | skill-name1 skill-name2 ...] or leave blank for interactive selection"
---

# Update Bio-Skills

Update previously installed bio-skills to the latest version from the **fbraza/bio-skills** GitHub repository.

**Source repository:** `https://github.com/fbraza/bio-skills`

## How This Works

1. Clone the bio-skills repo (shallow clone)
2. Identify which installed skills have updates available
3. Update selected skills in place
4. Optionally update knowhows and CLAUDE.md

## Instructions

### Step 1: Clone the repo

```bash
BIOSKILLS_TMP=$(mktemp -d)
git clone --depth 1 https://github.com/fbraza/bio-skills.git "$BIOSKILLS_TMP/bio-skills"
```

If `git clone` fails, try with `gh`:
```bash
gh repo clone fbraza/bio-skills "$BIOSKILLS_TMP/bio-skills" -- --depth 1
```

### Step 2: Identify installed skills

```bash
ls .claude/skills/ 2>/dev/null
```

Exclude `knowhows/` and any directories that don't exist in the remote repo (user-created skills — never touch these).

Build a list of skills that exist **both** locally and in the remote repo. These are the updatable skills.

If no skills are installed, tell the user and suggest running `/install-bioskills` instead. Stop here.

### Step 3: Determine what to update

**If `$ARGUMENTS` contains `--all`:**
- Update ALL installed skills that exist in the remote repo. No prompting needed.
- Also update knowhows.

**If `$ARGUMENTS` contains specific skill names (e.g., `scvi-tools-scrna bulk-rnaseq-counts-to-de-deseq2`):**
- Update only those named skills.
- Validate each name is actually installed locally. If not installed, warn and skip.
- Validate each name exists in the remote repo. If not in remote, warn and skip.

**If `$ARGUMENTS` is empty (interactive mode):**
- List all updatable skills (installed + exists in remote).
- Ask the user which skills to update. They can select individual skills or say "all".

### Step 4: Update selected skills

For each selected skill:

1. **Replace the skill directory contents:**
   ```bash
   rm -rf ".claude/skills/<skill-name>/"
   mkdir -p ".claude/skills/<skill-name>"
   cp -R "$BIOSKILLS_TMP/bio-skills/skills/<skill-name>/." ".claude/skills/<skill-name>/"
   ```

2. **Verify the update:**
   - `.claude/skills/<skill-name>/SKILL.md` must exist after copy
   - If verification fails, warn the user and continue with remaining skills

3. Print "⟳ Updated <skill-name>"

### Step 5: Update knowhows

**If `--all` was used**, update knowhows automatically:

```bash
mkdir -p .claude/skills/knowhows
cp -R "$BIOSKILLS_TMP/bio-skills/skills/knowhows/." ".claude/skills/knowhows/"
```

**Otherwise**, ask the user: "Also update knowhow guides? (Y/n)"

Print "⟳ Updated knowhows (N guides)" or "⏭ Skipped knowhows"

### Step 6: Handle CLAUDE.md

Ask the user: "Update CLAUDE.md from the latest bio-skills version?"
- **Replace:** Overwrite the existing CLAUDE.md with the remote version
- **Skip:** Don't touch the existing CLAUDE.md (default)

If `--all` was used, still ask about CLAUDE.md — it may contain user customizations.

### Step 7: Cleanup and report

```bash
rm -rf "$BIOSKILLS_TMP"
```

Print a summary:
```
============================================================
Bio-Skills Update Complete
============================================================
  Skills updated: <count> (<comma-separated list>)
  Skills skipped: <count> (<comma-separated list or "none">)
  Knowhows: updated / skipped
  CLAUDE.md: replaced / skipped
============================================================
```

## Important Notes

- **Only updates skills that exist both locally and in the remote repo.** Never deletes user-created skills.
- **Never touches skills that are not in the remote repo** — those are user-created and must be preserved.
- **CLAUDE.md always requires explicit confirmation** even with `--all`, because it may contain user customizations.
- **Requires `git`** and internet connection.
- **Shallow clone** (`--depth 1`) for speed.
- **Clean up** the temp directory after update, even if errors occur.
