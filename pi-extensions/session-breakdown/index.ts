/**
 * /session-breakdown
 *
 * Interactive TUI that analyzes ~/.pi/agent/sessions (recursively, *.jsonl) and shows
 * last 7/30/90 days of:
 * - sessions/day
 * - messages/day
 * - tokens/day (if available)
 * - cost/day (if available)
 * - model breakdown (sessions/messages/tokens + cost)
 *
 * Graph:
 * - GitHub-contributions-style calendar (weeks x weekdays)
 * - Hue: weighted mix of popular model colors (weighted by the selected metric)
 * - Brightness: selected metric per day (log-scaled)
 */

import type { ExtensionAPI, ExtensionContext } from "@mariozechner/pi-coding-agent";
import { BorderedLoader } from "@mariozechner/pi-coding-agent";
import path from "node:path";
import { RANGE_DAYS, SESSION_ROOT } from "./constants.ts";
import { formatCount } from "./utils.ts";
import type { BreakdownData, BreakdownProgressState } from "./types.ts";
import { walkSessionFiles, parseSessionFile } from "./session-parser.ts";
import { localMidnight } from "./utils.ts";
import {
	buildRangeAgg,
	addSessionToRange,
	choosePaletteFromLast30Days,
	chooseCwdPaletteFromLast30Days,
	buildDowPalette,
	buildTodPalette,
} from "./aggregation.ts";
import { rangeSummary } from "./rendering.ts";
import { BreakdownComponent } from "./tui.ts";

function setBorderedLoaderMessage(loader: BorderedLoader, message: string) {
	// BorderedLoader wraps a (Cancellable)Loader which supports setMessage(),
	// but it doesn't expose it publicly. Access the inner loader for progress updates.
	const inner = (loader as any)["loader"]; // eslint-disable-line @typescript-eslint/no-explicit-any
	if (inner && typeof inner.setMessage === "function") {
		inner.setMessage(message);
	}
}

async function computeBreakdown(
	signal?: AbortSignal,
	onProgress?: (update: Partial<BreakdownProgressState>) => void,
): Promise<BreakdownData> {
	const now = new Date();
	const ranges = new Map<number, ReturnType<typeof buildRangeAgg>>();
	for (const d of RANGE_DAYS) ranges.set(d, buildRangeAgg(d, now));
	const range90 = ranges.get(90)!;
	const start90 = range90.days[0].date;

	onProgress?.({ phase: "scan", foundFiles: 0, parsedFiles: 0, totalFiles: 0, currentFile: undefined });

	const candidates = await walkSessionFiles(SESSION_ROOT, start90, signal, (found) => {
		onProgress?.({ phase: "scan", foundFiles: found });
	});

	const totalFiles = candidates.length;
	onProgress?.({
		phase: "parse",
		foundFiles: totalFiles,
		totalFiles,
		parsedFiles: 0,
		currentFile: totalFiles > 0 ? path.basename(candidates[0]!) : undefined,
	});

	let parsedFiles = 0;
	for (const filePath of candidates) {
		if (signal?.aborted) break;
		parsedFiles += 1;
		onProgress?.({ phase: "parse", parsedFiles, totalFiles, currentFile: path.basename(filePath) });

		const session = await parseSessionFile(filePath, signal);
		if (!session) continue;

		const sessionDay = localMidnight(session.startedAt);
		for (const d of RANGE_DAYS) {
			const range = ranges.get(d)!;
			const start = range.days[0].date;
			const end = range.days[range.days.length - 1].date;
			if (sessionDay < start || sessionDay > end) continue;
			addSessionToRange(range, session);
		}
	}

	onProgress?.({ phase: "finalize", currentFile: undefined });

	const palette = choosePaletteFromLast30Days(ranges.get(30)!, 4);
	const cwdPalette = chooseCwdPaletteFromLast30Days(ranges.get(30)!, 4);
	const dowPalette = buildDowPalette();
	const todPalette = buildTodPalette();
	return { generatedAt: now, ranges, palette, cwdPalette, dowPalette, todPalette };
}

export default function sessionBreakdownExtension(pi: ExtensionAPI) {
	pi.registerCommand("session-breakdown", {
		description: "Interactive breakdown of last 7/30/90 days of ~/.pi session usage (sessions/messages/tokens + cost by model)",
		handler: async (_args, ctx: ExtensionContext) => {
			if (!ctx.hasUI) {
				// Non-interactive fallback: just notify.
				const data = await computeBreakdown(undefined);
				const range = data.ranges.get(30)!;
				pi.sendMessage(
					{
						customType: "session-breakdown",
						content: `Session breakdown (non-interactive)\n${rangeSummary(range, 30, "sessions")}`,
						display: true,
					},
					{ triggerTurn: false },
				);
				return;
			}

			let aborted = false;
			const data = await ctx.ui.custom<BreakdownData | null>((tui, theme, _kb, done) => {
				const baseMessage = "Analyzing sessions (last 90 days)…";
				const loader = new BorderedLoader(tui, theme, baseMessage);

				const startedAt = Date.now();
				const progress: BreakdownProgressState = {
					phase: "scan",
					foundFiles: 0,
					parsedFiles: 0,
					totalFiles: 0,
					currentFile: undefined,
				};

				const renderMessage = (): string => {
					const elapsed = ((Date.now() - startedAt) / 1000).toFixed(1);
					if (progress.phase === "scan") {
						return `${baseMessage}  scanning (${formatCount(progress.foundFiles)} files) · ${elapsed}s`;
					}
					if (progress.phase === "parse") {
						return `${baseMessage}  parsing (${formatCount(progress.parsedFiles)}/${formatCount(progress.totalFiles)}) · ${elapsed}s`;
					}
					return `${baseMessage}  finalizing · ${elapsed}s`;
				};

				let intervalId: NodeJS.Timeout | null = null;
				const stopTicker = () => {
					if (intervalId) {
						clearInterval(intervalId);
						intervalId = null;
					}
				};

				// Update every 0.5s so long-running scans show some visible progress.
				setBorderedLoaderMessage(loader, renderMessage());
				intervalId = setInterval(() => {
					setBorderedLoaderMessage(loader, renderMessage());
				}, 500);

				loader.onAbort = () => {
					aborted = true;
					stopTicker();
					done(null);
				};

				computeBreakdown(loader.signal, (update) => Object.assign(progress, update))
					.then((d) => {
						stopTicker();
						if (!aborted) done(d);
					})
					.catch((err) => {
						stopTicker();
						console.error("session-breakdown: failed to analyze sessions", err);
						if (!aborted) done(null);
					});

				return loader;
			});

			if (!data) {
				ctx.ui.notify(aborted ? "Cancelled" : "Failed to analyze sessions", aborted ? "info" : "error");
				return;
			}

			await ctx.ui.custom<void>((tui, _theme, _kb, done) => {
				return new BreakdownComponent(data, tui, done);
			});
		},
	});
}
