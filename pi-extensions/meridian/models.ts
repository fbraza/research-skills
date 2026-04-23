const DEFAULT_MODEL_INPUT: ("text" | "image")[] = ["text", "image"];

const SONNET_COST = {
  input: 3,
  output: 15,
  cacheRead: 0.3,
  cacheWrite: 3.75,
} as const;

const OPUS_COST = {
  input: 15,
  output: 75,
  cacheRead: 1.5,
  cacheWrite: 18.75,
} as const;

const HAIKU_COST = {
  input: 0.8,
  output: 4,
  cacheRead: 0.08,
  cacheWrite: 1,
} as const;

const HAIKU_CONTEXT_WINDOW = 200_000;
const SONNET_CONTEXT_WINDOW = 200_000;
const OPUS_CONTEXT_WINDOW = 1_000_000;

/**
 * These entries intentionally match Meridian's practical routing defaults:
 * - Haiku 4.5 stays on the standard 200k context window.
 * - Sonnet 4.6 advertises 200k because Meridian defaults sonnet to the
 *   non-1M tier unless the user explicitly enables sonnet[1m].
 * - Opus 4.7 advertises 1M because Meridian routes opus to the 1M tier on
 *   Claude Max by default.
 */
export const MERIDIAN_MODELS = [
  {
    id: "claude-haiku-4-5",
    name: "Claude Haiku 4.5 (Meridian)",
    reasoning: true,
    input: DEFAULT_MODEL_INPUT,
    cost: HAIKU_COST,
    contextWindow: HAIKU_CONTEXT_WINDOW,
    maxTokens: 8192,
  },
  {
    id: "claude-sonnet-4-6",
    name: "Claude Sonnet 4.6 (Meridian)",
    reasoning: true,
    input: DEFAULT_MODEL_INPUT,
    cost: SONNET_COST,
    contextWindow: SONNET_CONTEXT_WINDOW,
    maxTokens: 64000,
  },
  {
    id: "claude-opus-4-7",
    name: "Claude Opus 4.7 (Meridian)",
    reasoning: true,
    input: DEFAULT_MODEL_INPUT,
    cost: OPUS_COST,
    contextWindow: OPUS_CONTEXT_WINDOW,
    maxTokens: 32000,
  },
] as const;
