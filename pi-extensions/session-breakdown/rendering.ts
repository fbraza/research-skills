import { truncateToWidth, visibleWidth } from "@mariozechner/pi-tui";
import type { BreakdownView, DayAgg, MeasurementMode, RangeAgg, RGB } from "./types.ts";
import { DOW_NAMES, EMPTY_CELL_BG } from "./constants.ts";
import {
	addDaysLocal,
	abbreviatePath,
	ansiFg,
	bold,
	clamp01,
	countDaysInclusiveLocal,
	dim,
	displayModelName,
	fitRight,
	formatCount,
	formatUsd,
	mixRgb,
	mondayIndex,
	padLeft,
	padRight,
	sortMapByValueDesc,
	toLocalDayKey,
	todBucketLabel,
	weightedMix,
} from "./utils.ts";
import { TOD_BUCKETS } from "./constants.ts";

export function dayMixedColor(
	day: DayAgg,
	colorMap: Map<string, RGB>,
	otherColor: RGB,
	mode: MeasurementMode,
	view: BreakdownView = "model",
): RGB {
	const parts: Array<{ color: RGB; weight: number }> = [];
	let otherWeight = 0;

	let map: Map<string, number>;
	if (view === "dow") {
		// For dow, each day IS a single dow – use the dow color directly
		const dowKey = DOW_NAMES[mondayIndex(day.date)];
		const c = colorMap.get(dowKey);
		return c ?? otherColor;
	} else if (view === "tod") {
		if (mode === "tokens") {
			map = day.tokens > 0 ? day.tokensByTod : day.messages > 0 ? day.messagesByTod : day.sessionsByTod;
		} else if (mode === "messages") {
			map = day.messages > 0 ? day.messagesByTod : day.sessionsByTod;
		} else {
			map = day.sessionsByTod;
		}
	} else if (view === "cwd") {
		if (mode === "tokens") {
			map = day.tokens > 0 ? day.tokensByCwd : day.messages > 0 ? day.messagesByCwd : day.sessionsByCwd;
		} else if (mode === "messages") {
			map = day.messages > 0 ? day.messagesByCwd : day.sessionsByCwd;
		} else {
			map = day.sessionsByCwd;
		}
	} else {
		if (mode === "tokens") {
			map = day.tokens > 0 ? day.tokensByModel : day.messages > 0 ? day.messagesByModel : day.sessionsByModel;
		} else if (mode === "messages") {
			map = day.messages > 0 ? day.messagesByModel : day.sessionsByModel;
		} else {
			map = day.sessionsByModel;
		}
	}

	for (const [mk, w] of map.entries()) {
		const c = colorMap.get(mk);
		if (c) parts.push({ color: c, weight: w });
		else otherWeight += w;
	}
	if (otherWeight > 0) parts.push({ color: otherColor, weight: otherWeight });
	return weightedMix(parts);
}

export function graphMetricForRange(
	range: RangeAgg,
	mode: MeasurementMode,
): { kind: "sessions" | "messages" | "tokens"; max: number; denom: number } {
	if (mode === "tokens") {
		const maxTokens = Math.max(0, ...range.days.map((d) => d.tokens));
		if (maxTokens > 0) return { kind: "tokens", max: maxTokens, denom: Math.log1p(maxTokens) };
		// fall back if tokens aren't available
		mode = "messages";
	}

	if (mode === "messages") {
		const maxMessages = Math.max(0, ...range.days.map((d) => d.messages));
		if (maxMessages > 0) return { kind: "messages", max: maxMessages, denom: Math.log1p(maxMessages) };
		// fall back if messages aren't available
		mode = "sessions";
	}

	const maxSessions = Math.max(0, ...range.days.map((d) => d.sessions));
	return { kind: "sessions", max: maxSessions, denom: Math.log1p(maxSessions) };
}

export function weeksForRange(range: RangeAgg): number {
	const days = range.days;
	const start = days[0].date;
	const end = days[days.length - 1].date;
	const gridStart = addDaysLocal(start, -mondayIndex(start));
	const gridEnd = addDaysLocal(end, 6 - mondayIndex(end));
	const totalGridDays = countDaysInclusiveLocal(gridStart, gridEnd);
	return Math.ceil(totalGridDays / 7);
}

export function renderGraphLines(
	range: RangeAgg,
	colorMap: Map<string, RGB>,
	otherColor: RGB,
	mode: MeasurementMode,
	options?: { cellWidth?: number; gap?: number },
	view: BreakdownView = "model",
): string[] {
	const days = range.days;
	const start = days[0].date;
	const end = days[days.length - 1].date;

	const gridStart = addDaysLocal(start, -mondayIndex(start));
	const gridEnd = addDaysLocal(end, 6 - mondayIndex(end));
	const totalGridDays = countDaysInclusiveLocal(gridStart, gridEnd);
	const weeks = Math.ceil(totalGridDays / 7);

	const cellWidth = Math.max(1, Math.floor(options?.cellWidth ?? 1));
	const gap = Math.max(0, Math.floor(options?.gap ?? 1));
	const block = "█".repeat(cellWidth);
	const gapStr = " ".repeat(gap);

	const metric = graphMetricForRange(range, mode);
	const denom = metric.denom;

	// Label only Mon/Wed/Fri like GitHub (saves space)
	const labelByRow = new Map<number, string>([
		[0, "Mon"],
		[2, "Wed"],
		[4, "Fri"],
	]);

	const lines: string[] = [];
	for (let row = 0; row < 7; row++) {
		const label = labelByRow.get(row);
		let line = label ? padRight(label, 3) + " " : "    ";

		for (let w = 0; w < weeks; w++) {
			const cellDate = addDaysLocal(gridStart, w * 7 + row);
			const inRange = cellDate >= start && cellDate <= end;
			const colGap = w < weeks - 1 ? gapStr : "";
			if (!inRange) {
				line += " ".repeat(cellWidth) + colGap;
				continue;
			}

			const key = toLocalDayKey(cellDate);
			const day = range.dayByKey.get(key);
			const value =
				metric.kind === "tokens"
					? (day?.tokens ?? 0)
					: metric.kind === "messages"
						? (day?.messages ?? 0)
						: (day?.sessions ?? 0);

			if (!day || value <= 0) {
				line += ansiFg(EMPTY_CELL_BG, block) + colGap;
				continue;
			}

			const hue = dayMixedColor(day, colorMap, otherColor, mode, view);
			let t = denom > 0 ? Math.log1p(value) / denom : 0;
			t = clamp01(t);
			const minVisible = 0.2;
			const intensity = minVisible + (1 - minVisible) * t;
			const DEFAULT_BG: RGB = { r: 13, g: 17, b: 23 };
			const rgb = mixRgb(DEFAULT_BG, hue, intensity);
			line += ansiFg(rgb, block) + colGap;
		}

		lines.push(line);
	}

	return lines;
}

export function renderLegendItems(modelColors: Map<string, RGB>, orderedModels: string[], otherColor: RGB): string[] {
	const items: string[] = [];
	for (const mk of orderedModels) {
		const c = modelColors.get(mk);
		if (!c) continue;
		items.push(`${ansiFg(c, "█")} ${displayModelName(mk)}`);
	}
	items.push(`${ansiFg(otherColor, "█")} other`);
	return items;
}

export function renderLegendBlock(leftLabel: string, items: string[], width: number): string[] {
	if (width <= 0) return [];
	if (items.length === 0) return [truncateToWidth(leftLabel, width)];

	const lines: string[] = [];
	// First line: label on left, first item right-aligned into remaining space.
	const leftW = visibleWidth(leftLabel);
	if (leftW >= width) {
		lines.push(truncateToWidth(leftLabel, width));
		// Put all items on their own lines right-aligned.
		for (const it of items) lines.push(fitRight(it, width));
		return lines;
	}

	const remaining = Math.max(0, width - leftW);
	lines.push(leftLabel + fitRight(items[0], remaining));

	for (let i = 1; i < items.length; i++) {
		lines.push(fitRight(items[i], width));
	}
	return lines;
}

export function renderModelTable(range: RangeAgg, mode: MeasurementMode, maxRows = 8): string[] {
	// Keep this relatively narrow: model + selected metric + cost + share.
	const metric = graphMetricForRange(range, mode);
	const kind = metric.kind;

	let perModel: Map<string, number>;
	let total = 0;
	let label = kind;

	if (kind === "tokens") {
		perModel = range.modelTokens;
		total = range.totalTokens;
	} else if (kind === "messages") {
		perModel = range.modelMessages;
		total = range.totalMessages;
	} else {
		perModel = range.modelSessions;
		total = range.sessions;
	}

	const sorted = sortMapByValueDesc(perModel);
	const rows = sorted.slice(0, maxRows);

	const valueWidth = kind === "tokens" ? 10 : 8;
	const modelWidth = Math.min(52, Math.max("model".length, ...rows.map((r) => r.key.length)));

	const lines: string[] = [];
	lines.push(`${padRight("model", modelWidth)}  ${padLeft(label, valueWidth)}  ${padLeft("cost", 10)}  ${padLeft("share", 6)}`);
	lines.push(`${"-".repeat(modelWidth)}  ${"-".repeat(valueWidth)}  ${"-".repeat(10)}  ${"-".repeat(6)}`);

	for (const r of rows) {
		const value = perModel.get(r.key) ?? 0;
		const cost = range.modelCost.get(r.key) ?? 0;
		const share = total > 0 ? `${Math.round((value / total) * 100)}%` : "0%";
		lines.push(
			`${padRight(r.key.slice(0, modelWidth), modelWidth)}  ${padLeft(formatCount(value), valueWidth)}  ${padLeft(formatUsd(cost), 10)}  ${padLeft(share, 6)}`,
		);
	}

	if (sorted.length === 0) {
		lines.push(dim("(no model data found)"));
	}

	return lines;
}

export function renderCwdTable(range: RangeAgg, mode: MeasurementMode, maxRows = 8): string[] {
	const metric = graphMetricForRange(range, mode);
	const kind = metric.kind;

	let perCwd: Map<string, number>;
	let total = 0;
	let label = kind;

	if (kind === "tokens") {
		perCwd = range.cwdTokens;
		total = range.totalTokens;
	} else if (kind === "messages") {
		perCwd = range.cwdMessages;
		total = range.totalMessages;
	} else {
		perCwd = range.cwdSessions;
		total = range.sessions;
	}

	const sorted = sortMapByValueDesc(perCwd);
	const rows = sorted.slice(0, maxRows);

	const valueWidth = kind === "tokens" ? 10 : 8;
	const displayPaths = rows.map((r) => abbreviatePath(r.key, 40));
	const cwdWidth = Math.min(42, Math.max("directory".length, ...displayPaths.map((p) => p.length)));

	const lines: string[] = [];
	lines.push(`${padRight("directory", cwdWidth)}  ${padLeft(label, valueWidth)}  ${padLeft("cost", 10)}  ${padLeft("share", 6)}`);
	lines.push(`${"-".repeat(cwdWidth)}  ${"-".repeat(valueWidth)}  ${"-".repeat(10)}  ${"-".repeat(6)}`);

	for (let i = 0; i < rows.length; i++) {
		const r = rows[i];
		const value = perCwd.get(r.key) ?? 0;
		const cost = range.cwdCost.get(r.key) ?? 0;
		const share = total > 0 ? `${Math.round((value / total) * 100)}%` : "0%";
		lines.push(
			`${padRight(displayPaths[i].slice(0, cwdWidth), cwdWidth)}  ${padLeft(formatCount(value), valueWidth)}  ${padLeft(formatUsd(cost), 10)}  ${padLeft(share, 6)}`,
		);
	}

	if (sorted.length === 0) {
		lines.push(dim("(no directory data found)"));
	}

	return lines;
}

export function dowMetricForRange(
	range: RangeAgg,
	mode: MeasurementMode,
): { kind: "sessions" | "messages" | "tokens"; perDow: Map<string, number>; total: number } {
	const metric = graphMetricForRange(range, mode);
	const kind = metric.kind;

	if (kind === "tokens") {
		return { kind, perDow: range.dowTokens, total: range.totalTokens };
	}
	if (kind === "messages") {
		return { kind, perDow: range.dowMessages, total: range.totalMessages };
	}
	return { kind, perDow: range.dowSessions, total: range.sessions };
}

export function renderDowDistributionLines(
	range: RangeAgg,
	mode: MeasurementMode,
	dowColors: Map<string, RGB>,
	width: number,
): string[] {
	const { kind, perDow, total } = dowMetricForRange(range, mode);
	const dayWidth = 3;
	const pctWidth = 4; // "100%"
	const valueWidth = kind === "tokens" ? 10 : 8;
	const showValue = width >= dayWidth + 1 + 10 + 1 + pctWidth + 1 + valueWidth;
	const fixedWidth = dayWidth + 1 + 1 + pctWidth + (showValue ? 1 + valueWidth : 0);
	const barWidth = Math.max(1, width - fixedWidth);
	const fallbackColor: RGB = { r: 160, g: 160, b: 160 };

	const lines: string[] = [];
	for (const dow of DOW_NAMES) {
		const value = perDow.get(dow) ?? 0;
		const share = total > 0 ? value / total : 0;
		let filled = share > 0 ? Math.round(share * barWidth) : 0;
		if (share > 0) filled = Math.max(1, filled);
		filled = Math.min(barWidth, filled);
		const empty = Math.max(0, barWidth - filled);

		const color = dowColors.get(dow) ?? fallbackColor;
		const filledBar = filled > 0 ? ansiFg(color, "█".repeat(filled)) : "";
		const emptyBar = empty > 0 ? ansiFg(EMPTY_CELL_BG, "█".repeat(empty)) : "";
		const pct = padLeft(`${Math.round(share * 100)}%`, pctWidth);

		let line = `${padRight(dow, dayWidth)} ${filledBar}${emptyBar} ${pct}`;
		if (showValue) line += ` ${padLeft(formatCount(value), valueWidth)}`;
		lines.push(line);
	}

	return lines;
}

export function renderDowTable(range: RangeAgg, mode: MeasurementMode): string[] {
	const { kind, perDow, total } = dowMetricForRange(range, mode);
	const valueWidth = kind === "tokens" ? 10 : 8;
	const dowWidth = 5; // "day  "

	const lines: string[] = [];
	lines.push(`${padRight("day", dowWidth)}  ${padLeft(kind, valueWidth)}  ${padLeft("cost", 10)}  ${padLeft("share", 6)}`);
	lines.push(`${"-".repeat(dowWidth)}  ${"-".repeat(valueWidth)}  ${"-".repeat(10)}  ${"-".repeat(6)}`);

	// Always show in Mon–Sun order
	for (const dow of DOW_NAMES) {
		const value = perDow.get(dow) ?? 0;
		const cost = range.dowCost.get(dow) ?? 0;
		const share = total > 0 ? `${Math.round((value / total) * 100)}%` : "0%";
		lines.push(
			`${padRight(dow, dowWidth)}  ${padLeft(formatCount(value), valueWidth)}  ${padLeft(formatUsd(cost), 10)}  ${padLeft(share, 6)}`,
		);
	}

	return lines;
}

export function renderTodTable(range: RangeAgg, mode: MeasurementMode): string[] {
	const metric = graphMetricForRange(range, mode);
	const kind = metric.kind;

	let perTod: Map<string, number>;
	let total = 0;

	if (kind === "tokens") {
		perTod = range.todTokens;
		total = range.totalTokens;
	} else if (kind === "messages") {
		perTod = range.todMessages;
		total = range.totalMessages;
	} else {
		perTod = range.todSessions;
		total = range.sessions;
	}

	const valueWidth = kind === "tokens" ? 10 : 8;
	const todWidth = 22; // widest label

	const lines: string[] = [];
	lines.push(`${padRight("time of day", todWidth)}  ${padLeft(kind, valueWidth)}  ${padLeft("cost", 10)}  ${padLeft("share", 6)}`);
	lines.push(`${"-".repeat(todWidth)}  ${"-".repeat(valueWidth)}  ${"-".repeat(10)}  ${"-".repeat(6)}`);

	// Always show in chronological order
	for (const b of TOD_BUCKETS) {
		const value = perTod.get(b.key) ?? 0;
		const cost = range.todCost.get(b.key) ?? 0;
		const share = total > 0 ? `${Math.round((value / total) * 100)}%` : "0%";
		lines.push(
			`${padRight(b.label, todWidth)}  ${padLeft(formatCount(value), valueWidth)}  ${padLeft(formatUsd(cost), 10)}  ${padLeft(share, 6)}`,
		);
	}

	return lines;
}

export function rangeSummary(range: RangeAgg, days: number, mode: MeasurementMode): string {
	const avg = range.sessions > 0 ? range.totalCost / range.sessions : 0;
	const costPart = range.totalCost > 0 ? `${formatUsd(range.totalCost)} · avg ${formatUsd(avg)}/session` : `$0.0000`;

	if (mode === "tokens") {
		return `Last ${days} days: ${formatCount(range.sessions)} sessions · ${formatCount(range.totalTokens)} tokens · ${costPart}`;
	}
	if (mode === "messages") {
		return `Last ${days} days: ${formatCount(range.sessions)} sessions · ${formatCount(range.totalMessages)} messages · ${costPart}`;
	}
	return `Last ${days} days: ${formatCount(range.sessions)} sessions · ${costPart}`;
}
