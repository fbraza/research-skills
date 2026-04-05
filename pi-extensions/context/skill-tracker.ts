import path from "node:path";
import type { ExtensionAPI, ExtensionCommandContext, ExtensionContext } from "@mariozechner/pi-coding-agent";
import { normalizeReadPath } from "./utils.ts";
import type { SkillIndexEntry, SkillLoadedEntryData } from "./types.ts";

export function normalizeSkillName(name: string): string {
	return name.startsWith("skill:") ? name.slice("skill:".length) : name;
}

export function buildSkillIndex(pi: ExtensionAPI, cwd: string): SkillIndexEntry[] {
	return pi
		.getCommands()
		.filter((c) => c.source === "skill")
		.map((c) => {
			const p = c.sourceInfo?.path ? normalizeReadPath(c.sourceInfo.path, cwd) : "";
			return {
				name: normalizeSkillName(c.name),
				skillFilePath: p,
				skillDir: p ? path.dirname(p) : "",
			};
		})
		.filter((x) => x.name && x.skillDir);
}

export const SKILL_LOADED_ENTRY = "context:skill_loaded";

export function getLoadedSkillsFromSession(ctx: ExtensionContext): Set<string> {
	const out = new Set<string>();
	for (const e of ctx.sessionManager.getEntries()) {
		if ((e as any)?.type !== "custom") continue;
		if ((e as any)?.customType !== SKILL_LOADED_ENTRY) continue;
		const data = (e as any)?.data as SkillLoadedEntryData | undefined;
		if (data?.name) out.add(data.name);
	}
	return out;
}

export function extractCostTotal(usage: any): number {
	if (!usage) return 0;
	const c = usage?.cost;
	if (typeof c === "number") return Number.isFinite(c) ? c : 0;
	if (typeof c === "string") {
		const n = Number(c);
		return Number.isFinite(n) ? n : 0;
	}
	const t = c?.total;
	if (typeof t === "number") return Number.isFinite(t) ? t : 0;
	if (typeof t === "string") {
		const n = Number(t);
		return Number.isFinite(n) ? n : 0;
	}
	return 0;
}

export function sumSessionUsage(ctx: ExtensionCommandContext): {
	input: number;
	output: number;
	cacheRead: number;
	cacheWrite: number;
	totalTokens: number;
	totalCost: number;
} {
	let input = 0;
	let output = 0;
	let cacheRead = 0;
	let cacheWrite = 0;
	let totalCost = 0;

	for (const entry of ctx.sessionManager.getEntries()) {
		if ((entry as any)?.type !== "message") continue;
		const msg = (entry as any)?.message;
		if (!msg || msg.role !== "assistant") continue;
		const usage = msg.usage;
		if (!usage) continue;
		input += Number(usage.inputTokens ?? 0) || 0;
		output += Number(usage.outputTokens ?? 0) || 0;
		cacheRead += Number(usage.cacheRead ?? 0) || 0;
		cacheWrite += Number(usage.cacheWrite ?? 0) || 0;
		totalCost += extractCostTotal(usage);
	}

	return {
		input,
		output,
		cacheRead,
		cacheWrite,
		totalTokens: input + output + cacheRead + cacheWrite,
		totalCost,
	};
}
