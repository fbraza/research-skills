import type { ExtensionAPI, ExtensionContext, ThinkingLevel } from "@mariozechner/pi-coding-agent";
import { ModelSelectorComponent, SettingsManager } from "@mariozechner/pi-coding-agent";
import {
	ALL_THINKING_LEVELS,
	CUSTOM_MODE_NAME,
	DEFAULT_MODE_ORDER,
	MODE_UI_ADD,
	MODE_UI_BACK,
	MODE_UI_CONFIGURE,
	THINKING_UNSET_LABEL,
} from "./constants.ts";
import {
	applyMode,
	getCurrentSelectionSpec,
	orderedModeNames,
	storeSelectionIntoMode,
} from "./modes.ts";
import { customOverlay, requestEditorRender, runtime } from "./state.ts";
import { persistRuntime, ensureRuntime } from "./storage.ts";
import type { ModeSpec } from "./types.ts";

function isDefaultModeName(name: string): boolean {
	return (DEFAULT_MODE_ORDER as readonly string[]).includes(name);
}

function isReservedModeName(name: string): boolean {
	return name === CUSTOM_MODE_NAME || name === MODE_UI_CONFIGURE || name === MODE_UI_ADD || name === MODE_UI_BACK;
}

function normalizeModeNameInput(name: string | undefined): string {
	return (name ?? "").trim();
}

function validateModeNameOrError(name: string, existing: Record<string, ModeSpec>, opts?: { allowExisting?: boolean }): string | null {
	if (!name) return "Mode name cannot be empty";
	if (/\s/.test(name)) return "Mode name cannot contain whitespace";
	if (isReservedModeName(name)) return `Mode name \"${name}\" is reserved`;
	if (!opts?.allowExisting && existing[name]) return `Mode \"${name}\" already exists`;
	return null;
}

async function handleModeChoiceUI(pi: ExtensionAPI, ctx: ExtensionContext, choice: string): Promise<void> {
	if (runtime.currentMode === CUSTOM_MODE_NAME && choice !== CUSTOM_MODE_NAME) {
		const action = await ctx.ui.select(`Mode \"${choice}\"`, ["use", "store"]);
		if (!action) return;

		if (action === "use") {
			await applyMode(pi, ctx, choice);
			return;
		}

		await ensureRuntime(pi, ctx);
		const overlay = customOverlay.value ?? getCurrentSelectionSpec(pi, ctx);
		await storeSelectionIntoMode(pi, ctx, choice, overlay);
		await applyMode(pi, ctx, choice);
		ctx.ui.notify(`Stored ${CUSTOM_MODE_NAME} into \"${choice}\"`, "info");
		return;
	}

	await applyMode(pi, ctx, choice);
}

export async function selectModeUI(pi: ExtensionAPI, ctx: ExtensionContext): Promise<void> {
	if (!ctx.hasUI) return;

	while (true) {
		await ensureRuntime(pi, ctx);
		const names = orderedModeNames(runtime.data.modes);
		const choice = await ctx.ui.select(`Mode (current: ${runtime.currentMode})`, [...names, MODE_UI_CONFIGURE]);
		if (!choice) return;

		if (choice === MODE_UI_CONFIGURE) {
			await configureModesUI(pi, ctx);
			continue;
		}

		await handleModeChoiceUI(pi, ctx, choice);
		return;
	}
}

async function configureModesUI(pi: ExtensionAPI, ctx: ExtensionContext): Promise<void> {
	if (!ctx.hasUI) return;

	while (true) {
		await ensureRuntime(pi, ctx);
		const names = orderedModeNames(runtime.data.modes);
		const choice = await ctx.ui.select("Configure modes", [...names, MODE_UI_ADD, MODE_UI_BACK]);
		if (!choice || choice === MODE_UI_BACK) return;

		if (choice === MODE_UI_ADD) {
			const created = await addModeUI(pi, ctx);
			if (created) {
				await editModeUI(pi, ctx, created);
			}
			continue;
		}

		await editModeUI(pi, ctx, choice);
	}
}

async function addModeUI(pi: ExtensionAPI, ctx: ExtensionContext): Promise<string | undefined> {
	if (!ctx.hasUI) return undefined;
	await ensureRuntime(pi, ctx);

	while (true) {
		const raw = await ctx.ui.input("New mode name", "e.g. docs, review, planning");
		if (raw === undefined) return undefined;

		const name = normalizeModeNameInput(raw);
		const err = validateModeNameOrError(name, runtime.data.modes);
		if (err) {
			ctx.ui.notify(err, "warning");
			continue;
		}

		const selection = customOverlay.value ?? getCurrentSelectionSpec(pi, ctx);
		runtime.data.modes[name] = {
			provider: selection.provider,
			modelId: selection.modelId,
			thinkingLevel: selection.thinkingLevel,
		};
		await persistRuntime(pi, ctx);
		ctx.ui.notify(`Added mode \"${name}\"`, "info");
		return name;
	}
}

async function editModeUI(pi: ExtensionAPI, ctx: ExtensionContext, mode: string): Promise<void> {
	if (!ctx.hasUI) return;

	let modeName = mode;

	while (true) {
		await ensureRuntime(pi, ctx);
		const spec = runtime.data.modes[modeName];
		if (!spec) return;

		const modelLabel = spec.provider && spec.modelId ? `${spec.provider}/${spec.modelId}` : "(no model)";
		const thinkingLabel = spec.thinkingLevel ?? THINKING_UNSET_LABEL;

		const actions = ["Change name", "Change model", "Change thinking level"];
		if (!isDefaultModeName(modeName)) actions.push("Delete mode");
		actions.push(MODE_UI_BACK);

		const action = await ctx.ui.select(
			`Edit mode \"${modeName}\"  model: ${modelLabel}  thinking: ${thinkingLabel}`,
			actions,
		);
		if (!action || action === MODE_UI_BACK) return;

		if (action === "Change name") {
			const renamed = await renameModeUI(pi, ctx, modeName);
			if (renamed) modeName = renamed;
			continue;
		}

		if (action === "Change model") {
			const selected = await pickModelForModeUI(ctx, spec);
			if (!selected) continue;
			spec.provider = selected.provider;
			spec.modelId = selected.modelId;
			runtime.data.modes[modeName] = spec;
			await persistRuntime(pi, ctx);
			ctx.ui.notify(`Updated model for \"${modeName}\"`, "info");

			if (runtime.currentMode === modeName) {
				await applyMode(pi, ctx, modeName);
			}
			continue;
		}

		if (action === "Change thinking level") {
			const level = await pickThinkingLevelForModeUI(ctx, spec.thinkingLevel);
			if (level === undefined) continue;

			if (level === null) {
				delete spec.thinkingLevel;
			} else {
				spec.thinkingLevel = level;
			}

			runtime.data.modes[modeName] = spec;
			await persistRuntime(pi, ctx);
			ctx.ui.notify(`Updated thinking level for \"${modeName}\"`, "info");

			if (runtime.currentMode === modeName) {
				await applyMode(pi, ctx, modeName);
			}
			continue;
		}

		if (action === "Delete mode") {
			const ok = await ctx.ui.confirm("Delete mode", `Delete mode \"${modeName}\"?`);
			if (!ok) continue;

			delete runtime.data.modes[modeName];
			await persistRuntime(pi, ctx);

			if (runtime.currentMode === modeName) {
				runtime.currentMode = CUSTOM_MODE_NAME;
				customOverlay.value = getCurrentSelectionSpec(pi, ctx);
			}
			if (runtime.lastRealMode === modeName) {
				runtime.lastRealMode = "default";
			}
			requestEditorRender.value?.();
			ctx.ui.notify(`Deleted mode \"${modeName}\"`, "info");
			return;
		}
	}
}

function renameModesRecord(modes: Record<string, ModeSpec>, oldName: string, newName: string): Record<string, ModeSpec> {
	const out: Record<string, ModeSpec> = {};
	for (const [k, v] of Object.entries(modes)) {
		if (k === oldName) out[newName] = v;
		else out[k] = v;
	}
	return out;
}

async function renameModeUI(pi: ExtensionAPI, ctx: ExtensionContext, oldName: string): Promise<string | undefined> {
	if (!ctx.hasUI) return undefined;

	if (isDefaultModeName(oldName)) {
		ctx.ui.notify(`Cannot rename default mode \"${oldName}\"`, "warning");
		return oldName;
	}

	await ensureRuntime(pi, ctx);

	while (true) {
		const raw = await ctx.ui.input(`Rename mode \"${oldName}\"`, oldName);
		if (raw === undefined) return undefined;

		const newName = normalizeModeNameInput(raw);
		if (!newName || newName === oldName) return oldName;

		const err = validateModeNameOrError(newName, runtime.data.modes);
		if (err) {
			ctx.ui.notify(err, "warning");
			continue;
		}

		runtime.data.modes = renameModesRecord(runtime.data.modes, oldName, newName);
		await persistRuntime(pi, ctx);

		if (runtime.currentMode === oldName) runtime.currentMode = newName;
		if (runtime.lastRealMode === oldName) runtime.lastRealMode = newName;
		requestEditorRender.value?.();

		ctx.ui.notify(`Renamed \"${oldName}\" → \"${newName}\"`, "info");
		return newName;
	}
}

async function pickModelForModeUI(
	ctx: ExtensionContext,
	spec: ModeSpec,
): Promise<{ provider: string; modelId: string } | undefined> {
	if (!ctx.hasUI) return undefined;

	const settingsManager = SettingsManager.inMemory();
	const currentModel = spec.provider && spec.modelId ? ctx.modelRegistry.find(spec.provider, spec.modelId) : ctx.model;
	const scopedModels: Array<{ model: any; thinkingLevel: string }> = [];

	return ctx.ui.custom<{ provider: string; modelId: string } | undefined>((tui, _theme, _keybindings, done) => {
		const selector = new ModelSelectorComponent(
			tui,
			currentModel,
			settingsManager,
			ctx.modelRegistry as any,
			scopedModels as any,
			(model) => done({ provider: model.provider, modelId: model.id }),
			() => done(undefined),
		);
		return selector;
	});
}

async function pickThinkingLevelForModeUI(
	ctx: ExtensionContext,
	current: ThinkingLevel | undefined,
): Promise<ThinkingLevel | null | undefined> {
	if (!ctx.hasUI) return undefined;

	const defaultValue = current ?? "off";
	const options = [...ALL_THINKING_LEVELS, THINKING_UNSET_LABEL];
	const ordered = [defaultValue, ...options.filter((x) => x !== defaultValue)];

	const choice = await ctx.ui.select("Thinking level", ordered);
	if (!choice) return undefined;
	if (choice === THINKING_UNSET_LABEL) return null;
	if (ALL_THINKING_LEVELS.includes(choice as ThinkingLevel)) return choice as ThinkingLevel;
	return undefined;
}
