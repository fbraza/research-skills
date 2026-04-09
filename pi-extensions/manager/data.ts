import fs from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { CACHE_DIR, LOCAL_SKILLS_DIR, REMOTE_REPO, REMOTE_SKILLS_PATH } from "./constants.ts";
import type { ExecFn } from "./constants.ts";
import { normalizeError } from "./rendering.ts";

const RECOVERABLE_CACHE_ERROR_PATTERN =
	/not a git repository|this operation must be run in a work tree|bad object|index file corrupt|corrupt|reference broken|could not parse object|unable to read tree/i;

export interface CacheEnsureResult {
	rebuilt: boolean;
	message?: string;
}

export function getLocalSkillsPath(cwd: string): string {
	return path.join(cwd, LOCAL_SKILLS_DIR);
}

export async function pathExists(filePath: string): Promise<boolean> {
	try {
		await fs.access(filePath);
		return true;
	} catch {
		return false;
	}
}

export async function listInstalledSkills(cwd: string): Promise<string[]> {
	const skillsDir = getLocalSkillsPath(cwd);
	if (!(await pathExists(skillsDir))) return [];

	const entries = await fs.readdir(skillsDir, { withFileTypes: true });
	const installed: string[] = [];
	for (const entry of entries) {
		if (!entry.isDirectory()) continue;
		const skillDir = path.join(skillsDir, entry.name);
		const skillFile = path.join(skillDir, "SKILL.md");
		if (await pathExists(skillFile)) installed.push(entry.name);
	}
	return installed.sort((a, b) => a.localeCompare(b));
}

async function ensureGhAuthenticated(exec: ExecFn): Promise<void> {
	try {
		const result = await exec("gh", ["auth", "status"], { timeout: 20_000 });
		if (result.code !== 0) {
			throw new Error("GitHub CLI (`gh`) is required. Run `gh auth login` first.");
		}
	} catch (error) {
		throw new Error(`GitHub CLI (gh) is required and must be authenticated. ${normalizeError(error)}`);
	}
}

export async function listRemoteSkills(exec: ExecFn): Promise<string[]> {
	await ensureGhAuthenticated(exec);
	const result = await exec("gh", ["api", `repos/${REMOTE_REPO}/contents/${REMOTE_SKILLS_PATH}`], { timeout: 30_000 });
	if (result.code !== 0) {
		throw new Error(result.stderr.trim() || result.stdout.trim() || "Failed to fetch remote skill list.");
	}

	let payload: Array<{ name?: string; type?: string }> = [];
	try {
		payload = JSON.parse(result.stdout);
	} catch (error) {
		throw new Error(`Failed to parse GitHub API response: ${normalizeError(error)}`);
	}

	return payload
		.filter((entry) => entry.type === "dir" && typeof entry.name === "string")
		.map((entry) => entry.name as string)
		.sort((a, b) => a.localeCompare(b));
}

function formatGitFailure(output: string, fallback: string): string {
	const detail = output.trim();
	return detail ? `${fallback}: ${detail}` : fallback;
}

function isRecoverableCacheError(error: unknown): boolean {
	return RECOVERABLE_CACHE_ERROR_PATTERN.test(normalizeError(error));
}

async function isValidGitCache(exec: ExecFn, cacheDir: string): Promise<boolean> {
	if (!existsSync(cacheDir)) return false;

	const validateResult = await exec("git", ["-C", cacheDir, "rev-parse", "--is-inside-work-tree"], { timeout: 20_000 });
	if (validateResult.code !== 0) return false;
	return validateResult.stdout.trim() === "true";
}

async function removeCacheDir(cacheDir: string): Promise<void> {
	await fs.rm(cacheDir, { recursive: true, force: true });
}

async function cloneCache(exec: ExecFn, cacheDir: string): Promise<void> {
	const cloneResult = await exec(
		"git",
		["clone", "--depth", "1", `https://github.com/${REMOTE_REPO}.git`, cacheDir],
		{ timeout: 120_000 },
	);
	if (cloneResult.code !== 0) {
		throw new Error(formatGitFailure(cloneResult.stderr || cloneResult.stdout, "Failed to clone skill repository"));
	}
}

async function refreshCache(exec: ExecFn, cacheDir: string): Promise<void> {
	const fetchResult = await exec("git", ["-C", cacheDir, "fetch", "origin", "main", "--depth", "1"], { timeout: 60_000 });
	if (fetchResult.code !== 0) {
		throw new Error(formatGitFailure(fetchResult.stderr || fetchResult.stdout, "Failed to refresh skill cache"));
	}

	const resetResult = await exec("git", ["-C", cacheDir, "reset", "--hard", "origin/main"], { timeout: 60_000 });
	if (resetResult.code !== 0) {
		throw new Error(formatGitFailure(resetResult.stderr || resetResult.stdout, "Failed to reset skill cache"));
	}
}

async function rebuildCache(exec: ExecFn, cacheDir: string, reason: string): Promise<void> {
	await removeCacheDir(cacheDir);
	try {
		await cloneCache(exec, cacheDir);
	} catch (error) {
		throw new Error(`${reason} Tried to rebuild the cache, but cloning failed. ${normalizeError(error)}`);
	}
}

export async function ensureCache(exec: ExecFn, cacheDir = CACHE_DIR): Promise<CacheEnsureResult> {
	if (!(await pathExists(cacheDir))) {
		await cloneCache(exec, cacheDir);
		return { rebuilt: false };
	}

	const validCache = await isValidGitCache(exec, cacheDir);
	if (!validCache) {
		await rebuildCache(exec, cacheDir, `Detected an invalid skill cache at ${cacheDir}.`);
		return {
			rebuilt: true,
			message: "Detected an invalid local skill cache and rebuilt it automatically.",
		};
	}

	try {
		await refreshCache(exec, cacheDir);
		return { rebuilt: false };
	} catch (error) {
		if (!isRecoverableCacheError(error)) throw error;
		await rebuildCache(exec, cacheDir, `Detected a broken skill cache at ${cacheDir}. ${normalizeError(error)}`);
		return {
			rebuilt: true,
			message: "Detected a broken local skill cache and rebuilt it automatically.",
		};
	}
}

export async function ensureLocalSkillsDir(cwd: string): Promise<string> {
	const skillsDir = getLocalSkillsPath(cwd);
	await fs.mkdir(skillsDir, { recursive: true });
	return skillsDir;
}

export async function copySkillFromCache(name: string, cwd: string): Promise<void> {
	const targetDir = await ensureLocalSkillsDir(cwd);
	const sourceDir = path.join(CACHE_DIR, REMOTE_SKILLS_PATH, name);
	const destinationDir = path.join(targetDir, name);
	if (!(await pathExists(sourceDir))) {
		throw new Error(`Skill '${name}' was not found in the cache.`);
	}
	await fs.rm(destinationDir, { recursive: true, force: true });
	await fs.cp(sourceDir, destinationDir, { recursive: true });
}

export async function removeLocalSkill(name: string, cwd: string): Promise<void> {
	const destinationDir = path.join(getLocalSkillsPath(cwd), name);
	await fs.rm(destinationDir, { recursive: true, force: true });
}

export async function installManagedSkills(exec: ExecFn, cwd: string, names: string[]): Promise<void> {
	if (names.length === 0) return;
	await ensureCache(exec);
	for (const name of names) {
		await copySkillFromCache(name, cwd);
	}
}
