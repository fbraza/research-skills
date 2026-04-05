import os from "node:os";
import { visibleWidth } from "@mariozechner/pi-tui";
import type { RGB, TodKey } from "./types.ts";
import { TOD_BUCKETS } from "./constants.ts";

/**
 * Slice a string by visible column width (handling CJK/fullwidth characters).
 * @param text   Source string
 * @param start  Start column (in visible-width units)
 * @param width  Maximum width to include
 * @param fromRight  If true, take characters from the right side
 */
export function sliceByColumn(text: string, start: number, width: number, fromRight = false): string {
	let col = 0;
	let resultStart = 0;
	let resultEnd = 0;
	let resultCol = 0;

	for (let i = 0; i < text.length; ) {
		const cp = text.codePointAt(i)!;
		const char = String.fromCodePoint(cp);
		const isWide = cp > 0xffff || (cp >= 0x1100 && cp <= 0x115f) || (cp >= 0x2329 && cp <= 0x232a) || (cp >= 0x2e80 && cp <= 0xa4cf && cp !== 0x303f) || (cp >= 0xac00 && cp <= 0xd7a3) || (cp >= 0xf900 && cp <= 0xfaff) || (cp >= 0xfe10 && cp <= 0xfe19) || (cp >= 0xfe30 && cp <= 0xfe6f) || (cp >= 0xff01 && cp <= 0xff60) || (cp >= 0xffe0 && cp <= 0xffe6) || (cp >= 0x1f300 && cp <= 0x1f9ff);
		const charWidth = isWide ? 2 : 1;

		if (!fromRight) {
			if (col >= start && resultCol < width) {
				if (resultCol === 0) resultStart = i;
				resultEnd = i + char.length;
				resultCol += charWidth;
			}
		}
		col += charWidth;
		i += char.length;
	}

	if (fromRight) {
		let totalWidth = 0;
		for (let i = 0; i < text.length; ) {
			const cp = text.codePointAt(i)!;
			const cw = cp > 0x7f ? 2 : 1;
			totalWidth += cw;
			i += String.fromCodePoint(cp).length;
		}
		let running = 0;
		let started = false;
		for (let i = 0; i < text.length; ) {
			const cp = text.codePointAt(i)!;
			const char = String.fromCodePoint(cp);
			const cw = cp > 0x7f ? 2 : 1;
			if (running + cw > totalWidth - width && !started) {
				resultStart = i;
				started = true;
			}
			running += cw;
			if (started) resultEnd = i + char.length;
			i += char.length;
		}
	}

	return text.slice(resultStart, resultEnd);
}

export function clamp01(x: number): number {
	return Math.max(0, Math.min(1, x));
}

export function lerp(a: number, b: number, t: number): number {
	return a + (b - a) * t;
}

export function mixRgb(a: RGB, b: RGB, t: number): RGB {
	return {
		r: Math.round(lerp(a.r, b.r, t)),
		g: Math.round(lerp(a.g, b.g, t)),
		b: Math.round(lerp(a.b, b.b, t)),
	};
}

export function weightedMix(colors: Array<{ color: RGB; weight: number }>): RGB {
	let total = 0;
	let r = 0;
	let g = 0;
	let b = 0;
	for (const c of colors) {
		if (!Number.isFinite(c.weight) || c.weight <= 0) continue;
		total += c.weight;
		r += c.color.r * c.weight;
		g += c.color.g * c.weight;
		b += c.color.b * c.weight;
	}
	if (total <= 0) return { r: 22, g: 27, b: 34 }; // EMPTY_CELL_BG
	return { r: Math.round(r / total), g: Math.round(g / total), b: Math.round(b / total) };
}

export function ansiBg(rgb: RGB, text: string): string {
	return `\x1b[48;2;${rgb.r};${rgb.g};${rgb.b}m${text}\x1b[0m`;
}

export function ansiFg(rgb: RGB, text: string): string {
	return `\x1b[38;2;${rgb.r};${rgb.g};${rgb.b}m${text}\x1b[0m`;
}

export function dim(text: string): string {
	return `\x1b[2m${text}\x1b[0m`;
}

export function bold(text: string): string {
	return `\x1b[1m${text}\x1b[0m`;
}

export function formatCount(n: number): string {
	if (!Number.isFinite(n) || n === 0) return "0";
	if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(1)}B`;
	if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
	if (n >= 10_000) return `${(n / 1_000).toFixed(1)}K`;
	return n.toLocaleString("en-US");
}

export function formatUsd(cost: number): string {
	if (!Number.isFinite(cost)) return "$0.00";
	if (cost >= 1) return `$${cost.toFixed(2)}`;
	if (cost >= 0.1) return `$${cost.toFixed(3)}`;
	return `$${cost.toFixed(4)}`;
}

/**
 * Abbreviate a path for display. Strategy:
 * - Replace home dir with ~
 * - If still too long, keep first segment + last N segments with … in between
 * Examples:
 *   /Users/mitsuhiko/Development/agent-stuff  →  ~/Development/agent-stuff
 *   /Users/mitsuhiko/Development/minijinja/minijinja-go  →  ~/…/minijinja/minijinja-go
 */
export function abbreviatePath(p: string, maxWidth = 40): string {
	const home = os.homedir();
	let display = p;
	if (display.startsWith(home)) {
		display = "~" + display.slice(home.length);
	}
	if (display.length <= maxWidth) return display;

	const parts = display.split("/").filter(Boolean);
	// Always keep the first part (~ or root indicator) and try to keep as many trailing parts as possible
	if (parts.length <= 2) return display;

	const prefix = parts[0]; // typically "~"
	// Try keeping last N parts, increasing until it fits
	for (let keep = parts.length - 1; keep >= 1; keep--) {
		const tail = parts.slice(parts.length - keep);
		const candidate = prefix + "/…/" + tail.join("/");
		if (candidate.length <= maxWidth || keep === 1) return candidate;
	}
	return display;
}

export function padRight(s: string, n: number): string {
	const delta = n - s.length;
	return delta > 0 ? s + " ".repeat(delta) : s;
}

export function padLeft(s: string, n: number): string {
	const delta = n - s.length;
	return delta > 0 ? " ".repeat(delta) + s : s;
}

export function toLocalDayKey(d: Date): string {
	const yyyy = d.getFullYear();
	const mm = String(d.getMonth() + 1).padStart(2, "0");
	const dd = String(d.getDate()).padStart(2, "0");
	return `${yyyy}-${mm}-${dd}`;
}

export function localMidnight(d: Date): Date {
	return new Date(d.getFullYear(), d.getMonth(), d.getDate(), 0, 0, 0, 0);
}

export function addDaysLocal(d: Date, days: number): Date {
	const x = new Date(d);
	x.setDate(x.getDate() + days);
	return x;
}

export function countDaysInclusiveLocal(start: Date, end: Date): number {
	// Avoid ms-based day math because DST transitions can make a "day" 23/25h in local time.
	let n = 0;
	for (let d = new Date(start); d <= end; d = addDaysLocal(d, 1)) n++;
	return n;
}

export function mondayIndex(date: Date): number {
	// Mon=0 .. Sun=6
	return (date.getDay() + 6) % 7;
}

export function todBucketForHour(hour: number): TodKey {
	for (const b of TOD_BUCKETS) {
		if (hour >= b.from && hour <= b.to) return b.key;
	}
	return "after-midnight";
}

export function todBucketLabel(key: TodKey): string {
	return TOD_BUCKETS.find((b) => b.key === key)?.label ?? key;
}

export function sortMapByValueDesc<K extends string>(m: Map<K, number>): Array<{ key: K; value: number }> {
	return [...m.entries()]
		.map(([key, value]) => ({ key, value }))
		.sort((a, b) => b.value - a.value);
}

export function displayModelName(modelKey: string): string {
	const idx = modelKey.indexOf("/");
	return idx === -1 ? modelKey : modelKey.slice(idx + 1);
}

export function fitRight(text: string, width: number): string {
	if (width <= 0) return "";
	let w = visibleWidth(text);
	let t = text;
	if (w > width) {
		t = sliceByColumn(t, w - width, width, true);
		w = visibleWidth(t);
	}
	return " ".repeat(Math.max(0, width - w)) + t;
}

export function renderLeftRight(left: string, right: string, width: number): string {
	const leftW = visibleWidth(left);
	if (width <= 0) return "";
	if (leftW >= width) return left.slice(0, width);
	const remaining = width - leftW;
	let rightText = right;
	const rightW = visibleWidth(rightText);
	if (rightW > remaining) {
		rightText = sliceByColumn(rightText, rightW - remaining, remaining, true);
	}
	const pad = Math.max(0, remaining - visibleWidth(rightText));
	return left + " ".repeat(pad) + rightText;
}

export function modelKeyFromParts(provider?: unknown, model?: unknown): string | null {
	const p = typeof provider === "string" ? provider.trim() : "";
	const m = typeof model === "string" ? model.trim() : "";
	if (!p && !m) return null;
	if (!p) return m;
	if (!m) return p;
	return `${p}/${m}`;
}
