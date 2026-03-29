---
name: install-bioskills
description: "Install bio-skills (scientific analysis skills, CLAUDE.md, knowhows) from github.com/fbraza/bio-skills into the current project."
argument-hint: "[--all | skill-name1 skill-name2 ...] or leave blank for interactive selection"
---

# Install Bio-Skills

Install scientific analysis skills, CLAUDE.md, and knowhow guides from the **fbraza/bio-skills** GitHub repository into the current project.

**Source repository:** `https://github.com/fbraza/bio-skills`

## How This Works

1. Clone the bio-skills repo to a temporary directory (shallow clone for speed)
2. Present available skills to the user (or install all with `--all`)
3. Copy selected items into the current project:
   - Skills → `.claude/skills/<skill-name>/` (each skill's full directory: SKILL.md + scripts/ + references/ + assets/)
   - Knowhows → `.claude/skills/knowhows/`
   - CLAUDE.md → project root `CLAUDE.md`

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

Verify the clone worked:
```bash
ls "$BIOSKILLS_TMP/bio-skills/skills/"
```

### Step 2: Determine what to install

**If `$ARGUMENTS` contains `--all`:**
- Install ALL skills, knowhows, and CLAUDE.md. No prompting needed.

**If `$ARGUMENTS` contains specific skill names (e.g., `scvi-tools-scrna spatial-transcriptomics`):**
- Install only those named skills + knowhows + CLAUDE.md.
- Validate each name exists in the repo. If a name doesn't match, warn and skip it.

**If `$ARGUMENTS` is empty (interactive mode):**
- List all available skills from the repo with a brief description (read each SKILL.md frontmatter `short-description` field).
- Ask the user which skills they want to install. They can select individual skills or say "all".
- Always include knowhows and CLAUDE.md in the installation.

### Step 3: Install skills

**Before installing, check what already exists:**

```bash
ls .claude/skills/ 2>/dev/null
```

**The `.claude/skills/` directory may already contain previously installed skills or user-created skills. NEVER delete or overwrite existing content — only ADD new skills.**

For each selected skill:

1. **Check if the skill already exists:**
   ```bash
   ls .claude/skills/<skill-name>/SKILL.md 2>/dev/null
   ```

2. **If the skill does NOT exist** — install it:
   ```bash
   mkdir -p .claude/skills/<skill-name>
   cp -R "$BIOSKILLS_TMP/bio-skills/skills/<skill-name>/." ".claude/skills/<skill-name>/"
   ```
   Print "✓ Installed <skill-name>"

3. **If the skill ALREADY exists** — ask the user:
   - "<skill-name> already exists in .claude/skills/. **Update** (overwrite this skill only) or **Skip**?"
   - If Update: overwrite only that skill's directory, nothing else
   - If Skip: leave it untouched
   - Print "⟳ Updated <skill-name>" or "⏭ Skipped <skill-name>"

**Verify each installed/updated skill:**
- `.claude/skills/<skill-name>/SKILL.md` must exist
- If verification fails, warn and continue with remaining skills

### Step 4: Install knowhows

**Knowhows are always safe to update** (they are reference guides, not user-customized content):

```bash
mkdir -p .claude/skills/knowhows
cp -R "$BIOSKILLS_TMP/bio-skills/skills/knowhows/." ".claude/skills/knowhows/"
```

Print "✓ Installed knowhows (N guides)"

### Step 5: Handle CLAUDE.md

Check if a `CLAUDE.md` already exists at the project root.

**If CLAUDE.md does NOT exist:**
- Copy it directly: `cp "$BIOSKILLS_TMP/bio-skills/CLAUDE.md" ./CLAUDE.md`
- Print "✓ Installed CLAUDE.md"

**If CLAUDE.md ALREADY exists:**
- Ask the user: "A CLAUDE.md already exists in this project. How should I handle the bio-skills CLAUDE.md?"
  - **Merge:** Append the bio-skills CLAUDE.md content under a `# Bio-Skills Configuration` header at the end of the existing file
  - **Replace:** Overwrite the existing CLAUDE.md entirely
  - **Skip:** Don't touch the existing CLAUDE.md
- Do what the user chooses.

### Step 6: Cleanup and report

```bash
rm -rf "$BIOSKILLS_TMP"
```

Print a summary:
```
============================================================
Bio-Skills Installation Complete
============================================================
  Skills installed: <count> (<comma-separated list>)
  Knowhows: <count> guides
  CLAUDE.md: installed / merged / skipped
  Location: .claude/skills/
============================================================
```

## Important Notes

- **Additive only:** Installation MUST only add new skills. Never delete, overwrite, or replace existing skills or files in `.claude/skills/` without explicit user confirmation per item.
- **Requires `git` on the system.** If git is not available, tell the user to install it.
- **Internet connection required** to clone from GitHub.
- **Do NOT modify any existing project files** other than CLAUDE.md (when user chooses merge/replace).
- **Do NOT delete existing skills** in `.claude/skills/` that are not part of bio-skills.
- **Do NOT bulk-overwrite `.claude/skills/`** — always operate at the individual skill directory level.
- **Shallow clone** (`--depth 1`) for speed — we don't need git history.
- **Clean up** the temp directory after installation, even if errors occur.
