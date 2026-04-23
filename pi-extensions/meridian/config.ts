export const DEFAULT_BASE_URL = "http://127.0.0.1:3456";
export const DEFAULT_PORT = Number(new URL(DEFAULT_BASE_URL).port) || 3456;

export const HEALTH_TIMEOUT_MS = 3000;
export const STARTUP_WAIT_MS = 6000;
export const STARTUP_POLL_MS = 500;
export const START_RETRY_COOLDOWN_MS = 30_000;

export const MERIDIAN_PROVIDER = "meridian";

export function getBaseUrl(): string {
  return process.env.MERIDIAN_BASE_URL || DEFAULT_BASE_URL;
}

export function getPortFromBaseUrl(baseUrl: string): number {
  try {
    return Number(new URL(baseUrl).port) || DEFAULT_PORT;
  } catch {
    return DEFAULT_PORT;
  }
}
