import { isAbsolute, resolve as resolvePath } from "path";
import { generateDiffString } from "./diff.ts";
import type { EditItem, EditResult, Workspace } from "./types.ts";

/**
 * Apply a list of classic edits (path/oldText/newText) sequentially via a Workspace.
 *
 * When multiple edits target the same file, they are sorted by their position in
 * the original file content (top-to-bottom) before applying.  This makes the
 * operation robust regardless of the order the model listed the edits.
 *
 * A forward cursor (`searchOffset`) advances after each replacement so that
 * duplicate oldText snippets are disambiguated by position.
 */
export async function applyClassicEdits(
	edits: EditItem[],
	workspace: Workspace,
	cwd: string,
	signal?: AbortSignal,
	options?: { collectDiff?: boolean },
): Promise<EditResult[]> {
	const collectDiff = options?.collectDiff ?? false;

	const fileGroups = new Map<string, { index: number; edit: EditItem }[]>();
	const editOrder: string[] = [];

	for (let i = 0; i < edits.length; i++) {
		const abs = isAbsolute(edits[i].path) ? resolvePath(edits[i].path) : resolvePath(cwd, edits[i].path);
		if (!fileGroups.has(abs)) {
			fileGroups.set(abs, []);
			editOrder.push(abs);
		}
		fileGroups.get(abs)!.push({ index: i, edit: edits[i] });
	}

	const results: EditResult[] = new Array(edits.length);

	for (const absPath of editOrder) {
		await workspace.checkWriteAccess(absPath);
	}

	for (const absPath of editOrder) {
		const group = fileGroups.get(absPath)!;

		if (signal?.aborted) {
			throw new Error("Operation aborted");
		}

		const originalContent = await workspace.readText(absPath);

		if (group.length > 1) {
			const positions = new Map<{ index: number; edit: EditItem }, number>();
			for (const entry of group) {
				const pos = originalContent.indexOf(entry.edit.oldText);
				positions.set(entry, pos === -1 ? Number.MAX_SAFE_INTEGER : pos);
			}
			group.sort((a, b) => positions.get(a)! - positions.get(b)!);
		}

		let content = originalContent;
		let searchOffset = 0;
		const appliedPairs = new Set<string>();

		for (const { index, edit } of group) {
			if (signal?.aborted) {
				throw new Error("Operation aborted");
			}

			const pos = content.indexOf(edit.oldText, searchOffset);

			if (pos === -1) {
				const pairKey = `${edit.oldText}\0${edit.newText}`;
				if (appliedPairs.has(pairKey)) {
					results[index] = {
						path: edit.path,
						success: true,
						message: `Skipped redundant edit in ${edit.path} (already replaced all occurrences).`,
					};
					continue;
				}

				results[index] = {
					path: edit.path,
					success: false,
					message: `Could not find the exact text in ${edit.path}. The old text must match exactly including all whitespace and newlines.`,
				};
				const filled = Array.from({ length: edits.length }, (_, i) => results[i]).filter(Boolean) as EditResult[];
				throw new Error(formatResults(filled, edits.length));
			}

			content = content.slice(0, pos) + edit.newText + content.slice(pos + edit.oldText.length);
			searchOffset = pos + edit.newText.length;
			appliedPairs.add(`${edit.oldText}\0${edit.newText}`);

			results[index] = {
				path: edit.path,
				success: true,
				message: `Edited ${edit.path}.`,
			};
		}

		await workspace.writeText(absPath, content);

		if (collectDiff) {
			const diffResult = generateDiffString(originalContent, content);
			const firstIdx = group[0].index;
			results[firstIdx].diff = diffResult.diff;
			results[firstIdx].firstChangedLine = diffResult.firstChangedLine;
		}
	}

	return results;
}

export function formatResults(results: EditResult[], totalEdits: number): string {
	const lines: string[] = [];

	for (let i = 0; i < results.length; i++) {
		const r = results[i];
		const status = r.success ? "✓" : "✗";
		lines.push(`${status} Edit ${i + 1}/${totalEdits} (${r.path}): ${r.message}`);
	}

	const remaining = totalEdits - results.length;
	if (remaining > 0) {
		lines.push(`⊘ ${remaining} remaining edit(s) skipped due to error.`);
	}

	return lines.join("\n");
}
