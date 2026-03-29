---
name: list-bioskills
description: "List available bio-skills from the remote repo and show which are already installed locally."
argument-hint: "[--remote | --local | --all]"
---

# List Bio-Skills

Show available and/or installed bio-skills. Compares the remote repository against the local `.claude/skills/` directory.

**Source repository:** `https://github.com/fbraza/bio-skills`

## Instructions

### Step 1: Determine mode from arguments

- `--remote` → show only skills available in the remote repo
- `--local` → show only skills installed locally
- `--all` (or no arguments) → show both, with install status

### Step 2: Gather local skills

```bash
ls .claude/skills/ 2>/dev/null
```

Exclude `knowhows/` from the skill list — knowhows are reference guides, not skills.

### Step 3: Gather remote skills (skip if `--local`)

```bash
BIOSKILLS_TMP=$(mktemp -d)
git clone --depth 1 https://github.com/fbraza/bio-skills.git "$BIOSKILLS_TMP/bio-skills" 2>/dev/null
ls "$BIOSKILLS_TMP/bio-skills/skills/"
```

If `git clone` fails, try with `gh`:
```bash
gh repo clone fbraza/bio-skills "$BIOSKILLS_TMP/bio-skills" -- --depth 1
```

For each remote skill, read the SKILL.md frontmatter to get the `description` field.

### Step 4: Display results

Print a table with columns: **Skill**, **Status**, **Description**.

Status values:
- `installed` — exists locally
- `available` — exists in remote only, not installed
- `local only` — exists locally but not in the remote repo (user-created or removed upstream)

```
============================================================
Bio-Skills Inventory
============================================================
  Skill                              Status       Description
  ─────                              ──────       ───────────
  bulk-rnaseq-counts-to-de-deseq2    installed    Bulk RNA-seq DE with DESeq2
  scvi-tools-scrna                   available    scVI deep generative models
  my-custom-skill                    local only   (user-created)
  ...
============================================================
  Installed: X / Y available skills
  Knowhows: installed (N guides) / not installed
============================================================
```

### Step 5: Cleanup

```bash
rm -rf "$BIOSKILLS_TMP"
```

## Important Notes

- **Read-only operation.** This skill never modifies any files.
- **Requires `git`** and internet connection if listing remote skills.
- **Shallow clone** (`--depth 1`) for speed.
- **Clean up** the temp directory after listing, even if errors occur.
