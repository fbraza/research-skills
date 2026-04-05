import { DynamicBorder } from "@mariozechner/pi-coding-agent";
import { Container, Key, Text, matchesKey, type Component, type TUI } from "@mariozechner/pi-tui";
import { formatUsd, joinComma, joinCommaStyled, renderUsageBar } from "./utils.ts";
import type { ContextViewData } from "./types.ts";

class ContextView implements Component {
	private tui: TUI;
	private theme: any;
	private onDone: () => void;
	private data: ContextViewData;
	private container: Container;
	private body: Text;
	private cachedWidth?: number;

	constructor(tui: TUI, theme: any, data: ContextViewData, onDone: () => void) {
		this.tui = tui;
		this.theme = theme;
		this.data = data;
		this.onDone = onDone;

		this.container = new Container();
		this.container.addChild(new DynamicBorder((s) => theme.fg("accent", s)));
		this.container.addChild(
			new Text(
				theme.fg("accent", theme.bold("Context")) + theme.fg("dim", "  (Esc/q/Enter to close)"),
				1,
				0,
			),
		);
		this.container.addChild(new Text("", 1, 0));

		this.body = new Text("", 1, 0);
		this.container.addChild(this.body);

		this.container.addChild(new Text("", 1, 0));
		this.container.addChild(new DynamicBorder((s) => theme.fg("accent", s)));
	}

	private rebuild(width: number): void {
		const muted = (s: string) => this.theme.fg("muted", s);
		const dim = (s: string) => this.theme.fg("dim", s);
		const text = (s: string) => this.theme.fg("text", s);

		const lines: string[] = [];

		// Window + bar
		if (!this.data.usage) {
			lines.push(muted("Window: ") + dim("(unknown)"));
		} else {
			const u = this.data.usage;
			lines.push(
				muted("Window: ") +
					text(`~${u.effectiveTokens.toLocaleString()} / ${u.contextWindow.toLocaleString()}`) +
					muted(`  (${u.percent.toFixed(1)}% used, ~${u.remainingTokens.toLocaleString()} left)`),
			);

			// bar width tries to fit within the viewport
			const barWidth = Math.max(10, Math.min(36, width - 10));

			// Prorate system prompt into current message context estimate, then add tools estimate.
			const sysInMessages = Math.min(u.systemPromptTokens, u.messageTokens);
			const convoInMessages = Math.max(0, u.messageTokens - sysInMessages);
			const bar =
				renderUsageBar(
					this.theme,
					{
						system: sysInMessages,
						tools: u.toolsTokens,
						convo: convoInMessages,
						remaining: u.remainingTokens,
					},
					u.contextWindow,
					barWidth,
				) +
				" " +
				dim("sys") +
				this.theme.fg("accent", "█") +
				" " +
				dim("tools") +
				this.theme.fg("warning", "█") +
				" " +
				dim("convo") +
				this.theme.fg("success", "█") +
				" " +
				dim("free") +
				this.theme.fg("dim", "█");
			lines.push(bar);
		}

		lines.push("");

		// System prompt + tools totals (approx)
		if (this.data.usage) {
			const u = this.data.usage;
			lines.push(
				muted("System: ") +
					text(`~${u.systemPromptTokens.toLocaleString()} tok`) +
					muted(` (AGENTS ~${u.agentTokens.toLocaleString()})`),
			);
			lines.push(
				muted("Tools: ") +
					text(`~${u.toolsTokens.toLocaleString()} tok`) +
					muted(` (${u.activeTools} active)`),
			);
		}

		lines.push(muted(`AGENTS (${this.data.agentFiles.length}): `) + text(this.data.agentFiles.length ? joinComma(this.data.agentFiles) : "(none)"));
		lines.push("");
		lines.push(muted(`Extensions (${this.data.extensions.length}): `) + text(this.data.extensions.length ? joinComma(this.data.extensions) : "(none)"));

		const loaded = new Set(this.data.loadedSkills);
		const skillsRendered = this.data.skills.length
			? joinCommaStyled(
					this.data.skills,
					(name) => (loaded.has(name) ? this.theme.fg("success", name) : this.theme.fg("muted", name)),
					this.theme.fg("muted", ", "),
				)
			: "(none)";
		lines.push(muted(`Skills (${this.data.skills.length}): `) + skillsRendered);
		lines.push("");
		lines.push(
			muted("Session: ") +
				text(`${this.data.session.totalTokens.toLocaleString()} tokens`) +
				muted(" · ") +
				text(formatUsd(this.data.session.totalCost)),
		);

		this.body.setText(lines.join("\n"));
		this.cachedWidth = width;
	}

	handleInput(data: string): void {
		if (
			matchesKey(data, Key.escape) ||
			matchesKey(data, Key.ctrl("c")) ||
			data.toLowerCase() === "q" ||
			data === "\r"
		) {
			this.onDone();
			return;
		}
	}

	invalidate(): void {
		this.container.invalidate();
		this.cachedWidth = undefined;
	}

	render(width: number): string[] {
		if (this.cachedWidth !== width) this.rebuild(width);
		return this.container.render(width);
	}
}

export { ContextView };
