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

import type { ExtensionAPI, ExtensionContext } from "@mariozechner/pi-coding-agent";
import { CURSOR_MARKER, matchesKey, type Focusable, visibleWidth } from "@mariozechner/pi-tui";
import path from "node:path";
import * as fs from "node:fs/promises";
import { existsSync } from "node:fs";
import crypto from "node:crypto";

type Verdict = "PASS" | "REVIEW" | "FAIL";

type AuditIssue = {
	text: string;
	fingerprint: string;
	severity: "critical" | "warning" | "suggestion" | "issue";
};

type TodoFrontMatter = {
	id: string;
	title: string;
	tags: string[];
	status: string;
	created_at: string;
	assigned_to_session?: string;
};

type TodoRecord = TodoFrontMatter & {
	body: string;
};

type AuditState = {
	awaitingAuditResult: boolean;
	lastVerdict: Verdict | null;
	lastIssues: AuditIssue[];
	lastAuditTimestamp: string | null;
};

const SAVE_TYPE = "audit-enforcer-state";
const TODO_DIR_NAME = ".pi/todos";
const VERDICT_PATTERN = /\*\*Verdict\*\*:\s*(PASS|REVIEW|FAIL)\b/i;
const ISSUE_HEADING_PATTERN = /^#{1,6}\s+Issues\s*$/im;
const SECTION_HEADING_PATTERN = /^#{1,6}\s+(.+?)\s*$/;
const STRUCTURED_ISSUE_SECTION_TITLES = [
	"critical issues (must fix before proceeding)",
	"warnings (should address before publication)",
	"suggestions (consider addressing)",
	"issues",
];
const ISSUE_LINE_PATTERN = /^\s*(?:[-*+]\s+|\d+[.)]\s+)(.+?)\s*$/;
const AUDIT_TAGS = ["audit", "scientific-audit"];

function defaultState(): AuditState {
	return {
		awaitingAuditResult: false,
		lastVerdict: null,
		lastIssues: [],
		lastAuditTimestamp: null,
	};
}

function normalizeState(raw: Partial<AuditState> | null | undefined): AuditState {
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

function persistState(pi: ExtensionAPI, state: AuditState): void {
	pi.appendEntry(SAVE_TYPE, state);
}

function isAssistantMessage(message: any): boolean {
	return Boolean(message && message.role === "assistant");
}

function getMessageText(message: any): string {
	const content = message?.content;
	if (typeof content === "string") return content;
	if (!Array.isArray(content)) return "";
	return content
		.filter((block) => block && typeof block === "object" && block.type === "text" && typeof block.text === "string")
		.map((block) => block.text)
		.join("\n");
}

function parseVerdict(text: string): Verdict | null {
	const match = text.match(VERDICT_PATTERN);
	if (!match) return null;
	const verdict = match[1]?.toUpperCase();
	return verdict === "PASS" || verdict === "REVIEW" || verdict === "FAIL" ? verdict : null;
}

function cleanupIssueText(text: string): string {
	return text
		.replace(/^\[[^\]]+\]\s*/g, "")
		.replace(/\s+/g, " ")
		.trim();
}

function fingerprint(text: string): string {
	return crypto.createHash("sha1").update(text.trim().toLowerCase()).digest("hex").slice(0, 12);
}

function parseIssues(text: string): AuditIssue[] {
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

function getTodosDir(cwd: string): string {
	const envPath = process.env.PI_TODO_PATH?.trim();
	return envPath ? path.resolve(envPath) : path.join(cwd, TODO_DIR_NAME);
}

function getTodoPath(todoDir: string, id: string): string {
	return path.join(todoDir, `${id}.md`);
}

async function ensureTodosDir(todoDir: string): Promise<void> {
	await fs.mkdir(todoDir, { recursive: true });
}

function formatTodo(record: TodoRecord): string {
	const frontMatter: TodoFrontMatter = {
		id: record.id,
		title: record.title,
		tags: record.tags,
		status: record.status,
		created_at: record.created_at,
	};
	if (record.assigned_to_session) frontMatter.assigned_to_session = record.assigned_to_session;
	return `${JSON.stringify(frontMatter, null, 2)}\n\n${record.body.trim()}\n`;
}

function parseTodoFile(text: string): TodoRecord | null {
	const trimmed = text.trim();
	if (!trimmed.startsWith("{")) return null;
	const separator = text.indexOf("\n\n");
	const jsonPart = separator === -1 ? text.trim() : text.slice(0, separator).trim();
	const body = separator === -1 ? "" : text.slice(separator + 2).trim();
	try {
		const meta = JSON.parse(jsonPart) as TodoFrontMatter;
		if (!meta?.id || !meta?.title) return null;
		return {
			...meta,
			tags: Array.isArray(meta.tags) ? meta.tags : [],
			status: typeof meta.status === "string" ? meta.status : "open",
			created_at: typeof meta.created_at === "string" ? meta.created_at : new Date().toISOString(),
			body,
		};
	} catch {
		return null;
	}
}

async function readTodoRecords(cwd: string): Promise<TodoRecord[]> {
	const todoDir = getTodosDir(cwd);
	if (!existsSync(todoDir)) return [];
	const names = await fs.readdir(todoDir);
	const records: TodoRecord[] = [];
	for (const name of names) {
		if (!name.endsWith(".md") || name === "settings.md") continue;
		const filePath = path.join(todoDir, name);
		try {
			const text = await fs.readFile(filePath, "utf8");
			const parsed = parseTodoFile(text);
			if (parsed) records.push(parsed);
		} catch {
			// ignore malformed files
		}
	}
	return records;
}

function findTodoByFingerprint(records: TodoRecord[], fingerprintValue: string): TodoRecord | undefined {
	return records.find((record) => record.body.includes(`audit-fingerprint: ${fingerprintValue}`));
}

async function saveTodo(cwd: string, record: TodoRecord): Promise<void> {
	const todoDir = getTodosDir(cwd);
	await ensureTodosDir(todoDir);
	await fs.writeFile(getTodoPath(todoDir, record.id), formatTodo(record), "utf8");
}

function makeTodoBody(issue: AuditIssue, verdict: Verdict | null): string {
	return [
		"Audit issue captured by audit-enforcer.",
		"",
		`audit-fingerprint: ${issue.fingerprint}`,
		`audit-verdict: ${verdict ?? "unknown"}`,
		`audit-severity: ${issue.severity}`,
		"",
		"Issue:",
		issue.text,
	].join("\n");
}

function makeTodoTitle(issue: AuditIssue): string {
	const prefix = issue.severity === "critical"
		? "[critical]"
		: issue.severity === "warning"
			? "[warning]"
			: issue.severity === "suggestion"
				? "[suggestion]"
				: "[audit]";
	const compact = issue.text.replace(/\s+/g, " ").trim();
	const maxLength = 88;
	const base = `${prefix} ${compact}`;
	return base.length <= maxLength ? base : `${base.slice(0, maxLength - 1)}…`;
}

async function upsertAuditTodo(cwd: string, issue: AuditIssue, selectedNow: boolean, verdict: Verdict | null): Promise<TodoRecord> {
	const records = await readTodoRecords(cwd);
	const existing = findTodoByFingerprint(records, issue.fingerprint);
	const nextStatus = selectedNow ? "in_progress" : "open";
	const nextTags = [
		...AUDIT_TAGS,
		selectedNow ? "selected-now" : "deferred",
		verdict ? verdict.toLowerCase() : "unknown",
		issue.severity,
	];

	if (existing) {
		const mergedTags = [...new Set([...existing.tags.filter((tag) => tag !== "selected-now" && tag !== "deferred"), ...nextTags])];
		const updated: TodoRecord = {
			...existing,
			title: makeTodoTitle(issue),
			status: ["done", "closed"].includes(existing.status.toLowerCase()) ? existing.status : nextStatus,
			tags: mergedTags,
			body: makeTodoBody(issue, verdict),
		};
		await saveTodo(cwd, updated);
		return updated;
	}

	const created: TodoRecord = {
		id: crypto.randomBytes(4).toString("hex"),
		title: makeTodoTitle(issue),
		tags: [...new Set(nextTags)],
		status: nextStatus,
		created_at: new Date().toISOString(),
		body: makeTodoBody(issue, verdict),
	};
	await saveTodo(cwd, created);
	return created;
}

async function closeAuditTodo(cwd: string, todo: TodoRecord): Promise<TodoRecord> {
	const updated: TodoRecord = {
		...todo,
		status: "done",
		tags: [...new Set(todo.tags.filter((tag) => tag !== "selected-now" && tag !== "deferred").concat("resolved"))],
	};
	await saveTodo(cwd, updated);
	return updated;
}

async function listOpenAuditTodos(cwd: string): Promise<TodoRecord[]> {
	const records = await readTodoRecords(cwd);
	return records.filter((record) => {
		const tags = new Set(record.tags);
		return tags.has("audit") && tags.has("scientific-audit") && !["done", "closed"].includes(record.status.toLowerCase());
	});
}

function buildStatusLine(verdict: Verdict | null, openCount: number, ctx: ExtensionContext): string {
	const theme = ctx.ui.theme;
	const issueText = `${openCount} open audit todo${openCount === 1 ? "" : "s"}`;
	if (!verdict) return theme.fg("muted", `Audit: idle • ${issueText}`);
	if (verdict === "PASS") return theme.fg("success", "Audit: PASS") + theme.fg("muted", ` • ${issueText}`);
	if (verdict === "REVIEW") return theme.fg("warning", "Audit: REVIEW") + theme.fg("muted", ` • ${issueText}`);
	return theme.fg("error", "Audit: FAIL") + theme.fg("muted", ` • ${issueText}`);
}

async function updateStatus(ctx: ExtensionContext, state: AuditState): Promise<void> {
	const openCount = await listOpenAuditTodos(ctx.cwd).then((items) => items.length).catch(() => 0);
	ctx.ui.setStatus("audit-enforcer", buildStatusLine(state.lastVerdict, openCount, ctx));
}

class MultiSelectPrompt implements Focusable {
	readonly width = 88;
	focused = false;
	private selectedIndex = 0;
	private readonly checked: boolean[];

	constructor(
		private title: string,
		private subtitle: string,
		private items: string[],
		private theme: ExtensionContext["ui"]["theme"],
		private done: (value: number[] | null) => void,
		defaultChecked = true,
	) {
		this.checked = items.map(() => defaultChecked);
	}

	handleInput(data: string): void {
		if (matchesKey(data, "escape")) {
			this.done(null);
			return;
		}
		if (matchesKey(data, "up")) {
			this.selectedIndex = Math.max(0, this.selectedIndex - 1);
			return;
		}
		if (matchesKey(data, "down")) {
			this.selectedIndex = Math.min(this.items.length - 1, this.selectedIndex + 1);
			return;
		}
		if (matchesKey(data, "space")) {
			this.checked[this.selectedIndex] = !this.checked[this.selectedIndex];
			return;
		}
		if (data.toLowerCase() === "a") {
			const shouldSelectAll = this.checked.some((value) => !value);
			for (let i = 0; i < this.checked.length; i++) this.checked[i] = shouldSelectAll;
			return;
		}
		if (matchesKey(data, "return")) {
			const selected = this.checked.map((value, index) => (value ? index : -1)).filter((index) => index >= 0);
			this.done(selected);
		}
	}

	render(_width: number): string[] {
		const theme = this.theme;
		const innerWidth = this.width - 2;
		const pad = (text: string) => text + " ".repeat(Math.max(0, innerWidth - visibleWidth(text)));
		const row = (text: string) => `${theme.fg("border", "│")}${pad(text)}${theme.fg("border", "│")}`;
		const lines: string[] = [];
		lines.push(theme.fg("border", `╭${"─".repeat(innerWidth)}╮`));
		lines.push(row(` ${theme.fg("accent", theme.bold(this.title))}`));
		lines.push(row(` ${theme.fg("muted", this.subtitle)}`));
		lines.push(row(""));
		for (let i = 0; i < this.items.length; i++) {
			const current = this.items[i];
			const isSelected = i === this.selectedIndex;
			const mark = this.checked[i] ? "[x]" : "[ ]";
			const prefix = isSelected ? theme.fg("accent", "▶") : " ";
			const marker = isSelected && this.focused ? CURSOR_MARKER : "";
			const text = `${prefix} ${mark} ${current}`;
			lines.push(row(` ${marker}${isSelected ? theme.fg("accent", text) : text}`));
		}
		lines.push(row(""));
		lines.push(row(` ${theme.fg("dim", "↑↓ move • space toggle • a toggle all • enter confirm • esc cancel")}`));
		lines.push(theme.fg("border", `╰${"─".repeat(innerWidth)}╯`));
		return lines;
	}

	invalidate(): void {}
	dispose(): void {}
}

async function promptIssueSelection(ctx: ExtensionContext, issues: AuditIssue[]): Promise<Set<string> | null> {
	if (!ctx.hasUI || issues.length === 0) {
		return new Set(issues.map((issue) => issue.fingerprint));
	}

	const selectedIndices = await ctx.ui.custom<number[] | null>((_tui, theme, _kb, done) => {
		return new MultiSelectPrompt(
			"Scientific Audit Findings",
			"Select the issues you want to solve now. Unchecked issues stay as open todos.",
			issues.map((issue) => issue.text),
			theme,
			done,
			true,
		);
	}, { overlay: true });

	if (selectedIndices === null) return null;
	return new Set(selectedIndices.map((index) => issues[index]?.fingerprint).filter(Boolean) as string[]);
}

async function promptTodoResolution(ctx: ExtensionContext, todos: TodoRecord[]): Promise<TodoRecord[] | null> {
	if (todos.length === 0) return [];
	if (!ctx.hasUI) return todos;
	const selectedIndices = await ctx.ui.custom<number[] | null>((_tui, theme, _kb, done) => {
		return new MultiSelectPrompt(
			"Resolve Audit Todos",
			"Select the audit issues that are fixed and should be marked done.",
			todos.map((todo) => todo.title),
			theme,
			done,
			false,
		);
	}, { overlay: true });
	if (selectedIndices === null) return null;
	return selectedIndices.map((index) => todos[index]).filter(Boolean) as TodoRecord[];
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
			state.awaitingAuditResult = true;
			persistState(pi, state);
			ctx.ui.notify("Scientific audit requested", "info");
			const focus = args.trim();
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
