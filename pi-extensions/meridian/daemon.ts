import { spawn } from "node:child_process";

import {
  HEALTH_TIMEOUT_MS,
  START_RETRY_COOLDOWN_MS,
  STARTUP_POLL_MS,
  STARTUP_WAIT_MS,
} from "./config.js";
import { isReachable } from "./health.js";

let startInFlight: Promise<boolean> | null = null;
let lastStartFailedAt = 0;

/**
 * Start Meridian as a detached background process.
 * Returns true if Meridian became reachable after starting.
 * Dedupes concurrent calls and avoids rapid retry loops.
 */
export async function startMeridianDaemon(
  baseUrl: string,
  port: number
): Promise<boolean> {
  if (startInFlight) return startInFlight;

  if (Date.now() - lastStartFailedAt < START_RETRY_COOLDOWN_MS) {
    return false;
  }

  startInFlight = (async () => {
    let spawnError: string | null = null;

    try {
      await new Promise<void>((resolveSpawn) => {
        try {
          const child = spawn("meridian", ["--port", String(port)], {
            detached: true,
            stdio: "ignore",
            env: process.env,
          });

          child.unref();
          child.on("error", (error: NodeJS.ErrnoException) => {
            spawnError = error.code === "ENOENT"
              ? "meridian not found on PATH. Install: npm install -g @rynfar/meridian"
              : `Failed to start: ${error.message}`;
            resolveSpawn();
          });

          setTimeout(resolveSpawn, 200);
        } catch (error) {
          spawnError = `Failed to start: ${error instanceof Error ? error.message : String(error)}`;
          resolveSpawn();
        }
      });

      if (spawnError) {
        lastStartFailedAt = Date.now();
        return false;
      }

      const deadline = Date.now() + STARTUP_WAIT_MS;
      while (Date.now() < deadline) {
        const remaining = deadline - Date.now();
        const timeoutMs = Math.min(HEALTH_TIMEOUT_MS, remaining);
        if ((await isReachable(baseUrl, timeoutMs)).ok) {
          return true;
        }
        await new Promise((resolve) => setTimeout(resolve, STARTUP_POLL_MS));
      }

      lastStartFailedAt = Date.now();
      return false;
    } finally {
      startInFlight = null;
    }
  })();

  return startInFlight;
}
