/**
 * /context
 *
 * Small TUI view showing what's loaded/available:
 * - extensions (best-effort from registered extension slash commands)
 * - skills
 * - project context files (AGENTS.md / CLAUDE.md)
 * - current context window usage + session totals (tokens/cost)
 */

import path from "node:path";
import type { ExtensionAPI, ExtensionCommandContext, ExtensionContext, ToolResultEvent } from "@mariozechner/pi-coding-agent";
import { estimateTokens, formatUsd, joinComma, loadProjectContextFiles, normalizeReadPath, shortenPath } from "./utils.ts";
import { normalizeSkillName, buildSkillIndex, getLoadedSkillsFromSession, sumSessionUsage, SKILL_LOADED_ENTRY } from "./skill-tracker.ts";
import type { SkillIndexEntry, SkillLoadedEntryData, ContextViewData } from "./types.ts";
import { ContextView } from "./context-view.ts";

export default function contextExtension(pi: ExtensionAPI) {
	// Track which skills were actually pulled in via read tool calls.
	let lastSessionId: string | null = null;
	let cachedLoadedSkills = new Set<string>();
	let cachedSkillIndex: SkillIndexEntry[] = [];

	const ensureCaches = (ctx: ExtensionContext) => {
		const sid = ctx.sessionManager.getSessionId();
		if (sid !== lastSessionId) {
			lastSessionId = sid;
			cachedLoadedSkills = getLoadedSkillsFromSession(ctx);
			cachedSkillIndex = buildSkillIndex(pi, ctx.cwd);
		}
		if (cachedSkillIndex.length === 0) {
			cachedSkillIndex = buildSkillIndex(pi, ctx.cwd);
		}
	};

	const matchSkillForPath = (absPath: string): string | null => {
		let best: SkillIndexEntry | null = null;
		for (const s of cachedSkillIndex) {
			if (!s.skillDir) continue;
			if (absPath === s.skillFilePath || absPath.startsWith(s.skillDir + path.sep)) {
				if (!best || s.skillDir.length > best.skillDir.length) best = s;
			}
		}
		return best?.name ?? null;
	};

	pi.on("tool_result", (event: ToolResultEvent, ctx: ExtensionContext) => {
		// Only count successful reads.
		if ((event as any).toolName !== "read") return;
		if ((event as any).isError) return;

		const input = (event as any).input as { path?: unknown } | undefined;
		const p = typeof input?.path === "string" ? input.path : "";
		if (!p) return;

		ensureCaches(ctx);
		const abs = normalizeReadPath(p, ctx.cwd);
		const skillName = matchSkillForPath(abs);
		if (!skillName) return;

		if (!cachedLoadedSkills.has(skillName)) {
			cachedLoadedSkills.add(skillName);
			pi.appendEntry<SkillLoadedEntryData>(SKILL_LOADED_ENTRY, { name: skillName, path: abs });
		}
	});

	pi.registerCommand("context", {
		description: "Show loaded context overview",
		handler: async (_args, ctx: ExtensionCommandContext) => {
			const commands = pi.getCommands();
			const extensionCmds = commands.filter((c) => c.source === "extension");
			const skillCmds = commands.filter((c) => c.source === "skill");

			const extensionsByPath = new Map<string, string[]>();
			for (const c of extensionCmds) {
				const p = c.sourceInfo?.path ?? "<unknown>";
				const arr = extensionsByPath.get(p) ?? [];
				arr.push(c.name);
				extensionsByPath.set(p, arr);
			}
			const extensionFiles = [...extensionsByPath.keys()]
				.map((p) => (p === "<unknown>" ? p : path.basename(p)))
				.sort((a, b) => a.localeCompare(b));

			const skills = skillCmds
				.map((c) => normalizeSkillName(c.name))
				.sort((a, b) => a.localeCompare(b));

			const agentFiles = await loadProjectContextFiles(ctx.cwd);
			const agentFilePaths = agentFiles.map((f) => shortenPath(f.path, ctx.cwd));
			const agentTokens = agentFiles.reduce((a, f) => a + f.tokens, 0);

			const systemPrompt = ctx.getSystemPrompt();
			const systemPromptTokens = systemPrompt ? estimateTokens(systemPrompt) : 0;

			const usage = ctx.getContextUsage();
			const messageTokens = usage?.tokens ?? 0;
			const ctxWindow = usage?.contextWindow ?? 0;

			// Tool definitions are not part of ctx.getContextUsage() (it estimates message tokens).
			// We approximate their token impact from tool name + description, and apply a fudge
			// factor to account for parameters/schema/formatting.
			const TOOL_FUDGE = 1.5;
			const activeToolNames = pi.getActiveTools();
			const toolInfoByName = new Map(pi.getAllTools().map((t) => [t.name, t] as const));
			let toolsTokens = 0;
			for (const name of activeToolNames) {
				const info = toolInfoByName.get(name);
				const blob = `${name}\n${info?.description ?? ""}`;
				toolsTokens += estimateTokens(blob);
			}
			toolsTokens = Math.round(toolsTokens * TOOL_FUDGE);

			const effectiveTokens = messageTokens + toolsTokens;
			const percent = ctxWindow > 0 ? (effectiveTokens / ctxWindow) * 100 : 0;
			const remainingTokens = ctxWindow > 0 ? Math.max(0, ctxWindow - effectiveTokens) : 0;

			const sessionUsage = sumSessionUsage(ctx);

			const makePlainText = () => {
				const lines: string[] = [];
				lines.push("Context");
				if (usage) {
					lines.push(
						`Window: ~${effectiveTokens.toLocaleString()} / ${ctxWindow.toLocaleString()} (${percent.toFixed(1)}% used, ~${remainingTokens.toLocaleString()} left)`,
					);
				} else {
					lines.push("Window: (unknown)");
				}
				lines.push(`System: ~${systemPromptTokens.toLocaleString()} tok (AGENTS ~${agentTokens.toLocaleString()})`);
				lines.push(`Tools: ~${toolsTokens.toLocaleString()} tok (${activeToolNames.length} active)`);
				lines.push(`AGENTS: ${agentFilePaths.length ? joinComma(agentFilePaths) : "(none)"}`);
				lines.push(`Extensions (${extensionFiles.length}): ${extensionFiles.length ? joinComma(extensionFiles) : "(none)"}`);
				lines.push(`Skills (${skills.length}): ${skills.length ? joinComma(skills) : "(none)"}`);
				lines.push(`Session: ${sessionUsage.totalTokens.toLocaleString()} tokens · ${formatUsd(sessionUsage.totalCost)}`);
				return lines.join("\n");
			};

			if (!ctx.hasUI) {
				pi.sendMessage({ customType: "context", content: makePlainText(), display: true }, { triggerTurn: false });
				return;
			}

			const loadedSkills = Array.from(getLoadedSkillsFromSession(ctx)).sort((a, b) => a.localeCompare(b));

			const viewData: ContextViewData = {
				usage: usage
					? {
						messageTokens,
						contextWindow: ctxWindow,
						effectiveTokens,
						percent,
						remainingTokens,
						systemPromptTokens,
						agentTokens,
						toolsTokens,
						activeTools: activeToolNames.length,
					}
					: null,
				agentFiles: agentFilePaths,
				extensions: extensionFiles,
				skills,
				loadedSkills,
				session: { totalTokens: sessionUsage.totalTokens, totalCost: sessionUsage.totalCost },
			};

			await ctx.ui.custom<void>((tui, theme, _kb, done) => {
				return new ContextView(tui, theme, viewData, done);
			});
		},
	});
}
