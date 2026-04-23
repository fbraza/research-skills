import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

import { getBaseUrl, getPortFromBaseUrl, MERIDIAN_PROVIDER } from "./config.js";
import { startMeridianDaemon } from "./daemon.js";
import { fetchHealth, isReachable, type MeridianHealth } from "./health.js";
import { MERIDIAN_MODELS } from "./models.js";
import { buildMeridianSafeSystemPrompt } from "./prompt.js";
import { checkVersion } from "./version.js";

let versionChecked = false;

function isMeridianProvider(model: { provider?: string } | null | undefined): boolean {
  return model?.provider === MERIDIAN_PROVIDER;
}

function registerMeridianProvider(pi: ExtensionAPI, baseUrl: string): void {
  pi.registerProvider(MERIDIAN_PROVIDER, {
    baseUrl,
    apiKey: "meridian",
    api: "anthropic-messages",
    authHeader: true,
    headers: {
      "x-meridian-agent": "pi",
    },
    models: MERIDIAN_MODELS,
  });
}

function registerProviderHooks(pi: ExtensionAPI): void {
  pi.on("before_provider_request", (event, ctx) => {
    if (!isMeridianProvider(ctx.model)) return;
    if (!event.payload || typeof event.payload !== "object") {
      return event.payload;
    }

    return {
      ...(event.payload as Record<string, unknown>),
      system: buildMeridianSafeSystemPrompt(ctx.getSystemPrompt(), ctx.cwd),
    };
  });

  pi.on("after_provider_response", (event, ctx) => {
    if (!isMeridianProvider(ctx.model)) return;

    if (event.status === 401 || event.status === 403) {
      ctx.ui.notify(
        `Meridian auth error (HTTP ${event.status}). Run /meridian to check login status.`,
        "error"
      );
      return;
    }

    if (event.status >= 500) {
      ctx.ui.notify(
        `Meridian server error (HTTP ${event.status}). The proxy may be misconfigured or down.`,
        "error"
      );
      return;
    }

    if (event.status >= 400) {
      ctx.ui.notify(
        `Meridian request error (HTTP ${event.status}).`,
        "warning"
      );
    }
  });
}

function registerMeridianCommand(
  pi: ExtensionAPI,
  baseUrl: string,
  port: number
): void {
  pi.registerCommand("meridian", {
    description: "Check Meridian status. Use: /meridian start | /meridian version",
    handler: async (args, ctx) => {
      const subcommand = args.trim().toLowerCase();

      if (subcommand === "start") {
        const { ok: alreadyRunning, health } = await isReachable(baseUrl);
        if (alreadyRunning && health) {
          ctx.ui.notify(`Meridian is already running at ${baseUrl}`, "info");
          return;
        }

        ctx.ui.notify(`Starting Meridian on port ${port}...`, "info");
        const started = await startMeridianDaemon(baseUrl, port);
        if (!started) {
          ctx.ui.notify(
            "Failed to start Meridian. Is it installed? (npm install -g @rynfar/meridian)",
            "error"
          );
          return;
        }

        const healthStatus = await fetchHealth(baseUrl);
        if (healthStatus.auth?.loggedIn) {
          ctx.ui.notify(
            `✓ Meridian started (${baseUrl}) — ${healthStatus.auth.email} (${healthStatus.auth.subscriptionType || "unknown"})`,
            "info"
          );
          return;
        }

        ctx.ui.notify(
          `✓ Meridian started (${baseUrl}) — not logged in, run: claude login`,
          "warning"
        );
        return;
      }

      if (subcommand === "version" || subcommand === "update") {
        ctx.ui.notify("Checking Meridian version...", "info");
        const [health, version] = await Promise.all([
          fetchHealth(baseUrl).catch((): MeridianHealth => ({ status: "unreachable" })),
          checkVersion(),
        ]);

        const lines: string[] = [];
        if (version.installed) {
          lines.push(`Installed: v${version.installed}`);
        } else {
          lines.push("Installed: unknown (meridian not found on PATH)");
        }

        if (version.latest) {
          lines.push(`Latest:    v${version.latest}`);
        } else {
          lines.push("Latest:    could not check (npm unreachable?)");
        }

        if (version.updateAvailable) {
          lines.push("");
          lines.push(`⚠ Update available: v${version.installed} → v${version.latest}`);
          lines.push("  Run: npm install -g @rynfar/meridian");
        } else if (version.installed && version.latest) {
          lines.push("");
          lines.push("✓ Up to date");
        }

        lines.push("");
        lines.push(health.status !== "unreachable" ? `Running at ${baseUrl}` : "Not running");

        ctx.ui.notify(lines.join("\n"), version.updateAvailable ? "warning" : "info");
        return;
      }

      if (subcommand) {
        ctx.ui.notify(
          `Unknown /meridian subcommand: ${subcommand}. Use: /meridian start | /meridian version`,
          "error"
        );
        return;
      }

      let health: MeridianHealth;
      try {
        health = await fetchHealth(baseUrl, ctx.signal);
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        if (message.includes("timed out")) {
          ctx.ui.notify(`Meridian health check timed out at ${baseUrl}`, "error");
        } else if (error instanceof Error && error.name === "AbortError") {
          return;
        } else {
          ctx.ui.notify(
            `Meridian unreachable at ${baseUrl}. Use /meridian start to launch it.`,
            "error"
          );
        }
        return;
      }

      if (health.status === "healthy" && health.auth?.loggedIn) {
        ctx.ui.notify(
          [
            `✓ Meridian connected (${baseUrl})`,
            `  Auth: ${health.auth.email} (${health.auth.subscriptionType || "unknown"})`,
            `  Mode: ${health.mode || "unknown"}`,
          ].join("\n"),
          "info"
        );
        return;
      }

      if (health.status === "healthy") {
        ctx.ui.notify(
          `Meridian connected but auth issue: ${health.error || "not logged in"}. Run: claude login`,
          "warning"
        );
        return;
      }

      if (health.status === "degraded") {
        ctx.ui.notify(
          `Meridian degraded: ${health.error || "unknown"}`,
          "warning"
        );
        return;
      }

      ctx.ui.notify(
        `Meridian unhealthy: ${health.error || health.status}`,
        "error"
      );
    },
  });
}

function registerSessionStartHook(
  pi: ExtensionAPI,
  baseUrl: string,
  port: number
): void {
  pi.on("session_start", async (_event, ctx) => {
    if (!isMeridianProvider(ctx.model)) return;

    try {
      const health = await fetchHealth(baseUrl);
      if (health.status !== "healthy" || !health.auth?.loggedIn) {
        ctx.ui.notify(
          `Meridian issue: ${health.error || health.status}. Run /meridian for details.`,
          "warning"
        );
      }
    } catch {
      ctx.ui.notify("Meridian not running. Auto-starting...", "info");
      const started = await startMeridianDaemon(baseUrl, port);
      if (started) {
        ctx.ui.notify(`✓ Meridian auto-started at ${baseUrl}`, "info");
      } else {
        ctx.ui.notify("Could not auto-start Meridian. Run manually: meridian", "error");
      }
    }

    if (!versionChecked) {
      versionChecked = true;
      const version = await checkVersion();
      if (version.updateAvailable) {
        ctx.ui.notify(
          `⚠ Meridian update available: v${version.installed} → v${version.latest}. Run /meridian version for details.`,
          "warning"
        );
      }
    }
  });
}

export default function meridianExtension(pi: ExtensionAPI): void {
  const baseUrl = getBaseUrl();
  const port = getPortFromBaseUrl(baseUrl);

  registerMeridianProvider(pi, baseUrl);
  registerProviderHooks(pi);
  registerMeridianCommand(pi, baseUrl, port);
  registerSessionStartHook(pi, baseUrl, port);
}
