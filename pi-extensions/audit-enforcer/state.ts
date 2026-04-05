import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { fingerprint } from "./parse-audit.ts";
import { SAVE_TYPE } from "./constants.ts";
import type { AuditIssue, AuditState, Verdict } from "./types.ts";

export function defaultState(): AuditState {
	return {
		awaitingAuditResult: false,
		lastVerdict: null,
		lastIssues: [],
		lastAuditTimestamp: null,
	};
}

export function normalizeState(raw: Partial<AuditState> | null | undefined): AuditState {
	const state = defaultState();
	state.awaitingAuditResult = Boolean(raw?.awaitingAuditResult);
	state.lastVerdict = raw?.lastVerdict === "PASS" || raw?.lastVerdict === "REVIEW" || raw?.lastVerdict === "FAIL"
		? raw.lastVerdict
		: null;
	state.lastAuditTimestamp = typeof raw?.lastAuditTimestamp === "string" ? raw.lastAuditTimestamp : null;
	state.lastIssues = Array.isArray(raw?.lastIssues)
		? raw.lastIssues
				.map((issue) => ({
					text: typeof issue?.text === "string" ? issue.text.trim() : "",
					severity:
						issue?.severity === "critical" || issue?.severity === "warning" || issue?.severity === "suggestion"
							? issue.severity
							: "issue",
					fingerprint:
						typeof issue?.fingerprint === "string" && issue.fingerprint
							? issue.fingerprint
							: fingerprint(typeof issue?.text === "string" ? issue.text : ""),
				}))
				.filter((issue) => issue.text.length > 0)
		: [];
	return state;
}

export function persistState(pi: ExtensionAPI, state: AuditState): void {
	pi.appendEntry(SAVE_TYPE, state);
}
