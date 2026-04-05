export type Verdict = "PASS" | "REVIEW" | "FAIL";

export type AuditIssue = {
	text: string;
	fingerprint: string;
	severity: "critical" | "warning" | "suggestion" | "issue";
};

export type TodoFrontMatter = {
	id: string;
	title: string;
	tags: string[];
	status: string;
	created_at: string;
	assigned_to_session?: string;
};

export type TodoRecord = TodoFrontMatter & {
	body: string;
};

export type AuditState = {
	awaitingAuditResult: boolean;
	lastVerdict: Verdict | null;
	lastIssues: AuditIssue[];
	lastAuditTimestamp: string | null;
};
