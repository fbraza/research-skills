import path from "node:path";
import os from "node:os";

export const REMOTE_REPO = "fbraza/research-skills";
export const REMOTE_SKILLS_PATH = "skills";
export const LOCAL_SKILLS_DIR = path.join(".agents", "skills");
export const CACHE_DIR = path.join(os.tmpdir(), "bio-skills-cache");
export const ALL_ID = "__all__";
export const SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];

export interface ExecResult {
	stdout: string;
	stderr: string;
	code: number;
	killed?: boolean;
}

export type ExecFn = (command: string, args: string[], options?: { timeout?: number; signal?: AbortSignal }) => Promise<ExecResult>;

export type Screen = "mode" | "loading" | "list" | "empty" | "error" | "progress";
export type ActionMode = "install" | "update" | "remove";
export type ProgressStatus = "waiting" | "running" | "done" | "failed";

export interface ProgressItem {
	name: string;
	status: ProgressStatus;
	error?: string;
}

export interface OverlayResult {
	changed: boolean;
}

export interface ListRow {
	id: string;
	label: string;
	description?: string;
}
