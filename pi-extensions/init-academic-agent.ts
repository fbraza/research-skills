/**
 * /init-academic-agent [owner/repo] [remote-path] [destination]
 *
 * Download or update an AGENTS.md file from GitHub into the current project.
 *
 * Defaults:
 * - owner/repo: inferred from git remote.origin.url in the current project
 * - remote-path: agent-context/AGENTS.md
 * - destination: <project-root>/AGENTS.md
 *
 * Examples:
 * - /init-academic-agent
 * - /init-academic-agent fbraza/research-skills
 * - /init-academic-agent fbraza/research-skills agent-context/AGENTS.md
 * - /init-academic-agent fbraza/research-skills agent-context/AGENTS.md docs/ACADEMIC-AGENTS.md
 * - /init-academic-agent --force
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import fs from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";

const DEFAULT_REMOTE_PATH = "agent-context/AGENTS.md";
const DEFAULT_DESTINATION = "AGENTS.md";
const GITHUB_HOST = "github.com";

type ExecResult = {
	stdout: string;
	stderr: string;
	code: number;
};

type CommandOptions = {
	repo?: string;
	remotePath: string;
	destination?: string;
	force: boolean;
};

function tokenizeArgs(input: string): string[] {
	const tokens: string[] = [];
	let current = "";
	let quote: '"' | "'" | null = null;
	let escaping = false;

	for (const char of input.trim()) {
		if (escaping) {
			current += char;
			escaping = false;
			continue;
		}

		if (char === "\\") {
			escaping = true;
			continue;
		}

		if (quote) {
			if (char === quote) {
				quote = null;
			} else {
				current += char;
			}
			continue;
		}

		if (char === '"' || char === "'") {
			quote = char;
			continue;
		}

		if (/\s/.test(char)) {
			if (current) {
				tokens.push(current);
				current = "";
			}
			continue;
		}

		current += char;
	}

	if (escaping) current += "\\";
	if (quote) current = `${current}${quote}`;
	if (current) tokens.push(current);
	return tokens;
}

function parseArgs(rawArgs: string): CommandOptions {
	const tokens = tokenizeArgs(rawArgs);
	const positional: string[] = [];
	let force = false;

	for (const token of tokens) {
		if (token === "--force" || token === "-f") {
			force = true;
			continue;
		}
		positional.push(token);
	}

	return {
		repo: positional[0],
		remotePath: positional[1] ?? DEFAULT_REMOTE_PATH,
		destination: positional[2],
		force,
	};
}

function normalizeRepoSlug(input: string): string | null {
	const value = input.trim();
	if (!value) return null;

	const directMatch = value.match(/^([\w.-]+)\/([\w.-]+)$/);
	if (directMatch) return `${directMatch[1]}/${directMatch[2]}`;

	const httpsMatch = value.match(/^https?:\/\/github\.com\/([\w.-]+)\/([\w.-]+?)(?:\.git)?\/?$/i);
	if (httpsMatch) return `${httpsMatch[1]}/${httpsMatch[2]}`;

	const sshMatch = value.match(/^git@github\.com:([\w.-]+)\/([\w.-]+?)(?:\.git)?$/i);
	if (sshMatch) return `${sshMatch[1]}/${sshMatch[2]}`;

	const sshUrlMatch = value.match(/^ssh:\/\/git@github\.com\/([\w.-]+)\/([\w.-]+?)(?:\.git)?\/?$/i);
	if (sshUrlMatch) return `${sshUrlMatch[1]}/${sshUrlMatch[2]}`;

	return null;
}

async function detectProjectRoot(
	cwd: string,
	exec: (command: string, args: string[], options?: { timeout?: number }) => Promise<ExecResult>,
): Promise<string> {
	try {
		const result = await exec("git", ["-C", cwd, "rev-parse", "--show-toplevel"], { timeout: 10_000 });
		if (result.code === 0) {
			const root = result.stdout.trim();
			if (root) return root;
		}
	} catch {
		// Fall back to cwd.
	}
	return cwd;
}

async function inferRepoFromGitRemote(
	cwd: string,
	exec: (command: string, args: string[], options?: { timeout?: number }) => Promise<ExecResult>,
): Promise<string | null> {
	try {
		const result = await exec("git", ["-C", cwd, "config", "--get", "remote.origin.url"], { timeout: 10_000 });
		if (result.code !== 0) return null;
		return normalizeRepoSlug(result.stdout.trim());
	} catch {
		return null;
	}
}

function getGitHubToken(): string | undefined {
	return process.env.GITHUB_TOKEN || process.env.GH_TOKEN || process.env.GITHUB_PAT || undefined;
}

async function fetchViaGitHubApi(repo: string, remotePath: string): Promise<string | null> {
	const url = `https://api.${GITHUB_HOST}/repos/${repo}/contents/${encodeURIComponent(remotePath).replace(/%2F/g, "/")}`;
	const headers: Record<string, string> = {
		Accept: "application/vnd.github+json",
		"User-Agent": "init-academic-agent-extension",
	};

	const token = getGitHubToken();
	if (token) headers.Authorization = `Bearer ${token}`;

	const response = await fetch(url, { headers });
	if (response.status === 404) return null;
	if (!response.ok) {
		const body = await response.text();
		throw new Error(`GitHub API request failed (${response.status}): ${body || response.statusText}`);
	}

	const payload = (await response.json()) as { type?: string; content?: string; encoding?: string; message?: string };
	if (payload.type !== "file" || !payload.content) {
		throw new Error(`GitHub API did not return a file for ${repo}/${remotePath}`);
	}

	if (payload.encoding !== "base64") {
		throw new Error(`Unsupported GitHub content encoding: ${payload.encoding ?? "unknown"}`);
	}

	return Buffer.from(payload.content.replace(/\n/g, ""), "base64").toString("utf8");
}

async function fetchViaGhCli(
	exec: (command: string, args: string[], options?: { timeout?: number }) => Promise<ExecResult>,
	repo: string,
	remotePath: string,
): Promise<string | null> {
	try {
		const result = await exec("gh", ["api", `repos/${repo}/contents/${remotePath}`], { timeout: 30_000 });
		if (result.code !== 0) return null;

		const payload = JSON.parse(result.stdout) as { type?: string; content?: string; encoding?: string };
		if (payload.type !== "file" || !payload.content || payload.encoding !== "base64") return null;
		return Buffer.from(payload.content.replace(/\n/g, ""), "base64").toString("utf8");
	} catch {
		return null;
	}
}

async function downloadAgentsFile(
	repo: string,
	remotePath: string,
	exec: (command: string, args: string[], options?: { timeout?: number }) => Promise<ExecResult>,
): Promise<string> {
	const apiContent = await fetchViaGitHubApi(repo, remotePath);
	if (apiContent !== null) return apiContent;

	const ghContent = await fetchViaGhCli(exec, repo, remotePath);
	if (ghContent !== null) return ghContent;

	throw new Error(
		`Could not download ${remotePath} from ${repo}. Check that the repository/path exists and that GitHub access is configured for private repositories.`,
	);
}

function formatSummary(repo: string, remotePath: string, destination: string, updated: boolean): string {
	return `${updated ? "Updated" : "Created"} ${destination} from ${repo}/${remotePath}`;
}

export default function initAcademicAgentExtension(pi: ExtensionAPI) {
	pi.registerCommand("init-academic-agent", {
		description: "Download agent-context/AGENTS.md from GitHub into the current project",
		handler: async (args, ctx) => {
			const options = parseArgs(args);
			const projectRoot = await detectProjectRoot(ctx.cwd, pi.exec.bind(pi));
			const repo = options.repo ? normalizeRepoSlug(options.repo) : await inferRepoFromGitRemote(projectRoot, pi.exec.bind(pi));

			if (!repo) {
				ctx.ui.notify(
					options.repo
						? `Invalid GitHub repository: ${options.repo}. Use owner/repo, https://github.com/owner/repo, or git@github.com:owner/repo.git`
						: "Could not infer a GitHub repository from git remote.origin.url. Pass one explicitly, e.g. /init-academic-agent owner/repo",
					"error",
				);
				return;
			}

			const destinationPath = path.resolve(projectRoot, options.destination ?? DEFAULT_DESTINATION);
			const destinationDir = path.dirname(destinationPath);
			const remotePath = options.remotePath;

			try {
				ctx.ui.notify(`Downloading ${repo}/${remotePath}…`, "info");
				const content = await downloadAgentsFile(repo, remotePath, pi.exec.bind(pi));
				const hadExistingFile = existsSync(destinationPath);

				if (hadExistingFile) {
					const current = await fs.readFile(destinationPath, "utf8");
					if (current === content) {
						ctx.ui.notify(`AGENTS.md already up to date: ${path.relative(projectRoot, destinationPath) || path.basename(destinationPath)}`, "info");
						return;
					}

					if (!options.force) {
						const relativePath = path.relative(projectRoot, destinationPath) || path.basename(destinationPath);
						const confirmed = await ctx.ui.confirm(
							"Overwrite existing AGENTS.md?",
							`${relativePath} already exists in this project. Replace it with ${repo}/${remotePath}?`,
						);
						if (!confirmed) {
							ctx.ui.notify("init-academic-agent cancelled", "warning");
							return;
						}
					}
				}

				await fs.mkdir(destinationDir, { recursive: true });
				await fs.writeFile(destinationPath, content, "utf8");

				const relativeDestination = path.relative(projectRoot, destinationPath) || path.basename(destinationPath);
				ctx.ui.notify(formatSummary(repo, remotePath, relativeDestination, hadExistingFile), "info");
			} catch (error) {
				const message = error instanceof Error ? error.message : String(error);
				ctx.ui.notify(message, "error");
			}
		},
	});
}
