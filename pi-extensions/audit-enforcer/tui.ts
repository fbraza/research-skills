import type { ExtensionContext } from "@mariozechner/pi-coding-agent";
import { CURSOR_MARKER, matchesKey, type Focusable, visibleWidth } from "@mariozechner/pi-tui";
import { listOpenAuditTodos } from "./todo-store.ts";
import type { AuditIssue, AuditState, TodoRecord, Verdict } from "./types.ts";

class MultiSelectPrompt implements Focusable {
	readonly width = 88;
	focused = false;
	private selectedIndex = 0;
	private readonly checked: boolean[];
	private title: string;
	private subtitle: string;
	private items: string[];
	private theme: ExtensionContext["ui"]["theme"];
	private done: (value: number[] | null) => void;

	constructor(
		title: string,
		subtitle: string,
		items: string[],
		theme: ExtensionContext["ui"]["theme"],
		done: (value: number[] | null) => void,
		defaultChecked = true,
	) {
		this.title = title;
		this.subtitle = subtitle;
		this.items = items;
		this.theme = theme;
		this.done = done;
		this.checked = items.map(() => defaultChecked);
	}

	handleInput(data: string): void {
		if (matchesKey(data, "escape")) {
			this.done(null);
			return;
		}
		if (matchesKey(data, "up")) {
			this.selectedIndex = Math.max(0, this.selectedIndex - 1);
			return;
		}
		if (matchesKey(data, "down")) {
			this.selectedIndex = Math.min(this.items.length - 1, this.selectedIndex + 1);
			return;
		}
		if (matchesKey(data, "space")) {
			this.checked[this.selectedIndex] = !this.checked[this.selectedIndex];
			return;
		}
		if (data.toLowerCase() === "a") {
			const shouldSelectAll = this.checked.some((value) => !value);
			for (let i = 0; i < this.checked.length; i++) this.checked[i] = shouldSelectAll;
			return;
		}
		if (matchesKey(data, "return")) {
			const selected = this.checked.map((value, index) => (value ? index : -1)).filter((index) => index >= 0);
			this.done(selected);
		}
	}

	render(_width: number): string[] {
		const theme = this.theme;
		const innerWidth = this.width - 2;
		const pad = (text: string) => text + " ".repeat(Math.max(0, innerWidth - visibleWidth(text)));
		const row = (text: string) => `${theme.fg("border", "│")}${pad(text)}${theme.fg("border", "│")}`;
		const lines: string[] = [];
		lines.push(theme.fg("border", `╭${"─".repeat(innerWidth)}╮`));
		lines.push(row(` ${theme.fg("accent", theme.bold(this.title))}`));
		lines.push(row(` ${theme.fg("muted", this.subtitle)}`));
		lines.push(row(""));
		for (let i = 0; i < this.items.length; i++) {
			const current = this.items[i];
			const isSelected = i === this.selectedIndex;
			const mark = this.checked[i] ? "[x]" : "[ ]";
			const prefix = isSelected ? theme.fg("accent", "▶") : " ";
			const marker = isSelected && this.focused ? CURSOR_MARKER : "";
			const text = `${prefix} ${mark} ${current}`;
			lines.push(row(` ${marker}${isSelected ? theme.fg("accent", text) : text}`));
		}
		lines.push(row(""));
		lines.push(row(` ${theme.fg("dim", "↑↓ move • space toggle • a toggle all • enter confirm • esc cancel")}`));
		lines.push(theme.fg("border", `╰${"─".repeat(innerWidth)}╯`));
		return lines;
	}

	invalidate(): void {}
	dispose(): void {}
}

export async function promptIssueSelection(ctx: ExtensionContext, issues: AuditIssue[]): Promise<Set<string> | null> {
	if (!ctx.hasUI || issues.length === 0) {
		return new Set(issues.map((issue) => issue.fingerprint));
	}

	const selectedIndices = await ctx.ui.custom<number[] | null>((_tui, theme, _kb, done) => {
		return new MultiSelectPrompt(
			"Scientific Audit Findings",
			"Select the issues you want to solve now. Unchecked issues stay as open todos.",
			issues.map((issue) => issue.text),
			theme,
			done,
			true,
		);
	}, { overlay: true });

	if (selectedIndices === null) return null;
	return new Set(selectedIndices.map((index) => issues[index]?.fingerprint).filter(Boolean) as string[]);
}

export async function promptTodoResolution(ctx: ExtensionContext, todos: TodoRecord[]): Promise<TodoRecord[] | null> {
	if (todos.length === 0) return [];
	if (!ctx.hasUI) return todos;
	const selectedIndices = await ctx.ui.custom<number[] | null>((_tui, theme, _kb, done) => {
		return new MultiSelectPrompt(
			"Resolve Audit Todos",
			"Select the audit issues that are fixed and should be marked done.",
			todos.map((todo) => todo.title),
			theme,
			done,
			false,
		);
	}, { overlay: true });
	if (selectedIndices === null) return null;
	return selectedIndices.map((index) => todos[index]).filter(Boolean) as TodoRecord[];
}

function buildStatusLine(verdict: Verdict | null, openCount: number, ctx: ExtensionContext): string {
	const theme = ctx.ui.theme;
	const issueText = `${openCount} open audit todo${openCount === 1 ? "" : "s"}`;
	if (!verdict) return theme.fg("muted", `Audit: idle • ${issueText}`);
	if (verdict === "PASS") return theme.fg("success", "Audit: PASS") + theme.fg("muted", ` • ${issueText}`);
	if (verdict === "REVIEW") return theme.fg("warning", "Audit: REVIEW") + theme.fg("muted", ` • ${issueText}`);
	return theme.fg("error", "Audit: FAIL") + theme.fg("muted", ` • ${issueText}`);
}

export async function updateStatus(ctx: ExtensionContext, state: AuditState): Promise<void> {
	const openCount = await listOpenAuditTodos(ctx.cwd).then((items) => items.length).catch(() => 0);
	ctx.ui.setStatus("audit-enforcer", buildStatusLine(state.lastVerdict, openCount, ctx));
}
