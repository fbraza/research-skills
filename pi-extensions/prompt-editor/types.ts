import type { ThinkingLevel } from "@mariozechner/pi-coding-agent";

export type ModeName = string;

export type ModeSpec = {
	provider?: string;
	modelId?: string;
	thinkingLevel?: ThinkingLevel;
	/**
	 * Optional theme color token to use for the editor border.
	 * If unset, the border color is derived from the (current) thinking level.
	 */
	color?: string;
};

export type ModesFile = {
	version: 1;
	currentMode: ModeName;
	modes: Record<ModeName, ModeSpec>;
};

export interface PromptEntry {
	text: string;
	timestamp: number;
}

export type ModeRuntime = {
	filePath: string;
	fileMtimeMs: number | null;
	baseline: ModesFile | null;
	data: ModesFile;
	lastRealMode: string;
	currentMode: string;
	applying: boolean;
};
