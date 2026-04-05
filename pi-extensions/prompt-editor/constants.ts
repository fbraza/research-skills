import type { ThinkingLevel } from "@mariozechner/pi-coding-agent";

export const DEFAULT_MODE_ORDER = ["default"] as const;
export const CUSTOM_MODE_NAME = "custom" as const;

export const MODE_UI_CONFIGURE = "Configure modes…";
export const MODE_UI_ADD = "Add mode…";
export const MODE_UI_BACK = "Back";

export const ALL_THINKING_LEVELS: ThinkingLevel[] = ["off", "minimal", "low", "medium", "high", "xhigh"];
export const THINKING_UNSET_LABEL = "(don't change)";

export const MAX_HISTORY_ENTRIES = 100;
export const MAX_RECENT_PROMPTS = 30;
