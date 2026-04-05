import { Key, matchesKey, type Component, type TUI, truncateToWidth, visibleWidth } from "@mariozechner/pi-tui";
import type { BreakdownData, BreakdownView, MeasurementMode, RGB } from "./types.ts";
import { RANGE_DAYS } from "./constants.ts";
import {
	abbreviatePath,
	ansiFg,
	bold,
	dim,
	displayModelName,
	fitRight,
	todBucketLabel,
} from "./utils.ts";
import {
	graphMetricForRange,
	rangeSummary,
	renderDowDistributionLines,
	renderDowTable,
	renderGraphLines,
	renderModelTable,
	renderCwdTable,
	renderTodTable,
	weeksForRange,
} from "./rendering.ts";

export class BreakdownComponent implements Component {
	private data: BreakdownData;
	private tui: TUI;
	private onDone: () => void;
	private rangeIndex = 1; // default 30d
	private measurement: MeasurementMode = "sessions";
	private view: BreakdownView = "model";
	private cachedWidth?: number;
	private cachedLines?: string[];

	constructor(data: BreakdownData, tui: TUI, onDone: () => void) {
		this.data = data;
		this.tui = tui;
		this.onDone = onDone;
	}

	invalidate(): void {
		this.cachedWidth = undefined;
		this.cachedLines = undefined;
	}

	handleInput(data: string): void {
		if (matchesKey(data, Key.escape) || matchesKey(data, Key.ctrl("c")) || data.toLowerCase() === "q") {
			this.onDone();
			return;
		}

		if (matchesKey(data, Key.tab) || matchesKey(data, Key.shift("tab")) || data.toLowerCase() === "t") {
			const order: MeasurementMode[] = ["sessions", "messages", "tokens"];
			const idx = Math.max(0, order.indexOf(this.measurement));
			const dir = matchesKey(data, Key.shift("tab")) ? -1 : 1;
			this.measurement = order[(idx + order.length + dir) % order.length] ?? "sessions";
			this.invalidate();
			this.tui.requestRender();
			return;
		}

		const prev = () => {
			this.rangeIndex = (this.rangeIndex + RANGE_DAYS.length - 1) % RANGE_DAYS.length;
			this.invalidate();
			this.tui.requestRender();
		};
		const next = () => {
			this.rangeIndex = (this.rangeIndex + 1) % RANGE_DAYS.length;
			this.invalidate();
			this.tui.requestRender();
		};

		if (matchesKey(data, Key.left) || data.toLowerCase() === "h") prev();
		if (matchesKey(data, Key.right) || data.toLowerCase() === "l") next();

		if (matchesKey(data, Key.up) || matchesKey(data, Key.down) || data.toLowerCase() === "j" || data.toLowerCase() === "k") {
			const views: BreakdownView[] = ["model", "cwd", "dow", "tod"];
			const idx = views.indexOf(this.view);
			const dir = matchesKey(data, Key.up) || data.toLowerCase() === "k" ? -1 : 1;
			this.view = views[(idx + views.length + dir) % views.length] ?? "model";
			this.invalidate();
			this.tui.requestRender();
			return;
		}

		if (data === "1") {
			this.rangeIndex = 0;
			this.invalidate();
			this.tui.requestRender();
		}
		if (data === "2") {
			this.rangeIndex = 1;
			this.invalidate();
			this.tui.requestRender();
		}
		if (data === "3") {
			this.rangeIndex = 2;
			this.invalidate();
			this.tui.requestRender();
		}
	}

	render(width: number): string[] {
		if (this.cachedWidth === width && this.cachedLines) return this.cachedLines;

		const selectedDays = RANGE_DAYS[this.rangeIndex];
		const range = this.data.ranges.get(selectedDays)!;
		const metric = graphMetricForRange(range, this.measurement);

		const tab = (days: number, idx: number): string => {
			const selected = idx === this.rangeIndex;
			const label = `${days}d`;
			return selected ? bold(`[${label}]`) : dim(` ${label} `);
		};

		const metricTab = (mode: MeasurementMode, label: string): string => {
			const selected = mode === this.measurement;
			return selected ? bold(`[${label}]`) : dim(` ${label} `);
		};

		const viewTab = (v: BreakdownView, label: string): string => {
			const selected = v === this.view;
			return selected ? bold(`[${label}]`) : dim(` ${label} `);
		};

		const header =
			`${bold("Session breakdown")}  ${tab(7, 0)}${tab(30, 1)}${tab(90, 2)}  ` +
			`${metricTab("sessions", "sess")}${metricTab("messages", "msg")}${metricTab("tokens", "tok")}  ` +
			`${viewTab("model", "model")}${viewTab("cwd", "cwd")}${viewTab("dow", "dow")}${viewTab("tod", "tod")}`;

		// Choose colors and legend based on current view
		let activeColorMap: Map<string, RGB>;
		let activeOtherColor: RGB = { r: 160, g: 160, b: 160 };
		const legendItems: string[] = [];

		if (this.view === "model") {
			activeColorMap = this.data.palette.modelColors;
			activeOtherColor = this.data.palette.otherColor;
			for (const mk of this.data.palette.orderedModels) {
				const c = activeColorMap.get(mk);
				if (c) legendItems.push(`${ansiFg(c, "█")} ${displayModelName(mk)}`);
			}
			legendItems.push(`${ansiFg(activeOtherColor, "█")} other`);
		} else if (this.view === "cwd") {
			activeColorMap = this.data.cwdPalette.cwdColors;
			activeOtherColor = this.data.cwdPalette.otherColor;
			for (const cwd of this.data.cwdPalette.orderedCwds) {
				const c = activeColorMap.get(cwd);
				if (c) legendItems.push(`${ansiFg(c, "█")} ${abbreviatePath(cwd, 30)}`);
			}
			legendItems.push(`${ansiFg(activeOtherColor, "█")} other`);
		} else if (this.view === "dow") {
			activeColorMap = this.data.dowPalette.dowColors;
			for (const dow of this.data.dowPalette.orderedDows) {
				const c = activeColorMap.get(dow);
				if (c) legendItems.push(`${ansiFg(c, "█")} ${dow}`);
			}
		} else {
			activeColorMap = this.data.todPalette.todColors;
			for (const tod of this.data.todPalette.orderedTods) {
				const c = activeColorMap.get(tod);
				if (c) legendItems.push(`${ansiFg(c, "█")} ${todBucketLabel(tod)}`);
			}
		}

		const graphDescriptor = this.view === "dow" ? `share of ${metric.kind} by weekday` : `${metric.kind}/day`;
		const summary = rangeSummary(range, selectedDays, metric.kind) + dim(`   (graph: ${graphDescriptor})`);

		let graphLines: string[];
		if (this.view === "dow") {
			graphLines = renderDowDistributionLines(range, this.measurement, this.data.dowPalette.dowColors, width);
		} else {
			const maxScale = selectedDays === 7 ? 4 : selectedDays === 30 ? 3 : 2;
			const weeks = weeksForRange(range);
			const leftMargin = 4; // "Mon " (or 4 spaces)
			const gap = 1;
			const graphArea = Math.max(1, width - leftMargin);
			// Each week column uses: cellWidth + gap. Last column also gets gap (fine; we truncate anyway).
			const idealCellWidth = Math.floor((graphArea + gap) / Math.max(1, weeks)) - gap;
			const cellWidth = Math.min(maxScale, Math.max(1, idealCellWidth));

			graphLines = renderGraphLines(
				range,
				activeColorMap,
				activeOtherColor,
				this.measurement,
				{ cellWidth, gap },
				this.view,
			);
		}
		const tableLines =
			this.view === "model" ? renderModelTable(range, metric.kind, 8)
			: this.view === "cwd" ? renderCwdTable(range, metric.kind, 8)
			: this.view === "dow" ? renderDowTable(range, metric.kind)
			: renderTodTable(range, metric.kind);

		const lines: string[] = [];
		lines.push(truncateToWidth(header, width));
		lines.push(truncateToWidth(dim("←/→ range · ↑/↓ view · tab metric · q to close"), width));
		lines.push("");
		lines.push(truncateToWidth(summary, width));
		lines.push("");

		if (this.view === "dow") {
			for (const gl of graphLines) lines.push(truncateToWidth(gl, width));
		} else {
			// Render legend on the RIGHT of the graph if there is space.
			const graphWidth = Math.max(0, ...graphLines.map((l) => visibleWidth(l)));
			const sep = 2;
			const legendWidth = width - graphWidth - sep;
			const showSideLegend = legendWidth >= 22;

			if (showSideLegend) {
				const legendBlock: string[] = [];
				const legendTitle =
					this.view === "model" ? "Top models (30d palette):"
					: this.view === "cwd" ? "Top directories (30d palette):"
					: "Time of day:";
				legendBlock.push(dim(legendTitle));
				legendBlock.push(...legendItems);
				// Fit into 7 rows (same as graph). If too many, show a final "+N more" line.
				const maxLegendRows = graphLines.length;
				let legendLines = legendBlock.slice(0, maxLegendRows);
				if (legendBlock.length > maxLegendRows) {
					const remaining = legendBlock.length - (maxLegendRows - 1);
					legendLines = [...legendBlock.slice(0, maxLegendRows - 1), dim(`+${remaining} more`)];
				}
				while (legendLines.length < graphLines.length) legendLines.push("");

				const padRightAnsi = (s: string, target: number): string => {
					const w = visibleWidth(s);
					return w >= target ? s : s + " ".repeat(target - w);
				};

				for (let i = 0; i < graphLines.length; i++) {
					const left = padRightAnsi(graphLines[i] ?? "", graphWidth);
					const right = truncateToWidth(legendLines[i] ?? "", Math.max(0, legendWidth));
					lines.push(truncateToWidth(left + " ".repeat(sep) + right, width));
				}
			} else {
				// Fallback: graph only (legend will be shown below).
				for (const gl of graphLines) lines.push(truncateToWidth(gl, width));
				lines.push("");
				// Compact legend below, left-aligned.
				const legendTitleBelow =
					this.view === "model" ? "Top models (30d palette):"
					: this.view === "cwd" ? "Top directories (30d palette):"
					: "Time of day:";
				lines.push(truncateToWidth(dim(legendTitleBelow), width));
				for (const it of legendItems) lines.push(truncateToWidth(it, width));
			}
		}

		lines.push("");
		for (const tl of tableLines) lines.push(truncateToWidth(tl, width));

		// Ensure no overly long lines (truncateToWidth already), but keep at least 1 line.
		this.cachedWidth = width;
		this.cachedLines = lines.map((l) => (visibleWidth(l) > width ? truncateToWidth(l, width) : l));
		return this.cachedLines;
	}
}
