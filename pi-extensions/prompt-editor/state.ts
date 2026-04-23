import type { ThinkingLevel } from "@mariozechner/pi-coding-agent";
import type { ModeRuntime, ModeSpec } from "./types.ts";

export const runtime: ModeRuntime = {
	filePath: "",
	fileMtimeMs: null,
	baseline: null,
	data: { version: 1, currentMode: "default", modes: {} },
	lastRealMode: "default",
	currentMode: "default",
	applying: false,
};

export const customOverlay: { value: ModeSpec | null } = { value: null };
export const requestEditorRender: { value?: () => void } = {};
export const lastObservedModel: { value: { provider?: string; modelId?: string } } = { value: {} };
export const currentThinkingLevel: { value: ThinkingLevel } = { value: "off" };
export const loadCounter: { value: number } = { value: 0 };
