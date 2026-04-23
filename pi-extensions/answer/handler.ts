import { complete, type Api, type Model, type UserMessage } from "@mariozechner/pi-ai";
import { BorderedLoader } from "@mariozechner/pi-coding-agent";
import type { ExtensionAPI, ExtensionContext } from "@mariozechner/pi-coding-agent";
import { SYSTEM_PROMPT } from "./constants.ts";
import { selectExtractionModel } from "./model-selection.ts";
import { parseExtractionResult } from "./parsing.ts";
import { QnAComponent } from "./qna-component.ts";
import type { ExtractionResult } from "./types.ts";

export type QuestionExtractionOutcome =
	| { kind: "ok"; result: ExtractionResult }
	| { kind: "cancelled" }
	| { kind: "error"; message: string };

function getLastAssistantText(ctx: ExtensionContext): { status: "ok"; text: string } | { status: "incomplete"; reason: string } | { status: "missing" } {
	const branch = ctx.sessionManager.getBranch();
	let lastAssistantText: string | undefined;

	for (let i = branch.length - 1; i >= 0; i--) {
		const entry = branch[i];
		if (entry.type === "message") {
			const msg = entry.message;
			if ("role" in msg && msg.role === "assistant") {
				// Allow "stop", "length", and "toolUse" — these can all contain valid questions.
				// Only reject genuine error/aborted states.
				if (msg.stopReason === "error" || msg.stopReason === "aborted") {
					return { status: "incomplete", reason: msg.stopReason };
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
): Promise<QuestionExtractionOutcome> {
	return await ctx.ui.custom<QuestionExtractionOutcome>((tui, theme, _kb, done) => {
		const loader = new BorderedLoader(tui, theme, `Extracting questions using ${extractionModel.id}...`);
		loader.onAbort = () => done({ kind: "cancelled" });

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
				{ apiKey: auth.apiKey, signal: loader.signal },
			);

			if (response.stopReason === "aborted") {
				return { kind: "cancelled" } as QuestionExtractionOutcome;
			}

			const responseText = response.content
				.filter((c): c is { type: "text"; text: string } => c.type === "text")
				.map((c) => c.text)
				.join("\n");

			const parsed = parseExtractionResult(responseText);
			if (!parsed) {
				return { kind: "error", message: "Could not parse questions from model response" } as QuestionExtractionOutcome;
			}
			return { kind: "ok", result: parsed } as QuestionExtractionOutcome;
		};

		doExtract()
			.then(done)
			.catch((err) => {
				const msg = err instanceof Error ? err.message : String(err);
				done({ kind: "error", message: msg });
			});

		return loader;
	});
}

export function createAnswerHandler(pi: ExtensionAPI) {
	return async function answerHandler(ctx: ExtensionContext) {
		try {
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
				ctx.ui.notify(`Last assistant message incomplete (${lastAssistant.reason})`, "error");
				return;
			}
			if (lastAssistant.status === "missing") {
				ctx.ui.notify("No assistant text found in the last message", "error");
				return;
			}

			const extractionModel = await selectExtractionModel(ctx.model, ctx.modelRegistry);
			const outcome = await extractQuestions(ctx, lastAssistant.text, extractionModel);

			if (outcome.kind === "cancelled") {
				ctx.ui.notify("Cancelled", "info");
				return;
			}

			if (outcome.kind === "error") {
				ctx.ui.notify(`Question extraction failed: ${outcome.message}`, "error");
				return;
			}

			if (outcome.result.questions.length === 0) {
				ctx.ui.notify("No questions found in the last message", "info");
				return;
			}

			const answersResult = await ctx.ui.custom<string | null>((tui, _theme, _kb, done) => {
				return new QnAComponent(outcome.result.questions, tui, done);
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
		} catch (err) {
			const msg = err instanceof Error ? err.message : String(err);
			ctx.ui.notify(`/answer failed: ${msg}`, "error");
		}
	};
}
