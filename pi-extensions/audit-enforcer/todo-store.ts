import path from "node:path";
import * as fs from "node:fs/promises";
import { existsSync } from "node:fs";
import crypto from "node:crypto";
import { TODO_DIR_NAME, AUDIT_TAGS } from "./constants.ts";
import type { AuditIssue, TodoFrontMatter, TodoRecord, Verdict } from "./types.ts";

export function getTodosDir(cwd: string): string {
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

export async function readTodoRecords(cwd: string): Promise<TodoRecord[]> {
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

export function findTodoByFingerprint(records: TodoRecord[], fingerprintValue: string): TodoRecord | undefined {
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

export async function upsertAuditTodo(cwd: string, issue: AuditIssue, selectedNow: boolean, verdict: Verdict | null): Promise<TodoRecord> {
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

export async function closeAuditTodo(cwd: string, todo: TodoRecord): Promise<TodoRecord> {
	const updated: TodoRecord = {
		...todo,
		status: "done",
		tags: [...new Set(todo.tags.filter((tag) => tag !== "selected-now" && tag !== "deferred").concat("resolved"))],
	};
	await saveTodo(cwd, updated);
	return updated;
}

export async function listOpenAuditTodos(cwd: string): Promise<TodoRecord[]> {
	const records = await readTodoRecords(cwd);
	return records.filter((record) => {
		const tags = new Set(record.tags);
		return tags.has("audit") && tags.has("scientific-audit") && !["done", "closed"].includes(record.status.toLowerCase());
	});
}
