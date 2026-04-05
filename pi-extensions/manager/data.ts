import fs from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { CACHE_DIR, LOCAL_SKILLS_DIR, REMOTE_REPO, REMOTE_SKILLS_PATH } from "./constants.ts";
import type { ExecFn } from "./constants.ts";
import { normalizeError } from "./rendering.ts";

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

export async function ensureCache(exec: ExecFn): Promise<void> {
	const gitDir = path.join(CACHE_DIR, ".git");
	if (existsSync(gitDir)) {
		const fetchResult = await exec("git", ["-C", CACHE_DIR, "fetch", "origin", "main", "--depth", "1"], { timeout: 60_000 });
		if (fetchResult.code !== 0) {
			throw new Error(fetchResult.stderr.trim() || fetchResult.stdout.trim() || "Failed to refresh skill cache.");
		}
		const resetResult = await exec("git", ["-C", CACHE_DIR, "reset", "--hard", "origin/main"], { timeout: 60_000 });
		if (resetResult.code !== 0) {
			throw new Error(resetResult.stderr.trim() || resetResult.stdout.trim() || "Failed to reset skill cache.");
		}
		return;
	}

	const cloneResult = await exec(
		"git",
		["clone", "--depth", "1", `https://github.com/${REMOTE_REPO}.git`, CACHE_DIR],
		{ timeout: 120_000 },
	);
	if (cloneResult.code !== 0) {
		throw new Error(cloneResult.stderr.trim() || cloneResult.stdout.trim() || "Failed to clone skill repository.");
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
