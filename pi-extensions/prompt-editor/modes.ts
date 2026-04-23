import type { ExtensionAPI, ExtensionContext, ThinkingLevel } from "@mariozechner/pi-coding-agent";
import { CUSTOM_MODE_NAME } from "./constants.ts";
import { currentThinkingLevel, customOverlay, lastObservedModel, requestEditorRender, runtime } from "./state.ts";
import { ensureRuntime } from "./storage.ts";
import type { ModeSpec, ModesFile } from "./types.ts";

export function orderedModeNames(modes: Record<string, ModeSpec>): string[] {
	return Object.keys(modes).filter((name) => name !== CUSTOM_MODE_NAME);
}

type BorderTheme = Pick<ExtensionContext["ui"]["theme"], "fg" | "getFgAnsi" | "getThinkingBorderColor">;

export function getModeBorderColor(theme: BorderTheme, mode: string, thinkingLevel: ThinkingLevel): (text: string) => string {
	const spec = runtime.data.modes[mode];

	if (spec?.color) {
		try {
			theme.getFgAnsi(spec.color as any);
			return (text: string) => theme.fg(spec.color as any, text);
		} catch {}
	}

	return theme.getThinkingBorderColor(thinkingLevel);
}

export function inferModeFromSelection(ctx: ExtensionContext, pi: ExtensionAPI, data: ModesFile): string | null {
	const provider = ctx.model?.provider;
	const modelId = ctx.model?.id;
	const thinkingLevel = pi.getThinkingLevel();
	if (!provider || !modelId) return null;

	const names = orderedModeNames(data.modes);
	const supportsThinking = Boolean(ctx.model?.reasoning);

	if (supportsThinking) {
		for (const name of names) {
			const spec = data.modes[name];
			if (!spec) continue;
			if (spec.provider !== provider || spec.modelId !== modelId) continue;
			if ((spec.thinkingLevel ?? undefined) !== thinkingLevel) continue;
			return name;
		}
		return null;
	}

	const candidates: string[] = [];
	for (const name of names) {
		const spec = data.modes[name];
		if (!spec) continue;
		if (spec.provider !== provider || spec.modelId !== modelId) continue;
		candidates.push(name);
	}
	if (candidates.length === 0) return null;

	for (const name of candidates) {
		const spec = data.modes[name];
		if (!spec) continue;
		if ((spec.thinkingLevel ?? "off") === thinkingLevel) return name;
	}

	for (const name of candidates) {
		const spec = data.modes[name];
		if (!spec) continue;
		if (!spec.thinkingLevel) return name;
	}

	return candidates[0] ?? null;
}

export function getCurrentSelectionSpec(pi: ExtensionAPI, _ctx: ExtensionContext): ModeSpec {
	currentThinkingLevel.value = pi.getThinkingLevel();
	return {
		provider: lastObservedModel.value.provider,
		modelId: lastObservedModel.value.modelId,
		thinkingLevel: currentThinkingLevel.value,
	};
}

export async function storeSelectionIntoMode(pi: ExtensionAPI, ctx: ExtensionContext, mode: string, selection: ModeSpec): Promise<void> {
	if (mode === CUSTOM_MODE_NAME) return;

	await ensureRuntime(pi, ctx);
	const { persistRuntime } = await import("./storage.ts");

	const existingTarget = runtime.data.modes[mode] ?? {};
	const next: ModeSpec = { ...existingTarget };

	if (selection.provider && selection.modelId) {
		next.provider = selection.provider;
		next.modelId = selection.modelId;
	}
	if (selection.thinkingLevel) next.thinkingLevel = selection.thinkingLevel;

	runtime.data.modes[mode] = next;
	await persistRuntime(pi, ctx);
}

export async function applyMode(pi: ExtensionAPI, ctx: ExtensionContext, mode: string): Promise<void> {
	await ensureRuntime(pi, ctx);

	if (mode === CUSTOM_MODE_NAME) {
		runtime.currentMode = CUSTOM_MODE_NAME;
		customOverlay.value = getCurrentSelectionSpec(pi, ctx);
		if (ctx.hasUI) requestEditorRender.value?.();
		return;
	}

	const spec = runtime.data.modes[mode];
	if (!spec) {
		if (ctx.hasUI) {
			ctx.ui.notify(`Unknown mode: ${mode}`, "warning");
		}
		return;
	}

	runtime.currentMode = mode;
	runtime.lastRealMode = mode;
	customOverlay.value = null;

	runtime.applying = true;
	let modelAppliedOk = true;
	try {
		if (spec.provider && spec.modelId) {
			const m = ctx.modelRegistry.find(spec.provider, spec.modelId);
			if (m) {
				const ok = await pi.setModel(m);
				modelAppliedOk = ok;
				if (!ok && ctx.hasUI) {
					ctx.ui.notify(`No API key available for ${spec.provider}/${spec.modelId}`, "warning");
				}
			} else {
				modelAppliedOk = false;
				if (ctx.hasUI) {
					ctx.ui.notify(`Mode "${mode}" references unknown model ${spec.provider}/${spec.modelId}`, "warning");
				}
			}
		}

		if (spec.thinkingLevel) {
			pi.setThinkingLevel(spec.thinkingLevel);
			currentThinkingLevel.value = pi.getThinkingLevel();
		}
	} finally {
		runtime.applying = false;
	}

	if (!modelAppliedOk) {
		runtime.currentMode = CUSTOM_MODE_NAME;
		customOverlay.value = getCurrentSelectionSpec(pi, ctx);
	}

	if (ctx.hasUI) {
		requestEditorRender.value?.();
	}
}

export async function cycleMode(pi: ExtensionAPI, ctx: ExtensionContext, direction: 1 | -1 = 1): Promise<void> {
	if (!ctx.hasUI) return;
	await ensureRuntime(pi, ctx);
	const names = orderedModeNames(runtime.data.modes);
	if (names.length === 0) return;

	const baseMode = runtime.currentMode === CUSTOM_MODE_NAME ? runtime.lastRealMode : runtime.currentMode;
	const idx = Math.max(0, names.indexOf(baseMode));
	const next = names[(idx + direction + names.length) % names.length] ?? names[0]!;
	await applyMode(pi, ctx, next);
}

export { selectModeUI } from "./mode-ui.ts";
