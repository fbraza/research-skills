import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { registerFetchFulltextTool } from "./fulltext.ts";
import { registerPubmedSearchTool } from "./pubmed.ts";
import { registerSemanticScholarSearchTool } from "./semantic-scholar.ts";

export default function literatureToolsExtension(pi: ExtensionAPI) {
	registerPubmedSearchTool(pi);
	registerSemanticScholarSearchTool(pi);
	registerFetchFulltextTool(pi);
}
