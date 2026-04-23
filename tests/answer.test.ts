import assert from "node:assert/strict";
import test from "node:test";

import answerExtension from "../pi-extensions/answer/index.ts";
import { parseExtractionResult } from "../pi-extensions/answer/parsing.ts";
import { selectExtractionModel } from "../pi-extensions/answer/model-selection.ts";

// ---------------------------------------------------------------------------
// Parsing
// ---------------------------------------------------------------------------

test("parseExtractionResult handles plain JSON", () => {
	const result = parseExtractionResult('{"questions": [{"question": "Q1?"}]}');
	assert.ok(result);
	assert.equal(result!.questions.length, 1);
	assert.equal(result!.questions[0].question, "Q1?");
});

test("parseExtractionResult handles JSON inside markdown code block", () => {
	const result = parseExtractionResult('```json\n{"questions": [{"question": "Q2?", "context": "ctx"}]}\n```');
	assert.ok(result);
	assert.equal(result!.questions.length, 1);
	assert.equal(result!.questions[0].context, "ctx");
});

test("parseExtractionResult returns null for invalid JSON", () => {
	const result = parseExtractionResult("not json");
	assert.equal(result, null);
});

test("parseExtractionResult returns null for missing questions array", () => {
	const result = parseExtractionResult('{"foo": "bar"}');
	assert.equal(result, null);
});

// ---------------------------------------------------------------------------
// Model selection
// ---------------------------------------------------------------------------

test("selectExtractionModel falls back to current model when no codex/haiku", async () => {
	const currentModel = { id: "gpt-4o", api: "openai-chat", provider: "openai" } as any;
	const registry = {
		find: () => undefined,
		getApiKeyAndHeaders: async () => ({ ok: true }),
	} as any;

	const selected = await selectExtractionModel(currentModel, registry);
	assert.equal(selected.id, "gpt-4o");
});

test("selectExtractionModel prefers codex when available and authed", async () => {
	const currentModel = { id: "gpt-4o", api: "openai-chat", provider: "openai" } as any;
	const codex = { id: "gpt-5.1-codex-mini", api: "openai-codex", provider: "openai-codex" } as any;
	const registry = {
		find: (_p: string, id: string) => (id === "gpt-5.1-codex-mini" ? codex : undefined),
		getApiKeyAndHeaders: async (m: any) => ({ ok: m.id === "gpt-5.1-codex-mini" }),
	} as any;

	const selected = await selectExtractionModel(currentModel, registry);
	assert.equal(selected.id, "gpt-5.1-codex-mini");
});

// ---------------------------------------------------------------------------
// Extension registration
// ---------------------------------------------------------------------------

test("answer extension registers command and shortcut", () => {
	const commands: Array<{ name: string }> = [];
	const shortcuts: Array<{ key: string }> = [];
	const renderers: Array<{ type: string }> = [];

	const fakePi = {
		registerCommand(name: string, _info: any) {
			commands.push({ name });
		},
		registerShortcut(key: string, _info: any) {
			shortcuts.push({ key });
		},
		registerMessageRenderer(type: string, _renderer: any) {
			renderers.push({ type });
		},
	} as any;

	answerExtension(fakePi);

	assert.deepEqual(
		commands.map((c) => c.name),
		["answer"],
	);
	assert.deepEqual(
		shortcuts.map((s) => s.key),
		["ctrl+."],
	);
	assert.deepEqual(
		renderers.map((r) => r.type),
		["answers"],
	);
});
