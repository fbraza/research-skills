/**
 * /init-academic-agent [--force]
 *
 * Download or update AGENTS.md from fbraza/research-skills into the current project.
 *
 * The file is fetched from:
 *   https://github.com/fbraza/research-skills/blob/main/agent-context/AGENTS.md
 *
 * Flags:
 *   --force / -f   Overwrite without prompting
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import fs from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";

/** Hard-coded remote configuration — the single source of truth. */
const REPO = "fbraza/research-skills";
const REMOTE_PATH = "agent-context/AGENTS.md";
const DESTINATION = "AGENTS.md";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function hasForceFlag(args: string): boolean {
	return args
		.trim()
		.split(/\s+/)
		.some((t) => t === "--force" || t === "-f");
}

function getGitHubToken(): string | undefined {
	return process.env.GITHUB_TOKEN || process.env.GH_TOKEN || process.env.GITHUB_PAT || undefined;
}

async function fetchFileFromGitHub(): Promise<string> {
	const url = `https://api.github.com/repos/${REPO}/contents/${encodeURIComponent(REMOTE_PATH).replace(/%2F/g, "/")}`;
	const headers: Record<string, string> = {
		Accept: "application/vnd.github+json",
		"User-Agent": "init-academic-agent",
	};
	const token = getGitHubToken();
	if (token) headers.Authorization = `Bearer ${token}`;

	const response = await fetch(url, { headers });
	if (!response.ok) {
		throw new Error(`GitHub API request failed (${response.status}): ${response.statusText}`);
	}

	const payload = (await response.json()) as { type?: string; content?: string; encoding?: string };
	if (payload.type !== "file" || !payload.content || payload.encoding !== "base64") {
		throw new Error(`Unexpected GitHub API response for ${REPO}/${REMOTE_PATH}`);
	}

	return Buffer.from(payload.content.replace(/\n/g, ""), "base64").toString("utf8");
}

// ---------------------------------------------------------------------------
// Extension entry-point
// ---------------------------------------------------------------------------

export default function initAcademicAgentExtension(pi: ExtensionAPI) {
	pi.registerCommand("init-academic-agent", {
		description: `Download ${REMOTE_PATH} from ${REPO} into the current project`,
		handler: async (args, ctx) => {
			const force = hasForceFlag(args);
			const projectRoot = ctx.cwd;
			const destinationPath = path.resolve(projectRoot, DESTINATION);

			try {
				ctx.ui.notify(`Downloading ${REPO}/${REMOTE_PATH}…`, "info");
				const content = await fetchFileFromGitHub();

				const hadExistingFile = existsSync(destinationPath);

				if (hadExistingFile) {
					const current = await fs.readFile(destinationPath, "utf8");
					if (current === content) {
						ctx.ui.notify(`${DESTINATION} is already up to date.`, "info");
						return;
					}

					if (!force) {
						const confirmed = await ctx.ui.confirm(
							"Overwrite existing AGENTS.md?",
							`${DESTINATION} already exists. Replace it with the latest from ${REPO}/${REMOTE_PATH}?`,
						);
						if (!confirmed) {
							ctx.ui.notify("Cancelled.", "warning");
							return;
						}
					}
				}

				await fs.mkdir(path.dirname(destinationPath), { recursive: true });
				await fs.writeFile(destinationPath, content, "utf8");

				ctx.ui.notify(
					`${hadExistingFile ? "Updated" : "Created"} ${DESTINATION} from ${REPO}/${REMOTE_PATH}`,
					"info",
				);
			} catch (error) {
				ctx.ui.notify(error instanceof Error ? error.message : String(error), "error");
			}
		},
	});
}
