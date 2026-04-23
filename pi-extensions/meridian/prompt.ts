const MERIDIAN_BASE_PROMPT = [
  "You are Claude Code operating through Meridian for pi, a terminal coding assistant. Help the user by analyzing code, proposing changes, and using the available tools when needed.",
  "",
  "Guidelines:",
  "- Be concise in your responses",
  "- Show file paths clearly when working with files",
  "- Prefer using the available tools over guessing",
  "- Follow project-specific instructions when present",
].join("\n");

const PROJECT_CONTEXT_END_REGEX =
  /\n(?:<available_skills>|Current date:|Current working directory:)/;
const CURRENT_DATE_LINE_REGEX = /^Current date:.*$/m;
const CURRENT_WORKING_DIRECTORY_LINE_REGEX =
  /^Current working directory:.*$/m;

export function normalizeCwd(cwd: string): string {
  const normalized = cwd.trim().replace(/\\/g, "/");
  return normalized || ".";
}

export function extractProjectContextSection(systemPrompt: string): string {
  const projectContextHeader = "# Project Context";
  const startIndex = systemPrompt.indexOf(projectContextHeader);
  if (startIndex === -1) return "";

  const remaining = systemPrompt.slice(startIndex);
  const endMatch = PROJECT_CONTEXT_END_REGEX.exec(remaining);
  const endIndex = endMatch ? endMatch.index : remaining.length;

  return remaining.slice(0, endIndex).trim();
}

export function buildMeridianSafeSystemPrompt(
  originalSystemPrompt: string,
  cwd: string
): string {
  const projectContext = extractProjectContextSection(originalSystemPrompt);

  const currentDateLine =
    originalSystemPrompt.match(CURRENT_DATE_LINE_REGEX)?.[0] ||
    `Current date: ${new Date().toISOString().slice(0, 10)}`;

  const currentWorkingDirectoryLine =
    originalSystemPrompt.match(CURRENT_WORKING_DIRECTORY_LINE_REGEX)?.[0] ||
    `Current working directory: ${normalizeCwd(cwd)}`;

  return [
    MERIDIAN_BASE_PROMPT,
    projectContext,
    currentDateLine,
    currentWorkingDirectoryLine,
  ]
    .filter(Boolean)
    .join("\n\n");
}
