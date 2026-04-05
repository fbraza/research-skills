import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Type } from "@sinclair/typebox";
import { emitProgress, textResult } from "./tool-output.ts";
import { fetchJson, formatPaperText, normalizeDoi } from "./shared.ts";
import type { PaperRecord } from "./types.ts";

export const PREPRINT_SEARCH_PARAMS = Type.Object({
	query: Type.String({ description: "Keyword query used for client-side filtering" }),
	date_from: Type.Optional(Type.String({ description: "Start date as YYYY-MM-DD" })),
	date_to: Type.Optional(Type.String({ description: "End date as YYYY-MM-DD" })),
	server: Type.Optional(Type.Union([Type.Literal("biorxiv"), Type.Literal("medrxiv")], { description: "Preprint server" })),
	category: Type.Optional(Type.String({ description: "Optional category filter" })),
	max_results: Type.Optional(Type.Number({ description: "Maximum results to return (default 30)" })),
});

export function createPreprintSearchTool() {
	return {
		name: "preprint_search",
		label: "Preprint Search",
		description: "Search bioRxiv or medRxiv with pagination and client-side keyword filtering.",
		parameters: PREPRINT_SEARCH_PARAMS,
		async execute(_toolCallId: string, params: any, signal?: AbortSignal, onUpdate?: (update: any) => void) {
			const server = params.server ?? "biorxiv";
			const maxResults = Math.max(1, Math.floor(params.max_results ?? 30));
			const startDate = params.date_from ?? "2000-01-01";
			const endDate = params.date_to ?? new Date().toISOString().slice(0, 10);
			const filtered: PaperRecord[] = [];
			let cursor = 0;
			let page = 1;
			const queryNeedles = params.query.toLowerCase().split(/\s+/).filter(Boolean);
			while (filtered.length < maxResults) {
				emitProgress(onUpdate, `Fetching ${server} page ${page}...`);
				const url = `https://api.biorxiv.org/details/${server}/${startDate}/${endDate}/${cursor}`;
				const payload = await fetchJson<{ collection?: any[]; messages?: Array<{ total?: string }> }>(url, signal);
				const collection = payload.collection ?? [];
				if (collection.length === 0) break;
				for (const item of collection) {
					const haystack = `${item.title ?? ""} ${item.abstract ?? ""} ${item.authors ?? ""}`.toLowerCase();
					const matchesQuery = queryNeedles.every((needle) => haystack.includes(needle));
					const matchesCategory = !params.category || String(item.category ?? "").toLowerCase() === params.category.toLowerCase();
					if (!matchesQuery || !matchesCategory) continue;
					filtered.push({
						doi: normalizeDoi(item.doi),
						title: item.title ?? "Untitled preprint",
						abstract: item.abstract ?? undefined,
						authors: String(item.authors ?? "").split(/;\s*/).filter(Boolean),
						date: item.date ?? undefined,
						category: item.category ?? undefined,
						version: item.version ?? undefined,
						license: item.license ?? undefined,
						pdf_url: item.jatsxml ? undefined : normalizeDoi(item.doi) ? `https://www.${server}.org/content/${normalizeDoi(item.doi)}v${item.version ?? 1}.full.pdf` : undefined,
						source: server,
						is_preprint: true,
					});
					if (filtered.length >= maxResults) break;
				}
				cursor += collection.length;
				page += 1;
				const total = Number(payload.messages?.[0]?.total ?? 0);
				if (cursor >= total && total > 0) break;
			}
			return textResult(formatPaperText(filtered), { count: filtered.length, preprints: filtered, server });
		},
	};
}

export function registerPreprintSearchTool(pi: ExtensionAPI): void {
	pi.registerTool(createPreprintSearchTool());
}
