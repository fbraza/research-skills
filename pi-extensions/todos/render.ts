import { Text, type Theme } from "@mariozechner/pi-tui";
import type { TodoToolDetails, TodoRecord, TodoFrontMatter } from "./types.ts";
import {
	displayTodoId,
	formatTodoId,
	getTodoStatus,
	isTodoClosed,
	normalizeTodoId,
	splitTodosByAssignment,
} from "./utils.ts";
import {
	appendExpandHint,
	renderTodoDetail,
	renderTodoList,
} from "./format.ts";

export function renderCall(args: Record<string, unknown>, theme: Theme): Text {
	const action = typeof args.action === "string" ? args.action : "";
	const id = typeof args.id === "string" ? args.id : "";
	const normalizedId = id ? normalizeTodoId(id) : "";
	const title = typeof args.title === "string" ? args.title : "";
	let text = theme.fg("toolTitle", theme.bold("todo ")) + theme.fg("muted", action);
	if (normalizedId) {
		text += " " + theme.fg("accent", formatTodoId(normalizedId));
	}
	if (title) {
		text += " " + theme.fg("dim", `"${title}"`);
	}
	return new Text(text, 0, 0);
}

export function renderResult(
	result: { content: Array<{ type: string; text?: string }>; details?: TodoToolDetails },
	{ expanded, isPartial }: { expanded: boolean; isPartial: boolean },
	theme: Theme,
): Text {
	const details = result.details;
	if (isPartial) {
		return new Text(theme.fg("warning", "Processing..."), 0, 0);
	}
	if (!details) {
		const text = result.content[0];
		return new Text(text?.type === "text" ? text.text : "", 0, 0);
	}

	if (details.error) {
		return new Text(theme.fg("error", `Error: ${details.error}`), 0, 0);
	}

	if (details.action === "list" || details.action === "list-all") {
		let text = renderTodoList(theme, details.todos, expanded, details.currentSessionId);
		if (!expanded) {
			const { closedTodos } = splitTodosByAssignment(details.todos);
			if (closedTodos.length) {
				text = appendExpandHint(theme, text);
			}
		}
		return new Text(text, 0, 0);
	}

	if (!details.todo) {
		const text = result.content[0];
		return new Text(text?.type === "text" ? text.text : "", 0, 0);
	}

	let text = renderTodoDetail(theme, details.todo, expanded);
	const actionLabel =
		details.action === "create"
			? "Created"
			: details.action === "update"
				? "Updated"
				: details.action === "append"
					? "Appended to"
					: details.action === "delete"
						? "Deleted"
						: details.action === "claim"
							? "Claimed"
							: details.action === "release"
								? "Released"
								: null;
	if (actionLabel) {
		const lines = text.split("\n");
		lines[0] = theme.fg("success", "✓ ") + theme.fg("muted", `${actionLabel} `) + lines[0];
		text = lines.join("\n");
	}
	if (!expanded) {
		text = appendExpandHint(theme, text);
	}
	return new Text(text, 0, 0);
}
