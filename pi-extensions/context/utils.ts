import os from "node:os";
import path from "node:path";
import fs from "node:fs/promises";
import { existsSync } from "node:fs";

export function formatUsd(cost: number): string {
	if (!Number.isFinite(cost) || cost <= 0) return "$0.00";
	if (cost >= 1) return `$${cost.toFixed(2)}`;
	if (cost >= 0.1) return `$${cost.toFixed(3)}`;
	return `$${cost.toFixed(4)}`;
}

export function estimateTokens(text: string): number {
	// Deliberately fuzzy (good enough for "how big-ish is this").
	return Math.max(0, Math.ceil(text.length / 4));
}

export function normalizeReadPath(inputPath: string, cwd: string): string {
	// Similar to pi's resolveToCwd/resolveReadPath, but simplified.
	let p = inputPath;
	if (p.startsWith("@")) p = p.slice(1);
	if (p === "~") p = os.homedir();
	else if (p.startsWith("~/")) p = path.join(os.homedir(), p.slice(2));
	if (!path.isAbsolute(p)) p = path.resolve(cwd, p);
	return path.resolve(p);
}

export function getAgentDir(): string {
	// Mirrors pi's behavior reasonably well.
	const envCandidates = ["PI_CODING_AGENT_DIR", "TAU_CODING_AGENT_DIR"];
	let envDir: string | undefined;
	for (const k of envCandidates) {
		if (process.env[k]) {
			envDir = process.env[k];
			break;
		}
	}
	if (!envDir) {
		for (const [k, v] of Object.entries(process.env)) {
			if (k.endsWith("_CODING_AGENT_DIR") && v) {
				envDir = v;
				break;
			}
		}
	}

	if (envDir) {
		if (envDir === "~") return os.homedir();
		if (envDir.startsWith("~/")) return path.join(os.homedir(), envDir.slice(2));
		return envDir;
	}
	return path.join(os.homedir(), ".pi", "agent");
}

export async function readFileIfExists(filePath: string): Promise<{ path: string; content: string; bytes: number } | null> {
	if (!existsSync(filePath)) return null;
	try {
		const buf = await fs.readFile(filePath);
		return { path: filePath, content: buf.toString("utf8"), bytes: buf.byteLength };
	} catch {
		return null;
	}
}

export async function loadProjectContextFiles(cwd: string): Promise<Array<{ path: string; tokens: number; bytes: number }>> {
	const out: Array<{ path: string; tokens: number; bytes: number }> = [];
	const seen = new Set<string>();

	const loadFromDir = async (dir: string) => {
		for (const name of ["AGENTS.md", "CLAUDE.md"]) {
			const p = path.join(dir, name);
			const f = await readFileIfExists(p);
			if (f && !seen.has(f.path)) {
				seen.add(f.path);
				out.push({ path: f.path, tokens: estimateTokens(f.content), bytes: f.bytes });
				// pi loads at most one of those per dir
				return;
			}
		}
	};

	await loadFromDir(getAgentDir());

	// Ancestors: root → cwd (same order as pi)
	const stack: string[] = [];
	let current = path.resolve(cwd);
	while (true) {
		stack.push(current);
		const parent = path.resolve(current, "..");
		if (parent === current) break;
		current = parent;
	}
	stack.reverse();
	for (const dir of stack) await loadFromDir(dir);

	return out;
}

export function shortenPath(p: string, cwd: string): string {
	const rp = path.resolve(p);
	const rc = path.resolve(cwd);
	if (rp === rc) return ".";
	if (rp.startsWith(rc + path.sep)) return "./" + rp.slice(rc.length + 1);
	return rp;
}

export function renderUsageBar(
	theme: any,
	parts: { system: number; tools: number; convo: number; remaining: number },
	total: number,
	width: number,
): string {
	const w = Math.max(10, width);
	if (total <= 0) return "";

	const toCols = (n: number) => Math.round((n / total) * w);
	let sys = toCols(parts.system);
	let tools = toCols(parts.tools);
	let con = toCols(parts.convo);
	let rem = w - sys - tools - con;
	if (rem < 0) rem = 0;
	// adjust rounding drift
	while (sys + tools + con + rem < w) rem++;
	while (sys + tools + con + rem > w && rem > 0) rem--;

	const block = "█";
	const sysStr = theme.fg("accent", block.repeat(sys));
	const toolsStr = theme.fg("warning", block.repeat(tools));
	const conStr = theme.fg("success", block.repeat(con));
	const remStr = theme.fg("dim", block.repeat(rem));
	return `${sysStr}${toolsStr}${conStr}${remStr}`;
}

export function joinComma(items: string[]): string {
	return items.join(", ");
}

export function joinCommaStyled(items: string[], renderItem: (item: string) => string, sep: string): string {
	return items.map(renderItem).join(sep);
}
