import type { Api, Model } from "@mariozechner/pi-ai";
import type { ModelRegistry } from "@mariozechner/pi-coding-agent";
import { CODEX_MODEL_ID, HAIKU_MODEL_ID } from "./constants.ts";

/**
 * Prefer Codex mini for extraction when available, otherwise fallback to haiku or the current model.
 */
export async function selectExtractionModel(
	currentModel: Model<Api>,
	modelRegistry: ModelRegistry,
): Promise<Model<Api>> {
	const codexModel = modelRegistry.find("openai-codex", CODEX_MODEL_ID);
	if (codexModel) {
		const auth = await modelRegistry.getApiKeyAndHeaders(codexModel);
		if (auth.ok) {
			return codexModel;
		}
	}

	const haikuModel = modelRegistry.find("anthropic", HAIKU_MODEL_ID);
	if (!haikuModel) {
		return currentModel;
	}

	const auth = await modelRegistry.getApiKeyAndHeaders(haikuModel);
	if (!auth.ok) {
		return currentModel;
	}

	return haikuModel;
}
