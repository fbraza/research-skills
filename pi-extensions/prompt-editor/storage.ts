import type { ExtensionAPI, ExtensionContext, ThinkingLevel } from "@mariozechner/pi-coding-agent";
import path from "node:path";
import os from "node:os";
import fs from "node:fs/promises";
import { CUSTOM_MODE_NAME, DEFAULT_MODE_ORDER } from "./constants.ts";
import { runtime } from "./state.ts";
import type { ModeSpec, ModesFile } from "./types.ts";

function expandUserPath(p: string): string {
	if (p === "~") return os.homedir();
	if (p.startsWith("~/")) return path.join(os.homedir(), p.slice(2));
	return p;
}

export function getGlobalAgentDir(): string {
	const env = process.env.PI_CODING_AGENT_DIR;
	if (env) return expandUserPath(env);
	return path.join(os.homedir(), ".pi", "agent");
}

function getGlobalModesPath(): string {
	return path.join(getGlobalAgentDir(), "modes.json");
}

function getProjectModesPath(cwd: string): string {
	return path.join(cwd, ".pi", "modes.json");
}

async function fileExists(p: string): Promise<boolean> {
	try {
		await fs.stat(p);
		return true;
	} catch {
		return false;
	}
}

async function ensureDirForFile(filePath: string): Promise<void> {
	await fs.mkdir(path.dirname(filePath), { recursive: true });
}

async function getMtimeMs(p: string): Promise<number | null> {
	try {
		const st = await fs.stat(p);
		return st.mtimeMs;
	} catch {
		return null;
	}
}

function sleep(ms: number): Promise<void> {
	return new Promise((resolve) => setTimeout(resolve, ms));
}

function getLockPathForFile(filePath: string): string {
	return `${filePath}.lock`;
}

async function withFileLock<T>(filePath: string, fn: () => Promise<T>): Promise<T> {
	const lockPath = getLockPathForFile(filePath);
	await ensureDirForFile(lockPath);

	const start = Date.now();
	while (true) {
		try {
			const handle = await fs.open(lockPath, "wx");
			try {
				await handle.writeFile(JSON.stringify({ pid: process.pid, createdAt: new Date().toISOString() }) + "\n", "utf8");
			} catch {}

			try {
				return await fn();
			} finally {
				await handle.close().catch(() => {});
				await fs.unlink(lockPath).catch(() => {});
			}
		} catch (err: any) {
			if (err?.code !== "EEXIST") throw err;

			try {
				const st = await fs.stat(lockPath);
				if (Date.now() - st.mtimeMs > 30_000) {
					await fs.unlink(lockPath);
					continue;
				}
			} catch {}

			if (Date.now() - start > 5_000) {
				throw new Error(`Timed out waiting for lock: ${lockPath}`);
			}
			await sleep(40 + Math.random() * 80);
		}
	}
}

async function atomicWriteUtf8(filePath: string, content: string): Promise<void> {
	await ensureDirForFile(filePath);
	const dir = path.dirname(filePath);
	const base = path.basename(filePath);
	const tmpPath = path.join(dir, `.${base}.tmp.${process.pid}.${Math.random().toString(16).slice(2)}`);
	await fs.writeFile(tmpPath, content, "utf8");

	try {
		await fs.rename(tmpPath, filePath);
	} catch (err: any) {
		if (err?.code === "EEXIST" || err?.code === "EPERM") {
			await fs.unlink(filePath).catch(() => {});
			await fs.rename(tmpPath, filePath);
		} else {
			await fs.unlink(tmpPath).catch(() => {});
			throw err;
		}
	}
}

function cloneModesFile(file: ModesFile): ModesFile {
	return JSON.parse(JSON.stringify(file)) as ModesFile;
}

type ModeSpecPatch = {
	provider?: string | null;
	modelId?: string | null;
	thinkingLevel?: ThinkingLevel | null;
	color?: string | null;
};

type ModesPatch = {
	currentMode?: string;
	modes?: Record<string, ModeSpecPatch | null>;
};

function computeModesPatch(base: ModesFile, next: ModesFile, includeCurrentMode: boolean): ModesPatch | null {
	const patch: ModesPatch = {};
	if (includeCurrentMode && base.currentMode !== next.currentMode) {
		patch.currentMode = next.currentMode;
	}

	const keys = new Set([...Object.keys(base.modes), ...Object.keys(next.modes)]);
	const modesPatch: Record<string, ModeSpecPatch | null> = {};

	for (const k of keys) {
		const a = base.modes[k];
		const b = next.modes[k];
		if (!b) {
			if (a) modesPatch[k] = null;
			continue;
		}
		if (!a) {
			modesPatch[k] = { ...b };
			continue;
		}

		const diff: ModeSpecPatch = {};
		const fields: (keyof ModeSpec)[] = ["provider", "modelId", "thinkingLevel", "color"];
		for (const f of fields) {
			const av = a[f];
			const bv = b[f];
			if (av !== bv) {
				(diff as any)[f] = bv === undefined ? null : bv;
			}
		}
		if (Object.keys(diff).length > 0) {
			modesPatch[k] = diff;
		}
	}

	if (Object.keys(modesPatch).length > 0) patch.modes = modesPatch;
	if (!patch.modes && patch.currentMode === undefined) return null;
	return patch;
}

function applyModesPatch(target: ModesFile, patch: ModesPatch): void {
	if (patch.currentMode !== undefined) {
		target.currentMode = patch.currentMode;
	}
	if (!patch.modes) return;
	for (const [mode, specPatch] of Object.entries(patch.modes)) {
		if (specPatch === null) {
			delete target.modes[mode];
			continue;
		}
		const targetSpec: Record<string, unknown> = ((target.modes[mode] ??= {}) as any) ?? {};
		for (const [k, v] of Object.entries(specPatch)) {
			if (v === null || v === undefined) delete targetSpec[k];
			else targetSpec[k] = v;
		}
	}
}

function normalizeThinkingLevel(level: unknown): ThinkingLevel | undefined {
	if (typeof level !== "string") return undefined;
	const v = level as ThinkingLevel;
	const allowed: ThinkingLevel[] = ["off", "minimal", "low", "medium", "high", "xhigh"];
	return allowed.includes(v) ? v : undefined;
}

function sanitizeModeSpec(spec: unknown): ModeSpec {
	const obj = (spec && typeof spec === "object" ? spec : {}) as Record<string, unknown>;
	return {
		provider: typeof obj.provider === "string" ? obj.provider : undefined,
		modelId: typeof obj.modelId === "string" ? obj.modelId : undefined,
		thinkingLevel: normalizeThinkingLevel(obj.thinkingLevel),
		color: typeof obj.color === "string" ? obj.color : undefined,
	};
}

function createDefaultModes(ctx: ExtensionContext, pi: ExtensionAPI): ModesFile {
	const currentModel = ctx.model;
	const currentThinking = pi.getThinkingLevel();
	const base: ModeSpec = {
		provider: currentModel?.provider,
		modelId: currentModel?.id,
		thinkingLevel: currentThinking,
	};
	return {
		version: 1,
		currentMode: "default",
		modes: {
			default: { ...base },
			fast: { ...base, thinkingLevel: "off" },
		},
	};
}

function ensureDefaultModeEntries(file: ModesFile, ctx: ExtensionContext, pi: ExtensionAPI): void {
	for (const name of DEFAULT_MODE_ORDER) {
		if (!file.modes[name]) {
			const defaults = createDefaultModes(ctx, pi);
			file.modes[name] = defaults.modes[name];
		}
	}
	if (file.currentMode === CUSTOM_MODE_NAME) file.currentMode = "" as any;
	if (!file.currentMode || !(file.currentMode in file.modes) || file.currentMode === CUSTOM_MODE_NAME) {
		const first = Object.keys(file.modes).find((k) => k !== CUSTOM_MODE_NAME);
		file.currentMode = file.modes.default ? "default" : first || "default";
	}
}

async function loadModesFile(filePath: string, ctx: ExtensionContext, pi: ExtensionAPI): Promise<ModesFile> {
	try {
		const raw = await fs.readFile(filePath, "utf8");
		const parsed = JSON.parse(raw) as Record<string, unknown>;
		const currentMode = typeof parsed.currentMode === "string" ? parsed.currentMode : "default";
		const modesRaw = parsed.modes && typeof parsed.modes === "object" ? (parsed.modes as Record<string, unknown>) : {};
		const modes: Record<string, ModeSpec> = {};
		for (const [k, v] of Object.entries(modesRaw)) {
			modes[k] = sanitizeModeSpec(v);
		}
		const file: ModesFile = { version: 1, currentMode, modes };
		ensureDefaultModeEntries(file, ctx, pi);
		return file;
	} catch {
		return createDefaultModes(ctx, pi);
	}
}

async function saveModesFile(filePath: string, data: ModesFile): Promise<void> {
	await atomicWriteUtf8(filePath, JSON.stringify(data, null, 2) + "\n");
}

async function resolveModesPath(cwd: string): Promise<string> {
	const projectPath = getProjectModesPath(cwd);
	if (await fileExists(projectPath)) return projectPath;
	return getGlobalModesPath();
}

export async function ensureRuntime(pi: ExtensionAPI, ctx: ExtensionContext): Promise<void> {
	const filePath = await resolveModesPath(ctx.cwd);
	const mtimeMs = await getMtimeMs(filePath);
	const filePathChanged = runtime.filePath !== filePath;
	const fileChanged = filePathChanged || runtime.fileMtimeMs !== mtimeMs;

	if (fileChanged) {
		runtime.filePath = filePath;
		runtime.fileMtimeMs = mtimeMs;
		const loaded = await loadModesFile(filePath, ctx, pi);
		ensureDefaultModeEntries(loaded, ctx, pi);
		runtime.data = loaded;
		runtime.baseline = cloneModesFile(runtime.data);
		if (filePathChanged && runtime.currentMode !== CUSTOM_MODE_NAME) {
			runtime.currentMode = runtime.data.currentMode;
			runtime.lastRealMode = runtime.currentMode;
		}
	}

	if (runtime.currentMode !== CUSTOM_MODE_NAME) {
		if (!runtime.currentMode || !(runtime.currentMode in runtime.data.modes)) {
			runtime.currentMode = runtime.data.currentMode;
		}
		if (!runtime.lastRealMode || !(runtime.lastRealMode in runtime.data.modes)) {
			runtime.lastRealMode = runtime.currentMode;
		}
	}
}

export async function persistRuntime(pi: ExtensionAPI, ctx: ExtensionContext): Promise<void> {
	if (!runtime.filePath) return;
	runtime.baseline ??= cloneModesFile(runtime.data);
	const patch = computeModesPatch(runtime.baseline, runtime.data, false);
	if (!patch) return;

	await withFileLock(runtime.filePath, async () => {
		const latest = await loadModesFile(runtime.filePath, ctx, pi);
		applyModesPatch(latest, patch);
		ensureDefaultModeEntries(latest, ctx, pi);
		await saveModesFile(runtime.filePath, latest);
		runtime.data = latest;
		runtime.baseline = cloneModesFile(latest);
		runtime.fileMtimeMs = await getMtimeMs(runtime.filePath);
	});
}
