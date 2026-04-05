import assert from "node:assert/strict";
import test from "node:test";

import literatureToolsExtension from "../pi-extensions/literature-tools/index.ts";
import { createFetchFulltextTool } from "../pi-extensions/literature-tools/fulltext.ts";
import { createPubmedSearchTool } from "../pi-extensions/literature-tools/pubmed.ts";

const originalFetch = globalThis.fetch;

test("literature extension registers all expected tools", () => {
	const tools: Array<{ name: string }> = [];
	const fakePi = {
		registerTool(tool: { name: string }) {
			tools.push(tool);
		},
	} as any;

	literatureToolsExtension(fakePi);

	assert.deepEqual(
		tools.map((tool) => tool.name),
		["pubmed_search", "preprint_search", "semantic_scholar_search", "fetch_fulltext"],
	);
});

test("pubmed_search emits pi-compliant progress updates and returns text content", async () => {
	globalThis.fetch = async () =>
		new Response(
			JSON.stringify({
				esearchresult: { idlist: ["12345"], count: "1" },
			}),
			{
				status: 200,
				headers: { "content-type": "application/json" },
			},
		);

	const tool = createPubmedSearchTool();
	const updates: any[] = [];
	const result = await tool.execute(
		"tool-call",
		{ query: "trained immunity", max_results: 1, fetch_abstracts: false },
		undefined,
		(update: any) => updates.push(update),
	);

	assert.equal(updates.length, 1);
	assert.deepEqual(updates[0].content, [{ type: "text", text: "Searching PubMed for: trained immunity" }]);
	assert.deepEqual(updates[0].details, {});
	assert.equal(result.isError, undefined);
	assert.equal(result.content[0].type, "text");
	assert.deepEqual(JSON.parse(result.content[0].text), [{ pmid: "12345", title: "PubMed record", source: "pubmed" }]);
	assert.deepEqual(result.details, {
		count: 1,
		papers: [{ pmid: "12345", title: "PubMed record", source: "pubmed" }],
	});

	globalThis.fetch = originalFetch;
});

test("fetch_fulltext returns a structured error instead of throwing when identifiers are missing", async () => {
	const tool = createFetchFulltextTool();
	const result = await tool.execute("tool-call", {}, undefined, undefined);

	assert.equal(result.isError, true);
	assert.deepEqual(result.content, [{ type: "text", text: "Provide at least one of `pmid` or `doi`." }]);
	assert.deepEqual(result.details, {});
});

test.after(() => {
	globalThis.fetch = originalFetch;
});
