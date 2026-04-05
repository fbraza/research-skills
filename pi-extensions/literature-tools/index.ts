import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { registerFetchFulltextTool } from "./fulltext.ts";
import { registerPreprintSearchTool } from "./preprints.ts";
import { registerPubmedSearchTool } from "./pubmed.ts";
import { registerSemanticScholarSearchTool } from "./semantic-scholar.ts";

export default function literatureToolsExtension(pi: ExtensionAPI) {
	registerPubmedSearchTool(pi);
	registerPreprintSearchTool(pi);
	registerSemanticScholarSearchTool(pi);
	registerFetchFulltextTool(pi);
}
