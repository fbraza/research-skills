import type { ExtensionAPI, ExtensionContext, ModelSelectEvent } from "@mariozechner/pi-coding-agent";
import { applyEditor } from "./prompt-history.ts";
import {
	CUSTOM_MODE_NAME,
} from "./constants.ts";
import {
	applyMode,
	cycleMode,
	getCurrentSelectionSpec,
	inferModeFromSelection,
	orderedModeNames,
	selectModeUI,
	storeSelectionIntoMode,
} from "./modes.ts";
import { ensureRuntime } from "./storage.ts";
import { currentThinkingLevel, customOverlay, lastObservedModel, loadCounter, requestEditorRender, runtime } from "./state.ts";

export default function promptEditorExtension(pi: ExtensionAPI) {
	pi.registerCommand("mode", {
		description: "Select prompt mode",
		handler: async (args, ctx) => {
			const tokens = args
				.split(/\s+/)
				.map((x) => x.trim())
				.filter(Boolean);

			if (tokens.length === 0) {
				await selectModeUI(pi, ctx);
				return;
			}

			if (tokens[0] === "store") {
				await ensureRuntime(pi, ctx);

				let target = tokens[1];
				if (!target) {
					if (!ctx.hasUI) return;
					const names = orderedModeNames(runtime.data.modes);
					target = await ctx.ui.select("Store current selection into mode", names);
					if (!target) return;
				}

				if (target === CUSTOM_MODE_NAME) {
					if (ctx.hasUI) ctx.ui.notify(`Cannot store into "${CUSTOM_MODE_NAME}"`, "warning");
					return;
				}

				const selection = customOverlay.value ?? getCurrentSelectionSpec(pi, ctx);
				await storeSelectionIntoMode(pi, ctx, target, selection);
				if (ctx.hasUI) ctx.ui.notify(`Stored current selection into "${target}"`, "info");
				return;
			}

			await applyMode(pi, ctx, tokens[0]!);
		},
	});

	pi.registerShortcut("ctrl+shift+m", {
		description: "Select prompt mode",
		handler: async (ctx) => {
			await selectModeUI(pi, ctx);
		},
	});

	pi.registerShortcut("ctrl+space", {
		description: "Cycle prompt mode",
		handler: async (ctx) => {
			await cycleMode(pi, ctx, 1);
		},
	});

	const handleSessionStartLike = async (ctx: ExtensionContext) => {
		lastObservedModel.value = { provider: ctx.model?.provider, modelId: ctx.model?.id };
		currentThinkingLevel.value = pi.getThinkingLevel();
		await ensureRuntime(pi, ctx);
		customOverlay.value = null;

		const inferred = inferModeFromSelection(ctx, pi, runtime.data);
		if (inferred) {
			runtime.currentMode = inferred;
			runtime.lastRealMode = inferred;
		} else {
			runtime.currentMode = CUSTOM_MODE_NAME;
			customOverlay.value = getCurrentSelectionSpec(pi, ctx);
		}

		applyEditor(ctx);
	};

	pi.on("session_start", async (_event, ctx) => {
		await handleSessionStartLike(ctx);
	});

	pi.on("session_switch", async (_event, ctx) => {
		await handleSessionStartLike(ctx);
	});

	pi.on("model_select", async (event: ModelSelectEvent, ctx) => {
		lastObservedModel.value = { provider: event.model.provider, modelId: event.model.id };
		currentThinkingLevel.value = pi.getThinkingLevel();
		if (runtime.applying) return;

		await ensureRuntime(pi, ctx);
		if (runtime.currentMode !== CUSTOM_MODE_NAME) {
			runtime.lastRealMode = runtime.currentMode;
		}
		runtime.currentMode = CUSTOM_MODE_NAME;

		customOverlay.value = {
			provider: event.model.provider,
			modelId: event.model.id,
			thinkingLevel: pi.getThinkingLevel(),
		};

		if (ctx.hasUI) {
			requestEditorRender.value?.();
		}
	});

	pi.on("session_shutdown", async (_event, ctx) => {
		loadCounter.value += 1;
		requestEditorRender.value = undefined;
		if (ctx.hasUI) {
			ctx.ui.setEditorComponent(undefined);
		}
	});
}
