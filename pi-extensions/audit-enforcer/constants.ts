export const SAVE_TYPE = "audit-enforcer-state";
export const TODO_DIR_NAME = ".pi/todos";
export const VERDICT_PATTERN = /\*\*Verdict\*\*:\s*(PASS|REVIEW|FAIL)\b/i;
export const ISSUE_HEADING_PATTERN = /^#{1,6}\s+Issues\s*$/im;
export const SECTION_HEADING_PATTERN = /^#{1,6}\s+(.+?)\s*$/;
export const STRUCTURED_ISSUE_SECTION_TITLES = [
	"critical issues (must fix before proceeding)",
	"warnings (should address before publication)",
	"suggestions (consider addressing)",
	"issues",
];
export const ISSUE_LINE_PATTERN = /^\s*(?:[-*+]\s+|\d+[.)]\s+)(.+?)\s*$/;
export const AUDIT_TAGS = ["audit", "scientific-audit"];
