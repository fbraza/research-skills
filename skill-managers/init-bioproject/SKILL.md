---
name: init-bioproject
description: "Initialize a bioinformatics project: pull CLAUDE.md from github.com/fbraza/bio-skills into the current project root and create ./data/ and ./results/ directories."
---

# Initialize Bio Project

Set up the current project directory for bioinformatics work by pulling the `CLAUDE.md` configuration from the **fbraza/bio-skills** GitHub repository and creating the standard directory structure.

**Source repository:** `https://github.com/fbraza/bio-skills`
**Install target:** Current project root (`./`)

## How This Works

1. Clone the bio-skills repo to a temporary directory (shallow clone)
2. Create `./data/` and `./results/` directories if they don't exist
3. Copy `CLAUDE.md` to the current project root
4. Handle conflicts if `CLAUDE.md` already exists (merge, replace, or skip)
5. Clean up the temp directory

## Instructions

### Step 1: Clone the repo

```bash
BIOSKILLS_TMP=$(mktemp -d)
gh repo clone fbraza/bio-skills "$BIOSKILLS_TMP/bio-skills" -- --depth 1
```

If `gh` fails, fall back to:
```bash
git clone --depth 1 https://github.com/fbraza/bio-skills.git "$BIOSKILLS_TMP/bio-skills"
```

Verify the clone worked:
```bash
ls "$BIOSKILLS_TMP/bio-skills/CLAUDE.md"
```

### Step 2: Create project directories

```bash
mkdir -p ./data ./results
```

These are standard bioinformatics working directories:
- `./data/` — user-provided input data
- `./results/` — all analysis outputs

### Step 3: Handle CLAUDE.md

Check if `./CLAUDE.md` already exists:

```bash
ls ./CLAUDE.md 2>/dev/null
```

**If CLAUDE.md does NOT exist:**
```bash
cp "$BIOSKILLS_TMP/bio-skills/CLAUDE.md" ./CLAUDE.md
```
Print "Installed CLAUDE.md"

**If CLAUDE.md ALREADY exists:**
Ask the user: "A CLAUDE.md already exists in this project. How should I handle it?"
- **Merge:** Append the bio-skills CLAUDE.md content under a `# Bio-Skills Configuration` header at the end of the existing file
- **Replace:** Overwrite the existing CLAUDE.md with the remote version
- **Skip:** Don't touch the existing CLAUDE.md

Do what the user chooses.

For merge, read the existing CLAUDE.md first, then append:
```
---

# Bio-Skills Configuration

<full content of bio-skills CLAUDE.md>
```

### Step 4: Cleanup and report

```bash
rm -rf "$BIOSKILLS_TMP"
```

Print a summary:
```
============================================================
Bio Project Initialized
============================================================
  CLAUDE.md: installed / merged / replaced / skipped
  ./data/   : created / already exists
  ./results/: created / already exists
============================================================
```

## Important Notes

- **Project-local only.** This skill only modifies files in the current project root. It does NOT touch `~/.claude/skills/`.
- **Skills are NOT installed by this skill.** Use `/install-bioskills` to install skills globally to `~/.claude/skills/`.
- **Requires `git`** and internet connection.
- **Shallow clone** (`--depth 1`) for speed.
- **Clean up** the temp directory after installation, even if errors occur.
- **Do NOT modify any existing project files** other than CLAUDE.md (when user chooses merge/replace).
