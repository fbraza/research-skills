import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Type } from "@sinclair/typebox";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const PUBMED_SEARCH_PARAMS = Type.Object({
	query: Type.String({ description: "PubMed query string (supports field tags like [tiab], [mh], [pt])" }),
	max_results: Type.Optional(Type.Number({ description: "Maximum results to return (default 20, max 200)" })),
	date_from: Type.Optional(Type.String({ description: "Start date as YYYY/MM/DD" })),
	date_to: Type.Optional(Type.String({ description: "End date as YYYY/MM/DD" })),
	publication_types: Type.Optional(Type.Array(Type.String({ description: "PubMed publication type" }))),
	fetch_abstracts: Type.Optional(Type.Boolean({ description: "Whether to fetch abstracts (default true)" })),
	sort: Type.Optional(Type.Union([
		Type.Literal("relevance"),
		Type.Literal("pub_date"),
		Type.Literal("first_author"),
	])),
	api_key: Type.Optional(Type.String({ description: "Environment variable name containing an NCBI API key" })),
});

const PREPRINT_SEARCH_PARAMS = Type.Object({
	query: Type.String({ description: "Keyword query used for client-side filtering" }),
	date_from: Type.Optional(Type.String({ description: "Start date as YYYY-MM-DD" })),
	date_to: Type.Optional(Type.String({ description: "End date as YYYY-MM-DD" })),
	server: Type.Optional(Type.Union([Type.Literal("biorxiv"), Type.Literal("medrxiv")], { description: "Preprint server" })),
	category: Type.Optional(Type.String({ description: "Optional category filter" })),
	max_results: Type.Optional(Type.Number({ description: "Maximum results to return (default 30)" })),
});

const SEMANTIC_SCHOLAR_PARAMS = Type.Object({
	query: Type.String({ description: "Search query" }),
	max_results: Type.Optional(Type.Number({ description: "Maximum results to return (default 20, max 100)" })),
	year_from: Type.Optional(Type.Number({ description: "Minimum publication year" })),
	year_to: Type.Optional(Type.Number({ description: "Maximum publication year" })),
	fields_of_study: Type.Optional(Type.Array(Type.String({ description: "Field of study" }))),
	min_citation_count: Type.Optional(Type.Number({ description: "Minimum citation count" })),
	open_access_only: Type.Optional(Type.Boolean({ description: "Only keep open access papers" })),
});

const FETCH_FULLTEXT_PARAMS = Type.Object({
	pmid: Type.Optional(Type.String({ description: "PubMed ID" })),
	doi: Type.Optional(Type.String({ description: "Digital Object Identifier" })),
	output_dir: Type.Optional(Type.String({ description: "Directory where the PDF should be saved" })),
});

type PaperRecord = {
	pmid?: string;
	doi?: string;
	s2_id?: string;
	title: string;
	abstract?: string;
	authors?: string[];
	journal?: string;
	year?: number;
	publication_types?: string[];
	mesh_terms?: string[];
	citation_count?: number;
	tldr?: string;
	open_access_pdf?: string;
	external_ids?: Record<string, string>;
	source?: string;
	is_preprint?: boolean;
	date?: string;
	category?: string;
	version?: string;
	license?: string;
	pdf_url?: string;
};

const USER_AGENT = "research-skills-literature-tools/0.1 (+https://github.com/fbraza/research-skills)";
const SCIHUB_MIRRORS = ["https://sci-hub.st", "https://sci-hub.ru", "https://sci-hub.se"];
const PDF_PATTERNS = [
	/<meta[^>]+name=["']citation_pdf_url["'][^>]+content=["']([^"']+)["']/gi,
	/<meta[^>]+property=["']og:pdf["'][^>]+content=["']([^"']+)["']/gi,
	/<meta[^>]+name=["']dc\.identifier["'][^>]+content=["']([^"']*\.pdf[^"']*)["']/gi,
	/<(?:iframe|embed|object)[^>]+(?:src|data)=["']([^"']+)["']/gi,
	/<a[^>]+data-track-action=["'][^"']*pdf[^"']*["'][^>]+href=["']([^"']+)["']/gi,
	/<a[^>]+aria-label=["'][^"']*pdf[^"']*["'][^>]+href=["']([^"']+)["']/gi,
	/["']((?:https?:)?\/\/[^"']+?\.pdf(?:\?[^"']*)?)["']/gi,
	/["']((?:https?:)?\/\/[^"']+?\/pdf(?:\/|\?|$)[^"']*)["']/gi,
	/<a[^>]+href=["']([^"']+\.pdf(?:\?[^"']*)?)["']/gi,
];

const OA_LINK_PATTERNS = [
	/<a[^>]+href=["']([^"']+)["'][^>]*>[^<]*(?:download\s+pdf|pdf|full\s+text|view\s+pdf)[^<]*<\/a>/gi,
	/<a[^>]+class=["'][^"']*(?:pdf|download|article-pdf)[^"']*["'][^>]+href=["']([^"']+)["']/gi,
	/<link[^>]+type=["']application\/pdf["'][^>]+href=["']([^"']+)["']/gi,
];

const KNOWN_PDF_QUERY_FLAGS = ["pdf=1", "download=true", "download=1", "downloadpdf=true", "is_pdf=true"];

function unique<T>(items: T[]): T[] {
	return [...new Set(items.filter((item) => item !== undefined && item !== null && item !== ""))];
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
	return new Promise((resolve, reject) => {
		const timeout = setTimeout(resolve, ms);
		if (!signal) return;
		const onAbort = () => {
			clearTimeout(timeout);
			reject(new Error("Request aborted"));
		};
		if (signal.aborted) onAbort();
		signal.addEventListener("abort", onAbort, { once: true });
	});
}

function htmlDecode(text: string): string {
	return text
		.replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1")
		.replace(/&lt;/g, "<")
		.replace(/&gt;/g, ">")
		.replace(/&amp;/g, "&")
		.replace(/&quot;/g, '"')
		.replace(/&#39;/g, "'")
		.replace(/<[^>]+>/g, " ")
		.replace(/\s+/g, " ")
		.trim();
}

function normalizeDoi(raw?: string): string | undefined {
	if (!raw) return undefined;
	return raw
		.trim()
		.replace(/^doi:\s*/i, "")
		.replace(/^https?:\/\/(?:dx\.)?doi\.org\//i, "")
		.trim() || undefined;
}

function xmlDecode(text: string): string {
	return htmlDecode(text);
}

function pickAll(regex: RegExp, text: string): string[] {
	const matches: string[] = [];
	for (const match of text.matchAll(regex)) {
		if (match[1]) matches.push(xmlDecode(match[1]));
	}
	return matches;
}

function pickOne(regex: RegExp, text: string): string | undefined {
	const match = regex.exec(text);
	return match?.[1] ? xmlDecode(match[1]) : undefined;
}

function normalizePubmedQuery(query: string, publicationTypes?: string[], dateFrom?: string, dateTo?: string): string {
	const fragments = [query.trim()].filter(Boolean);
	if (publicationTypes && publicationTypes.length > 0) {
		fragments.push(`(${publicationTypes.map((item) => `\"${item}\"[Publication Type]`).join(" OR ")})`);
	}
	if (dateFrom || dateTo) {
		const start = dateFrom ?? "1000/01/01";
		const end = dateTo ?? "3000/12/31";
		fragments.push(`(${start}:${end}[Date - Publication])`);
	}
	return fragments.join(" AND ");
}

async function fetchText(url: string, signal?: AbortSignal, headers?: Record<string, string>): Promise<string> {
	const response = await fetch(url, {
		headers: {
			"user-agent": USER_AGENT,
			accept: "application/json, text/xml, application/xml, text/html;q=0.9, */*;q=0.8",
			...headers,
		},
		signal,
		redirect: "follow",
	});
	if (!response.ok) throw new Error(`${response.status} ${response.statusText} for ${url}`);
	return await response.text();
}

async function fetchJson<T>(url: string, signal?: AbortSignal, headers?: Record<string, string>): Promise<T> {
	const text = await fetchText(url, signal, headers);
	return JSON.parse(text) as T;
}

function parsePubmedArticle(articleXml: string): PaperRecord {
	const pmid = pickOne(/<PMID[^>]*>(.*?)<\/PMID>/i, articleXml);
	const title = pickOne(/<ArticleTitle>([\s\S]*?)<\/ArticleTitle>/i, articleXml) ?? "Untitled";
	const abstractSections = pickAll(/<AbstractText[^>]*>([\s\S]*?)<\/AbstractText>/gi, articleXml);
	const abstract = abstractSections.join(" ").trim() || undefined;
	const journal = pickOne(/<Title>([\s\S]*?)<\/Title>/i, articleXml) ?? pickOne(/<ISOAbbreviation>(.*?)<\/ISOAbbreviation>/i, articleXml);
	const yearText =
		pickOne(/<PubDate>[\s\S]*?<Year>(\d{4})<\/Year>/i, articleXml) ??
		pickOne(/<ArticleDate[^>]*>[\s\S]*?<Year>(\d{4})<\/Year>/i, articleXml) ??
		pickOne(/<PubMedPubDate[^>]*PubStatus=\"pubmed\">[\s\S]*?<Year>(\d{4})<\/Year>/i, articleXml);
	const doi =
		normalizeDoi(pickOne(/<ELocationID[^>]*EIdType=\"doi\"[^>]*>(.*?)<\/ELocationID>/i, articleXml)) ??
		normalizeDoi(pickOne(/<ArticleId[^>]*IdType=\"doi\"[^>]*>(.*?)<\/ArticleId>/i, articleXml));
	const publicationTypes = unique(pickAll(/<PublicationType[^>]*>([\s\S]*?)<\/PublicationType>/gi, articleXml));
	const meshTerms = unique(pickAll(/<DescriptorName[^>]*>([\s\S]*?)<\/DescriptorName>/gi, articleXml));
	const authors = unique(Array.from(articleXml.matchAll(/<Author[\s\S]*?<LastName>(.*?)<\/LastName>[\s\S]*?(?:<ForeName>(.*?)<\/ForeName>|<Initials>(.*?)<\/Initials>)/gi)).map((match) => {
		const last = xmlDecode(match[1] ?? "");
		const fore = xmlDecode(match[2] ?? match[3] ?? "");
		return [fore, last].filter(Boolean).join(" ").trim();
	}));
	const collectiveAuthors = pickAll(/<CollectiveName>([\s\S]*?)<\/CollectiveName>/gi, articleXml);
	return {
		pmid,
		doi,
		title,
		abstract,
		authors: unique([...authors, ...collectiveAuthors]),
		journal,
		year: yearText ? Number(yearText) : undefined,
		publication_types: publicationTypes,
		mesh_terms: meshTerms,
		source: "pubmed",
	};
}

function parsePubmedArticles(xml: string): PaperRecord[] {
	const chunks = xml.match(/<PubmedArticle>[\s\S]*?<\/PubmedArticle>/gi) ?? [];
	return chunks.map(parsePubmedArticle);
}

async function lookupPubmedIdentifiers(pmid: string, signal?: AbortSignal): Promise<{ doi?: string; title?: string }> {
	const url = new URL("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi");
	url.searchParams.set("db", "pubmed");
	url.searchParams.set("id", pmid);
	url.searchParams.set("retmode", "xml");
	const xml = await fetchText(url.toString(), signal);
	const article = parsePubmedArticles(xml)[0];
	return { doi: article?.doi, title: article?.title };
}

async function tryPubmedCentral(pmid: string, signal?: AbortSignal): Promise<{ source: string; pdf_url?: string; access_note: string; is_preprint: boolean }> {
	const url = new URL("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi");
	url.searchParams.set("dbfrom", "pubmed");
	url.searchParams.set("db", "pmc");
	url.searchParams.set("id", pmid);
	const xml = await fetchText(url.toString(), signal);
	const linkSet = /<LinkSetDb>[\s\S]*?<LinkName>pubmed_pmc<\/LinkName>[\s\S]*?<Id>(\d+)<\/Id>[\s\S]*?<\/LinkSetDb>/i.exec(xml);
	if (!linkSet?.[1]) {
		return { source: "not_found", access_note: "No PMC full text linked from PubMed", is_preprint: false };
	}
	const pmcId = `PMC${linkSet[1]}`;
	const articleUrl = `https://pmc.ncbi.nlm.nih.gov/articles/${pmcId}/`;
	const articleHtml = await fetchText(articleUrl, signal);
	const pdfMatch = articleHtml.match(/href=["']([^"']+\.pdf(?:\?pdf=render)?)["']/i);
	const pdfUrl = pdfMatch?.[1] ? new URL(pdfMatch[1], articleUrl).toString() : `https://pmc.ncbi.nlm.nih.gov/articles/${pmcId}/pdf`;
	return { source: "pmc", pdf_url: pdfUrl, access_note: `Open access via PubMed Central (${pmcId})`, is_preprint: false };
}

function extractPdfCandidates(html: string, pageUrl: string): string[] {
	const urls: string[] = [];
	for (const pattern of PDF_PATTERNS) {
		for (const match of html.matchAll(pattern)) {
			const raw = match[1];
			if (!raw) continue;
			try {
				urls.push(new URL(raw.startsWith("//") ? `https:${raw}` : raw, pageUrl).toString());
			} catch {
				// ignore invalid candidate
			}
		}
	}
	return unique(urls);
}

function extractOpenAccessLinks(html: string, pageUrl: string): string[] {
	const urls: string[] = [];
	for (const pattern of OA_LINK_PATTERNS) {
		for (const match of html.matchAll(pattern)) {
			const raw = match[1];
			if (!raw) continue;
			try {
				urls.push(new URL(raw.startsWith("//") ? `https:${raw}` : raw, pageUrl).toString());
			} catch {
				// ignore invalid candidate
			}
		}
	}
	return unique(urls);
}

function candidatePdfVariants(url: string): string[] {
	const variants = [url];
	try {
		const parsed = new URL(url);
		if (!parsed.pathname.toLowerCase().endsWith(".pdf")) {
			variants.push(new URL(`${parsed.pathname}.pdf${parsed.search}`, `${parsed.origin}`).toString());
		}
		for (const flag of KNOWN_PDF_QUERY_FLAGS) {
			const withFlag = new URL(parsed.toString());
			const [key, value] = flag.split("=");
			withFlag.searchParams.set(key, value);
			variants.push(withFlag.toString());
		}
		if (/article|full|abstract/i.test(parsed.pathname)) {
			variants.push(new URL(parsed.pathname.replace(/(article|full|abstract)/i, "pdf"), parsed.origin).toString());
		}
	} catch {
		// ignore malformed URLs
	}
	return unique(variants);
}

function publisherSpecificPdfVariants(url: string): string[] {
	const variants: string[] = [];
	try {
		const parsed = new URL(url);
		const host = parsed.hostname.toLowerCase();
		const pathname = parsed.pathname;

		if (/nature\.com$/.test(host)) {
			variants.push(new URL(pathname.replace(/$/, ".pdf"), parsed.origin).toString());
			variants.push(new URL(`${pathname}.pdf`, parsed.origin).toString());
		}

		if (/cell\.com$/.test(host) || /sciencedirect\.com$/.test(host)) {
			variants.push(new URL(pathname.replace(/\/fulltext$/i, "/pdf"), parsed.origin).toString());
			variants.push(new URL(pathname.replace(/\/fulltext$/i, "/pdf?download=true"), parsed.origin).toString());
			variants.push(new URL(pathname.replace(/\/article\//i, "/article/am/pii/"), parsed.origin).toString());
		}

		if (/wiley\.com$/.test(host) || /onlinelibrary\.wiley\.com$/.test(host)) {
			variants.push(new URL(pathname.replace(/\/full$/i, "/pdf"), parsed.origin).toString());
			variants.push(new URL(pathname.replace(/\/full$/i, "/pdfdirect"), parsed.origin).toString());
			variants.push(new URL(pathname.replace(/\/doi\//i, "/doi/pdf/"), parsed.origin).toString());
			variants.push(new URL(pathname.replace(/\/doi\//i, "/doi/epdf/"), parsed.origin).toString());
		}

		if (/tandfonline\.com$/.test(host)) {
			variants.push(new URL(pathname.replace(/\/full$/i, "/pdf"), parsed.origin).toString());
			variants.push(new URL(pathname.replace(/\/full$/i, "/pdf?download=true"), parsed.origin).toString());
		}
	} catch {
		// ignore malformed URLs
	}
	return unique(variants);
}

async function resolvePublisherPdfFromPage(pageUrl: string, html: string, signal?: AbortSignal): Promise<string | undefined> {
	const directCandidates = extractPdfCandidates(html, pageUrl);
	for (const candidate of directCandidates.flatMap((value) => [...candidatePdfVariants(value), ...publisherSpecificPdfVariants(value)])) {
		if (await headOrGet(candidate, signal)) return candidate;
	}

	for (const candidate of [...candidatePdfVariants(pageUrl), ...publisherSpecificPdfVariants(pageUrl)]) {
		if (await headOrGet(candidate, signal)) return candidate;
	}

	for (const landingPage of extractOpenAccessLinks(html, pageUrl)) {
		for (const candidate of [...candidatePdfVariants(landingPage), ...publisherSpecificPdfVariants(landingPage)]) {
			if (await headOrGet(candidate, signal)) return candidate;
		}
		try {
			const nestedHtml = await fetchText(landingPage, signal, { accept: "text/html,application/xhtml+xml,*/*" });
			const nestedCandidates = extractPdfCandidates(nestedHtml, landingPage);
			for (const candidate of nestedCandidates.flatMap((value) => [...candidatePdfVariants(value), ...publisherSpecificPdfVariants(value)])) {
				if (await headOrGet(candidate, signal)) return candidate;
			}
		} catch {
			// ignore nested landing page failures
		}
	}

	return undefined;
}

async function headOrGet(url: string, signal?: AbortSignal): Promise<boolean> {
	try {
		const response = await fetch(url, {
			method: "HEAD",
			signal,
			headers: { "user-agent": USER_AGENT, accept: "application/pdf,*/*" },
			redirect: "follow",
		});
		const contentType = response.headers.get("content-type") ?? "";
		if (response.ok && (contentType.includes("pdf") || url.toLowerCase().includes(".pdf"))) return true;
	} catch {
		// fall through
	}
	try {
		const response = await fetch(url, {
			method: "GET",
			signal,
			headers: { "user-agent": USER_AGENT, accept: "application/pdf,*/*" },
			redirect: "follow",
		});
		const contentType = response.headers.get("content-type") ?? "";
		return response.ok && (contentType.includes("pdf") || url.toLowerCase().includes(".pdf"));
	} catch {
		return false;
	}
}

async function tryPublisherOpenAccess(doi: string, signal?: AbortSignal): Promise<{ source: string; pdf_url?: string; access_note: string; is_preprint: boolean }> {
	const doiUrl = `https://doi.org/${encodeURIComponent(doi)}`;
	const response = await fetch(doiUrl, {
		method: "GET",
		signal,
		headers: { "user-agent": USER_AGENT, accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" },
		redirect: "follow",
	});
	if (!response.ok) {
		return { source: "not_found", access_note: `DOI landing page unavailable (${response.status})`, is_preprint: false };
	}
	const html = await response.text();
	const finalUrl = response.url || doiUrl;
	const pdfUrl = await resolvePublisherPdfFromPage(finalUrl, html, signal);
	if (pdfUrl) {
		return {
			source: "publisher_oa",
			pdf_url: pdfUrl,
			access_note: "PDF found on publisher/open-access landing page or linked OA page",
			is_preprint: false,
		};
	}
	return { source: "not_found", access_note: "No direct PDF found on publisher/open-access landing page", is_preprint: false };
}

async function trySemanticScholarOpenAccess(doi: string, signal?: AbortSignal): Promise<{ source: string; pdf_url?: string; access_note: string; is_preprint: boolean }> {
	const url = new URL("https://api.semanticscholar.org/graph/v1/paper/search");
	url.searchParams.set("query", doi);
	url.searchParams.set("limit", "5");
	url.searchParams.set("fields", "title,openAccessPdf,externalIds,isOpenAccess");
	const data = await fetchJson<{ data?: Array<{ openAccessPdf?: { url?: string }; externalIds?: Record<string, string> }> }>(url.toString(), signal);
	const match = (data.data ?? []).find((item) => normalizeDoi(item.externalIds?.DOI) === normalizeDoi(doi) && item.openAccessPdf?.url);
	const pdfUrl = match?.openAccessPdf?.url;
	if (!pdfUrl || !/biorxiv|medrxiv/i.test(pdfUrl)) {
		return { source: "not_found", access_note: "No bioRxiv/medRxiv PDF found via Semantic Scholar", is_preprint: true };
	}
	return {
		source: "biorxiv",
		pdf_url: pdfUrl,
		access_note: "bioRxiv/medRxiv PDF found via Semantic Scholar openAccessPdf",
		is_preprint: true,
	};
}

async function trySciHub(doi: string, signal?: AbortSignal): Promise<{ source: string; pdf_url?: string; access_note: string; is_preprint: boolean }> {
	for (const mirror of SCIHUB_MIRRORS) {
		try {
			const pageUrl = `${mirror}/${encodeURIComponent(doi)}`;
			const html = await fetchText(pageUrl, signal, { accept: "text/html,*/*" });
			const candidates = extractPdfCandidates(html, pageUrl);
			for (const candidate of candidates) {
				if (await headOrGet(candidate, signal)) {
					return { source: "scihub", pdf_url: candidate, access_note: `PDF resolved through Sci-Hub mirror ${mirror}`, is_preprint: false };
				}
			}
		} catch {
			// try next mirror
		}
	}
	return { source: "not_found", access_note: "Sci-Hub did not yield a PDF", is_preprint: false };
}

function sanitizeFilename(value: string): string {
	return value.replace(/[^a-z0-9._-]+/gi, "_").replace(/^_+|_+$/g, "") || "paper";
}

async function savePdf(pdfUrl: string, outputDir: string, preferredId: string, signal?: AbortSignal): Promise<string> {
	await mkdir(outputDir, { recursive: true });
	const response = await fetch(pdfUrl, {
		method: "GET",
		signal,
		headers: { "user-agent": USER_AGENT, accept: "application/pdf,*/*" },
		redirect: "follow",
	});
	if (!response.ok) throw new Error(`Failed to download PDF (${response.status})`);
	const bytes = Buffer.from(await response.arrayBuffer());
	const filePath = path.resolve(outputDir, `${sanitizeFilename(preferredId)}.pdf`);
	await writeFile(filePath, bytes);
	return filePath;
}

function formatPaperText(papers: PaperRecord[]): string {
	return JSON.stringify(papers, null, 2);
}

export default function literatureToolsExtension(pi: ExtensionAPI) {
	pi.registerTool({
		name: "pubmed_search",
		label: "PubMed Search",
		description: "Search PubMed using typed parameters and return metadata with abstracts when available.",
		parameters: PUBMED_SEARCH_PARAMS,
		async execute(_toolCallId, params, signal, onUpdate) {
			const maxResults = Math.min(200, Math.max(1, Math.floor(params.max_results ?? 20)));
			const query = normalizePubmedQuery(params.query, params.publication_types, params.date_from, params.date_to);
			const apiKeyValue = params.api_key ? process.env[params.api_key] : undefined;
			const esearchUrl = new URL("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi");
			esearchUrl.searchParams.set("db", "pubmed");
			esearchUrl.searchParams.set("retmode", "json");
			esearchUrl.searchParams.set("retmax", String(maxResults));
			esearchUrl.searchParams.set("sort", params.sort ?? "relevance");
			esearchUrl.searchParams.set("term", query);
			if (apiKeyValue) esearchUrl.searchParams.set("api_key", apiKeyValue);
			onUpdate?.(`Searching PubMed for: ${params.query}`);
			const esearch = await fetchJson<{ esearchresult?: { idlist?: string[]; count?: string } }>(esearchUrl.toString(), signal);
			const ids = esearch.esearchresult?.idlist ?? [];
			if (ids.length === 0) {
				return { content: [{ type: "text", text: "[]" }], details: { count: 0, papers: [] } };
			}
			if (params.fetch_abstracts === false) {
				const papers = ids.map((pmid) => ({ pmid, title: "PubMed record", source: "pubmed" }));
				return { content: [{ type: "text", text: formatPaperText(papers) }], details: { count: papers.length, papers } };
			}
			const rateLimitMs = apiKeyValue ? 120 : 350;
			const batchSize = 50;
			const papers: PaperRecord[] = [];
			for (let start = 0; start < ids.length; start += batchSize) {
				const batch = ids.slice(start, start + batchSize);
				onUpdate?.(`Searching PubMed... found ${ids.length} PMIDs, fetching abstracts ${start + 1}-${Math.min(start + batch.length, ids.length)}...`);
				const efetchUrl = new URL("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi");
				efetchUrl.searchParams.set("db", "pubmed");
				efetchUrl.searchParams.set("retmode", "xml");
				efetchUrl.searchParams.set("id", batch.join(","));
				if (apiKeyValue) efetchUrl.searchParams.set("api_key", apiKeyValue);
				const xml = await fetchText(efetchUrl.toString(), signal);
				papers.push(...parsePubmedArticles(xml));
				if (start + batchSize < ids.length) await sleep(rateLimitMs, signal);
			}
			return {
				content: [{ type: "text", text: formatPaperText(papers) }],
				details: { count: papers.length, papers, query, total: Number(esearch.esearchresult?.count ?? papers.length) },
			};
		},
	});

	pi.registerTool({
		name: "preprint_search",
		label: "Preprint Search",
		description: "Search bioRxiv or medRxiv with pagination and client-side keyword filtering.",
		parameters: PREPRINT_SEARCH_PARAMS,
		async execute(_toolCallId, params, signal, onUpdate) {
			const server = params.server ?? "biorxiv";
			const maxResults = Math.max(1, Math.floor(params.max_results ?? 30));
			const startDate = params.date_from ?? "2000-01-01";
			const endDate = params.date_to ?? new Date().toISOString().slice(0, 10);
			const filtered: PaperRecord[] = [];
			let cursor = 0;
			let page = 1;
			const queryNeedles = params.query.toLowerCase().split(/\s+/).filter(Boolean);
			while (filtered.length < maxResults) {
				onUpdate?.(`Fetching ${server} page ${page}...`);
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
			return {
				content: [{ type: "text", text: formatPaperText(filtered) }],
				details: { count: filtered.length, preprints: filtered, server },
			};
		},
	});

	pi.registerTool({
		name: "semantic_scholar_search",
		label: "Semantic Scholar Search",
		description: "Search Semantic Scholar for relevance-ranked papers, citation counts, and open-access metadata.",
		parameters: SEMANTIC_SCHOLAR_PARAMS,
		async execute(_toolCallId, params, signal, onUpdate) {
			const maxResults = Math.min(100, Math.max(1, Math.floor(params.max_results ?? 20)));
			const url = new URL("https://api.semanticscholar.org/graph/v1/paper/search");
			url.searchParams.set("query", params.query);
			url.searchParams.set("limit", String(maxResults));
			url.searchParams.set(
				"fields",
				[
					"paperId",
					"title",
					"abstract",
					"year",
					"citationCount",
					"tldr",
					"externalIds",
					"openAccessPdf",
					"fieldsOfStudy",
					"isOpenAccess",
					"authors",
				].join(","),
			);
			if (params.year_from) url.searchParams.set("year", `${params.year_from}-${params.year_to ?? ""}`);
			onUpdate?.(`Searching Semantic Scholar for: ${params.query}`);
			const response = await fetchJson<{ data?: any[] }>(url.toString(), signal, process.env.SEMANTIC_SCHOLAR_API_KEY ? { "x-api-key": process.env.SEMANTIC_SCHOLAR_API_KEY } : undefined);
			let papers: PaperRecord[] = (response.data ?? []).map((item) => ({
				s2_id: item.paperId,
				title: item.title ?? "Untitled",
				abstract: item.abstract ?? undefined,
				year: item.year ?? undefined,
				citation_count: item.citationCount ?? undefined,
				tldr: item.tldr?.text ?? undefined,
				open_access_pdf: item.openAccessPdf?.url ?? undefined,
				external_ids: item.externalIds ?? undefined,
				doi: normalizeDoi(item.externalIds?.DOI),
				pmid: item.externalIds?.PubMed ?? item.externalIds?.PMID,
				authors: Array.isArray(item.authors) ? item.authors.map((author: any) => author.name).filter(Boolean) : [],
				source: "semantic_scholar",
			}));
			if (params.fields_of_study?.length) {
				const wanted = new Set(params.fields_of_study.map((item) => item.toLowerCase()));
				papers = papers.filter((paper, index) => {
					const fields = (response.data?.[index]?.fieldsOfStudy ?? []).map((item: string) => item.toLowerCase());
					return fields.some((item: string) => wanted.has(item));
				});
			}
			if (params.min_citation_count !== undefined) papers = papers.filter((paper) => (paper.citation_count ?? 0) >= params.min_citation_count!);
			if (params.open_access_only) papers = papers.filter((paper) => !!paper.open_access_pdf);
			if (params.year_from !== undefined) papers = papers.filter((paper) => (paper.year ?? 0) >= params.year_from!);
			if (params.year_to !== undefined) papers = papers.filter((paper) => (paper.year ?? 9999) <= params.year_to!);
			return { content: [{ type: "text", text: formatPaperText(papers) }], details: { count: papers.length, papers } };
		},
	});

	pi.registerTool({
		name: "fetch_fulltext",
		label: "Fetch Full Text",
		description: "Retrieve a paper PDF using PMC, publisher OA, preprint OA, then Sci-Hub fallback.",
		parameters: FETCH_FULLTEXT_PARAMS,
		async execute(_toolCallId, params, signal, onUpdate) {
			if (!params.pmid && !params.doi) {
				throw new Error("Provide at least one of `pmid` or `doi`.");
			}
			let pmid = params.pmid?.trim() || undefined;
			let doi = normalizeDoi(params.doi);
			if (!doi && pmid) {
				onUpdate?.(`Resolving DOI from PubMed for PMID ${pmid}...`);
				const identifiers = await lookupPubmedIdentifiers(pmid, signal);
				doi = identifiers.doi;
			}

			const attempts: Array<{ source: string; pdf_url?: string; access_note: string; is_preprint: boolean }> = [];

			if (pmid) {
				onUpdate?.(`Checking PubMed Central for PMID ${pmid}...`);
				const pmc = await tryPubmedCentral(pmid, signal);
				attempts.push(pmc);
				if (pmc.source !== "not_found" && pmc.pdf_url) {
					const result: any = { ...pmc };
					if (params.output_dir) result.pdf_path = await savePdf(pmc.pdf_url, params.output_dir, pmid ?? doi ?? "paper", signal);
					return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }], details: result };
				}
			}

			if (doi) {
				onUpdate?.(`Checking publisher open-access routes for DOI ${doi}...`);
				const publisher = await tryPublisherOpenAccess(doi, signal);
				attempts.push(publisher);
				if (publisher.source !== "not_found" && publisher.pdf_url) {
					const result: any = { ...publisher };
					if (params.output_dir) result.pdf_path = await savePdf(publisher.pdf_url, params.output_dir, doi, signal);
					return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }], details: result };
				}

				onUpdate?.(`Checking Semantic Scholar open-access PDF metadata for DOI ${doi}...`);
				const preprint = await trySemanticScholarOpenAccess(doi, signal);
				attempts.push(preprint);
				if (preprint.source !== "not_found" && preprint.pdf_url) {
					const result: any = { ...preprint };
					if (params.output_dir) result.pdf_path = await savePdf(preprint.pdf_url, params.output_dir, doi, signal);
					return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }], details: result };
				}

				onUpdate?.(`Trying Sci-Hub fallback for DOI ${doi}...`);
				const scihub = await trySciHub(doi, signal);
				attempts.push(scihub);
				if (scihub.source !== "not_found" && scihub.pdf_url) {
					const result: any = { ...scihub };
					if (params.output_dir) result.pdf_path = await savePdf(scihub.pdf_url, params.output_dir, doi, signal);
					return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }], details: result };
				}
			}

			const result = {
				source: "not_found",
				is_preprint: false,
				access_note: "No full-text PDF found via PMC, publisher OA, Semantic Scholar OA, or Sci-Hub",
				attempts,
			};
			return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }], details: result };
		},
	});
}
