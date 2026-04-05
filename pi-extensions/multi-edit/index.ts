import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { applyClassicEdits } from "./classic.ts";
import { parsePatch, applyPatchOperations } from "./patch.ts";
import { multiEditSchema, type EditItem } from "./types.ts";
import { createRealWorkspace, createVirtualWorkspace } from "./workspace.ts";

export default function multiEditExtension(pi: ExtensionAPI) {
	pi.registerTool({
		name: "edit",
		label: "edit",
		description:
			"Edit a file by replacing exact text. The oldText must match exactly (including whitespace). Use this for precise, surgical edits. Supports a `multi` parameter for batch edits across one or more files, and a `patch` parameter for Codex-style patches.",
		promptSnippet:
			"Edit a file by replacing exact text. The oldText must match exactly (including whitespace). Use this for precise, surgical edits.",
		promptGuidelines: [
			"Use edit for precise changes (old text must match exactly)",
			"Use the `multi` parameter to apply multiple edits in a single tool call",
			"Use the `patch` parameter for Codex-style multi-file / hunk-based edits",
		],
		parameters: multiEditSchema,

		async execute(toolCallId, params, signal, onUpdate, ctx) {
			const { path, oldText, newText, multi, patch } = params;

			const hasAnyClassicParam = path !== undefined || oldText !== undefined || newText !== undefined || multi !== undefined;
			if (patch !== undefined && hasAnyClassicParam) {
				throw new Error("The `patch` parameter is mutually exclusive with path/oldText/newText/multi.");
			}

			if (patch !== undefined) {
				const ops = parsePatch(patch);
				await applyPatchOperations(ops, createVirtualWorkspace(ctx.cwd), ctx.cwd, signal, { collectDiff: false });
				const applied = await applyPatchOperations(ops, createRealWorkspace(), ctx.cwd, signal, { collectDiff: true });
				const summary = applied.map((r, i) => `${i + 1}. ${r.message}`).join("\n");
				const combinedDiff = applied
					.filter((r) => r.diff)
					.map((r) => `File: ${r.path}\n${r.diff}`)
					.join("\n\n");
				const firstChangedLine = applied.find((r) => r.firstChangedLine !== undefined)?.firstChangedLine;
				return {
					content: [{ type: "text" as const, text: `Applied patch with ${applied.length} operation(s).\n${summary}` }],
					details: {
						diff: combinedDiff,
						firstChangedLine,
					},
				};
			}

			const edits: EditItem[] = [];
			const hasTopLevel = path !== undefined && oldText !== undefined && newText !== undefined;

			if (hasTopLevel) {
				edits.push({ path: path!, oldText: oldText!, newText: newText! });
			} else if (path !== undefined || oldText !== undefined || newText !== undefined) {
				const hasOnlyPath = path !== undefined && oldText === undefined && newText === undefined;
				if (!hasOnlyPath || multi === undefined) {
					const missing: string[] = [];
					if (path === undefined) missing.push("path");
					if (oldText === undefined) missing.push("oldText");
					if (newText === undefined) missing.push("newText");
					throw new Error(
						`Incomplete top-level edit: missing ${missing.join(", ")}. Provide all three (path, oldText, newText) or use only the multi parameter.`,
					);
				}
			}

			if (multi) {
				for (const item of multi) {
					edits.push({
						path: item.path ?? path ?? "",
						oldText: item.oldText,
						newText: item.newText,
					});
				}
			}

			if (edits.length === 0) {
				throw new Error("No edits provided. Supply path/oldText/newText, a multi array, or a patch.");
			}

			for (let i = 0; i < edits.length; i++) {
				if (!edits[i].path) {
					throw new Error(
						`Edit ${i + 1} is missing a path. Provide a path on each multi item or set a top-level path to inherit.`,
					);
				}
			}

			try {
				await applyClassicEdits(edits, createVirtualWorkspace(ctx.cwd), ctx.cwd, signal, { collectDiff: false });
			} catch (err: any) {
				throw new Error(`Preflight failed before mutating files.\n${err.message ?? String(err)}`);
			}

			const results = await applyClassicEdits(edits, createRealWorkspace(), ctx.cwd, signal, { collectDiff: true });

			if (results.length === 1) {
				const r = results[0];
				return {
					content: [{ type: "text" as const, text: r.message }],
					details: {
						diff: r.diff ?? "",
						firstChangedLine: r.firstChangedLine,
					},
				};
			}

			const combinedDiff = results
				.filter((r) => r.diff)
				.map((r) => r.diff)
				.join("\n");

			const firstChanged = results.find((r) => r.firstChangedLine !== undefined)?.firstChangedLine;
			const summary = results.map((r, i) => `${i + 1}. ${r.message}`).join("\n");

			return {
				content: [{ type: "text" as const, text: `Applied ${results.length} edit(s) successfully.\n${summary}` }],
				details: {
					diff: combinedDiff,
					firstChangedLine: firstChanged,
				},
			};
		},
	});
}
