import { HEALTH_TIMEOUT_MS } from "./config.js";

export interface MeridianHealth {
  status: string;
  auth?: {
    loggedIn: boolean;
    email?: string;
    subscriptionType?: string;
  };
  mode?: string;
  error?: string;
}

function isValidHealth(value: unknown): value is MeridianHealth {
  return (
    typeof value === "object" &&
    value !== null &&
    "status" in value &&
    typeof (value as MeridianHealth).status === "string"
  );
}

export async function fetchHealth(
  baseUrl: string,
  signal?: AbortSignal
): Promise<MeridianHealth> {
  if (signal?.aborted) throw new DOMException("Aborted", "AbortError");

  const controller = new AbortController();
  let timedOut = false;
  const timeout = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, HEALTH_TIMEOUT_MS);

  const onExternalAbort = () => controller.abort();
  if (signal) {
    signal.addEventListener("abort", onExternalAbort, { once: true });
  }

  try {
    const response = await fetch(`${baseUrl}/health`, {
      signal: controller.signal,
    });
    const body = await response.text();

    let health: MeridianHealth;
    try {
      const parsed: unknown = JSON.parse(body);
      health = isValidHealth(parsed)
        ? parsed
        : {
            status: "error",
            error: `Unexpected response: ${body.slice(0, 200)}`,
          };
    } catch {
      health = {
        status: "error",
        error: `HTTP ${response.status}: ${body.slice(0, 200)}`,
      };
    }

    if (!response.ok && !health.error) {
      health.error = `HTTP ${response.status}`;
    }

    return health;
  } catch (error) {
    if (timedOut) {
      throw new Error(
        `Meridian health check timed out after ${HEALTH_TIMEOUT_MS}ms`
      );
    }
    throw error;
  } finally {
    clearTimeout(timeout);
    if (signal) {
      signal.removeEventListener("abort", onExternalAbort);
    }
  }
}

export async function isReachable(
  baseUrl: string,
  timeoutMs = HEALTH_TIMEOUT_MS
): Promise<{ ok: boolean; health?: MeridianHealth }> {
  try {
    const health = await fetchHealth(baseUrl, AbortSignal.timeout(timeoutMs));
    return { ok: true, health };
  } catch {
    return { ok: false };
  }
}
