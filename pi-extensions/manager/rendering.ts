import { truncateToWidth, visibleWidth, wrapTextWithAnsi } from "@mariozechner/pi-tui";

export function normalizeError(error: unknown): string {
	if (error instanceof Error && error.message) return error.message;
	return String(error);
}

export function padRight(text: string, width: number): string {
	const diff = Math.max(0, width - visibleWidth(text));
	return text + " ".repeat(diff);
}

export function centerText(text: string, width: number): string {
	const truncated = truncateToWidth(text, width, "");
	const diff = Math.max(0, width - visibleWidth(truncated));
	const left = Math.floor(diff / 2);
	return " ".repeat(left) + truncated + " ".repeat(diff - left);
}

export function boxedLine(content: string, innerWidth: number): string {
	return `│ ${padRight(truncateToWidth(content, innerWidth, ""), innerWidth)} │`;
}

export function wrapLine(line: string, width: number): string[] {
	const wrapped = wrapTextWithAnsi(line, width);
	return wrapped.length > 0 ? wrapped : [""];
}

export function renderPanel(
	width: number,
	title: string,
	bodyLines: string[],
	footerLines: string[] = [],
	subtitle?: string,
): string[] {
	const panelWidth = Math.max(24, width);
	const innerWidth = Math.max(20, panelWidth - 4);
	const lines: string[] = [];
	lines.push(`╭${"─".repeat(panelWidth - 2)}╮`);
	lines.push(boxedLine(centerText(title, innerWidth), innerWidth));
	if (subtitle) lines.push(boxedLine(subtitle, innerWidth));
	lines.push(`├${"─".repeat(panelWidth - 2)}┤`);
	for (const line of bodyLines.length > 0 ? bodyLines : [""]) {
		for (const wrapped of wrapLine(line, innerWidth)) lines.push(boxedLine(wrapped, innerWidth));
	}
	if (footerLines.length > 0) {
		lines.push(`├${"─".repeat(panelWidth - 2)}┤`);
		for (const line of footerLines) {
			for (const wrapped of wrapLine(line, innerWidth)) lines.push(boxedLine(wrapped, innerWidth));
		}
	}
	lines.push(`╰${"─".repeat(panelWidth - 2)}╯`);
	return lines.map((line) => truncateToWidth(line, panelWidth, ""));
}
