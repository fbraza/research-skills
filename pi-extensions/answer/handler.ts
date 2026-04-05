import { complete, type Api, type Model, type UserMessage } from "@mariozechner/pi-ai";
import { BorderedLoader } from "@mariozechner/pi-coding-agent";
import type { ExtensionAPI, ExtensionContext } from "@mariozechner/pi-coding-agent";
import { SYSTEM_PROMPT } from "./constants.ts";
import { selectExtractionModel } from "./model-selection.ts";
import { parseExtractionResult } from "./parsing.ts";
import { QnAComponent } from "./qna-component.ts";
import type { ExtractionResult } from "./types.ts";

function getLastAssistantText(ctx: ExtensionContext): { status: "ok"; text: string } | { status: "incomplete" } | { status: "missing" } {
	const branch = ctx.sessionManager.getBranch();
	let lastAssistantText: string | undefined;

	for (let i = branch.length - 1; i >= 0; i--) {
		const entry = branch[i];
		if (entry.type === "message") {
			const msg = entry.message;
			if ("role" in msg && msg.role === "assistant") {
				if (msg.stopReason !== "stop") {
					ctx.ui.notify(`Last assistant message incomplete (${msg.stopReason})`, "error");
					return { status: "incomplete" };
				}
				const textParts = msg.content
					.filter((c): c is { type: "text"; text: string } => c.type === "text")
					.map((c) => c.text);
				if (textParts.length > 0) {
					lastAssistantText = textParts.join("\n");
					break;
				}
			}
		}
	}

	if (!lastAssistantText) {
		return { status: "missing" };
	}

	return { status: "ok", text: lastAssistantText };
}

async function extractQuestions(
	ctx: ExtensionContext,
	lastAssistantText: string,
	extractionModel: Model<Api>,
): Promise<ExtractionResult | null> {
	return await ctx.ui.custom<ExtractionResult | null>((tui, theme, _kb, done) => {
		const loader = new BorderedLoader(tui, theme, `Extracting questions using ${extractionModel.id}...`);
		loader.onAbort = () => done(null);

		const doExtract = async () => {
			const auth = await ctx.modelRegistry.getApiKeyAndHeaders(extractionModel);
			if (!auth.ok) {
				const errorMessage = "error" in auth ? auth.error : `No API key for ${extractionModel.provider}`;
				throw new Error(errorMessage);
			}
			const userMessage: UserMessage = {
				role: "user",
				content: [{ type: "text", text: lastAssistantText }],
				timestamp: Date.now(),
			};

			const response = await complete(
				extractionModel,
				{ systemPrompt: SYSTEM_PROMPT, messages: [userMessage] },
				{ apiKey: auth.apiKey, headers: auth.headers, signal: loader.signal },
			);

			if (response.stopReason === "aborted") {
				return null;
			}

			const responseText = response.content
				.filter((c): c is { type: "text"; text: string } => c.type === "text")
				.map((c) => c.text)
				.join("\n");

			return parseExtractionResult(responseText);
		};

		doExtract()
			.then(done)
			.catch(() => done(null));

		return loader;
	});
}

export function createAnswerHandler(pi: ExtensionAPI) {
	return async function answerHandler(ctx: ExtensionContext) {
		if (!ctx.hasUI) {
			ctx.ui.notify("answer requires interactive mode", "error");
			return;
		}

		if (!ctx.model) {
			ctx.ui.notify("No model selected", "error");
			return;
		}

		const lastAssistant = getLastAssistantText(ctx);
		if (lastAssistant.status === "incomplete") {
			return;
		}
		if (lastAssistant.status === "missing") {
			ctx.ui.notify("No assistant messages found", "error");
			return;
		}

		const extractionModel = await selectExtractionModel(ctx.model, ctx.modelRegistry);
		const extractionResult = await extractQuestions(ctx, lastAssistant.text, extractionModel);

		if (extractionResult === null) {
			ctx.ui.notify("Cancelled", "info");
			return;
		}

		if (extractionResult.questions.length === 0) {
			ctx.ui.notify("No questions found in the last message", "info");
			return;
		}

		const answersResult = await ctx.ui.custom<string | null>((tui, _theme, _kb, done) => {
			return new QnAComponent(extractionResult.questions, tui, done);
		});

		if (answersResult === null) {
			ctx.ui.notify("Cancelled", "info");
			return;
		}

		pi.sendMessage(
			{
				customType: "answers",
				content: "I answered your questions in the following way:\n\n" + answersResult,
				display: true,
			},
			{ triggerTurn: true },
		);
	};
}
