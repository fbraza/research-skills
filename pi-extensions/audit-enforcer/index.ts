/**
 * audit-enforcer
 *
 * Minimal scientific audit helper:
 * - /audit asks the agent to run the scientific-audit skill
 * - parses verdict + issue list from the audit response
 * - prompts the user with a multi-select TUI for issues to solve now
 * - syncs issues to the todo extension storage (.pi/todos or PI_TODO_PATH)
 * - /audit-resolve closes selected audit todos
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { installManagedSkills, listInstalledSkills } from "../manager/index.ts";
import { SAVE_TYPE } from "./constants.ts";
import { defaultState, normalizeState, persistState } from "./state.ts";
import { isAssistantMessage, getMessageText, parseVerdict, parseIssues } from "./parse-audit.ts";
import { upsertAuditTodo, closeAuditTodo, listOpenAuditTodos } from "./todo-store.ts";
import { promptIssueSelection, promptTodoResolution, updateStatus } from "./tui.ts";
import type { AuditState } from "./types.ts";

async function ensureScientificAuditSkill(pi: ExtensionAPI, ctx: any, rerunCommand: string): Promise<boolean> {
	const installed = await listInstalledSkills(ctx.cwd);
	if (installed.includes("scientific-audit")) return true;

	const confirmed = await ctx.ui.confirm(
		"Install required skill?",
		"The scientific-audit skill is not installed in this project. Install it now via the skills manager cache and continue with /audit?",
	);
	if (!confirmed) {
		ctx.ui.notify("/audit cancelled: scientific-audit is not installed", "warning");
		return false;
	}

	ctx.ui.notify("Installing scientific-audit...", "info");
	await installManagedSkills(pi.exec.bind(pi), ctx.cwd, ["scientific-audit"]);
	ctx.ui.notify("Installed scientific-audit. Reloading Pi and retrying /audit...", "success");
	pi.sendUserMessage(rerunCommand, { deliverAs: "followUp" });
	await ctx.reload();
	return false;
}

export default function auditEnforcerExtension(pi: ExtensionAPI) {
	const state = defaultState();

	pi.on("session_start", async (_event, ctx) => {
		for (const entry of [...ctx.sessionManager.getEntries()].reverse()) {
			if (entry.type === "custom" && entry.customType === SAVE_TYPE) {
				Object.assign(state, normalizeState(entry.data as Partial<AuditState>));
				break;
			}
		}
		await updateStatus(ctx, state);
	});

	pi.on("session_shutdown", async (_event, ctx) => {
		ctx.ui.setStatus("audit-enforcer", undefined);
	});

	pi.registerCommand("audit", {
		description: "Run scientific-audit on the current analysis and sync findings to todos",
		handler: async (args, ctx) => {
			const focus = args.trim();
			const rerunCommand = focus ? `/audit ${focus}` : "/audit";
			const ready = await ensureScientificAuditSkill(pi, ctx, rerunCommand);
			if (!ready) return;

			state.awaitingAuditResult = true;
			persistState(pi, state);
			ctx.ui.notify("Scientific audit requested", "info");
			const prompt = [
				"Run /skill:scientific-audit on the current analysis.",
				focus ? `Focus area: ${focus}.` : "Run the full audit.",
				"Use the skill exactly as written.",
				"At the end of your response, include exactly this structure:",
				"**Verdict**: PASS|REVIEW|FAIL",
				"## Issues",
				"- <issue 1>",
				"- <issue 2>",
				"If there are no issues, write: - None",
			].join("\n");

			if (ctx.isIdle()) pi.sendUserMessage(prompt);
			else pi.sendUserMessage(prompt, { deliverAs: "followUp" });
		},
	});

	pi.registerCommand("audit-resolve", {
		description: "Select audit todos to mark as resolved",
		handler: async (_args, ctx) => {
			const openTodos = await listOpenAuditTodos(ctx.cwd);
			if (openTodos.length === 0) {
				ctx.ui.notify("No open audit todos", "info");
				await updateStatus(ctx, state);
				return;
			}

			const resolved = await promptTodoResolution(ctx, openTodos);
			if (resolved === null) {
				ctx.ui.notify("Audit resolution cancelled", "info");
				return;
			}

			for (const todo of resolved) await closeAuditTodo(ctx.cwd, todo);
			ctx.ui.notify(`Marked ${resolved.length} audit todo${resolved.length === 1 ? "" : "s"} as resolved`, "info");
			await updateStatus(ctx, state);
		},
	});

	pi.on("agent_end", async (event, ctx) => {
		if (!state.awaitingAuditResult) {
			await updateStatus(ctx, state);
			return;
		}

		const lastAssistant = [...(event.messages ?? [])].reverse().find(isAssistantMessage);
		if (!lastAssistant) return;
		const text = getMessageText(lastAssistant);
		const verdict = parseVerdict(text);
		const issues = parseIssues(text).filter((issue) => issue.text.toLowerCase() !== "none");

		state.awaitingAuditResult = false;
		state.lastVerdict = verdict;
		state.lastIssues = issues;
		state.lastAuditTimestamp = new Date().toISOString();
		persistState(pi, state);

		if (!verdict) {
			ctx.ui.notify("Audit completed but the verdict could not be parsed", "warning");
			await updateStatus(ctx, state);
			return;
		}

		if (issues.length === 0) {
			ctx.ui.notify(`Scientific audit ${verdict} with no actionable issues`, verdict === "PASS" ? "info" : "warning");
			await updateStatus(ctx, state);
			return;
		}

		const selectedNow = await promptIssueSelection(ctx, issues);
		if (selectedNow === null) {
			ctx.ui.notify("Audit issue selection cancelled; no todo changes applied", "info");
			await updateStatus(ctx, state);
			return;
		}

		for (const issue of issues) {
			await upsertAuditTodo(ctx.cwd, issue, selectedNow.has(issue.fingerprint), verdict);
		}

		const selectedCount = [...selectedNow].length;
		const deferredCount = issues.length - selectedCount;
		ctx.ui.notify(
			`Audit ${verdict}: ${selectedCount} selected now, ${deferredCount} deferred to todos`,
			verdict === "FAIL" ? "error" : verdict === "REVIEW" ? "warning" : "info",
		);
		await updateStatus(ctx, state);
	});
}
