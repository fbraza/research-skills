import { Type } from "@sinclair/typebox";

export const editItemSchema = Type.Object({
	path: Type.Optional(Type.String({ description: "Path to the file to edit (relative or absolute). Inherits from top-level path if omitted." })),
	oldText: Type.String({ description: "Exact text to find and replace (must match exactly)" }),
	newText: Type.String({ description: "New text to replace the old text with" }),
});

export const multiEditSchema = Type.Object({
	path: Type.Optional(Type.String({ description: "Path to the file to edit (relative or absolute)" })),
	oldText: Type.Optional(Type.String({ description: "Exact text to find and replace (must match exactly)" })),
	newText: Type.Optional(Type.String({ description: "New text to replace the old text with" })),
	multi: Type.Optional(
		Type.Array(editItemSchema, {
			description: "Multiple edits to apply in sequence. Each item has path, oldText, and newText.",
		}),
	),
	patch: Type.Optional(
		Type.String({
			description:
				"Codex-style apply_patch payload (*** Begin Patch ... *** End Patch). Mutually exclusive with path/oldText/newText/multi.",
		}),
	),
});

export interface EditItem {
	path: string;
	oldText: string;
	newText: string;
}

export interface EditResult {
	path: string;
	success: boolean;
	message: string;
	diff?: string;
	firstChangedLine?: number;
}

export interface UpdateChunk {
	changeContext?: string;
	oldLines: string[];
	newLines: string[];
	isEndOfFile: boolean;
}

export type PatchOperation =
	| { kind: "add"; path: string; contents: string }
	| { kind: "delete"; path: string }
	| { kind: "update"; path: string; chunks: UpdateChunk[] };

export interface PatchOpResult {
	path: string;
	message: string;
	diff?: string;
	firstChangedLine?: number;
}

export interface Workspace {
	readText: (absolutePath: string) => Promise<string>;
	writeText: (absolutePath: string, content: string) => Promise<void>;
	deleteFile: (absolutePath: string) => Promise<void>;
	exists: (absolutePath: string) => Promise<boolean>;
	/** Check that the file is writable. Rejects if not. No-op on virtual workspaces. */
	checkWriteAccess: (absolutePath: string) => Promise<void>;
}
