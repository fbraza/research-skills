import crypto from "node:crypto";
import {
	VERDICT_PATTERN,
	ISSUE_HEADING_PATTERN,
	SECTION_HEADING_PATTERN,
	STRUCTURED_ISSUE_SECTION_TITLES,
	ISSUE_LINE_PATTERN,
} from "./constants.ts";
import type { AuditIssue, Verdict } from "./types.ts";

export function parseVerdict(text: string): Verdict | null {
	const match = text.match(VERDICT_PATTERN);
	if (!match) return null;
	const verdict = match[1]?.toUpperCase();
	return verdict === "PASS" || verdict === "REVIEW" || verdict === "FAIL" ? verdict : null;
}

export function cleanupIssueText(text: string): string {
	return text
		.replace(/^\[[^\]]+\]\s*/g, "")
		.replace(/\s+/g, " ")
		.trim();
}

export function fingerprint(text: string): string {
	return crypto.createHash("sha1").update(text.trim().toLowerCase()).digest("hex").slice(0, 12);
}

export function parseIssues(text: string): AuditIssue[] {
	const lines = text.split(/\r?\n/);
	const issues: AuditIssue[] = [];
	let inIssuesSection = false;
	let currentSection: string | null = null;

	for (const line of lines) {
		const trimmed = line.trim();
		const headingMatch = trimmed.match(SECTION_HEADING_PATTERN);
		if (headingMatch) {
			currentSection = headingMatch[1]?.trim().toLowerCase() ?? null;
			inIssuesSection = STRUCTURED_ISSUE_SECTION_TITLES.includes(currentSection ?? "");
			if (!inIssuesSection && trimmed.toLowerCase() === "## audit coverage summary") break;
			continue;
		}

		if (ISSUE_HEADING_PATTERN.test(line)) {
			inIssuesSection = true;
			continue;
		}

		if (inIssuesSection && /^#{1,6}\s+/.test(trimmed)) {
			break;
		}

		if (/^\(or\s+"?none/i.test(trimmed) || /^none identified$/i.test(trimmed) || /^none$/i.test(trimmed)) {
			continue;
		}

		const source = inIssuesSection ? line : trimmed;
		const match = source.match(ISSUE_LINE_PATTERN);
		if (!match) continue;
		const cleaned = cleanupIssueText(match[1] ?? "");
		if (!cleaned) continue;
		if (/^(evidence|impact|suggested fix):/i.test(cleaned)) continue;
		const severity: AuditIssue["severity"] = currentSection?.startsWith("critical issues")
			? "critical"
			: currentSection?.startsWith("warnings")
				? "warning"
				: currentSection?.startsWith("suggestions")
					? "suggestion"
					: "issue";
		if (currentSection && currentSection !== "issues") {
			issues.push({
				text: cleaned,
				severity,
				fingerprint: fingerprint(`${currentSection}:${cleaned}`),
			});
			continue;
		}
		issues.push({ text: cleaned, severity, fingerprint: fingerprint(cleaned) });
	}

	const deduped = new Map<string, AuditIssue>();
	for (const issue of issues) {
		if (!deduped.has(issue.fingerprint)) deduped.set(issue.fingerprint, issue);
	}
	return [...deduped.values()];
}

export function isAssistantMessage(message: any): boolean {
	return Boolean(message && message.role === "assistant");
}

export function getMessageText(message: any): string {
	const content = message?.content;
	if (typeof content === "string") return content;
	if (!Array.isArray(content)) return "";
	return content
		.filter((block) => block && typeof block === "object" && block.type === "text" && typeof block.text === "string")
		.map((block) => block.text)
		.join("\n");
}
