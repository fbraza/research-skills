import { exec as execCallback } from "node:child_process";
import { realpathSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { promisify } from "node:util";

const exec = promisify(execCallback);

export interface VersionStatus {
  installed: string | null;
  latest: string | null;
  updateAvailable: boolean;
}

/**
 * Compare two semver strings.
 * Returns negative if a < b, 0 if equal, positive if a > b.
 */
export function compareSemver(a: string, b: string): number {
  const pa = a.replace(/^v/, "").split(".").map(Number);
  const pb = b.replace(/^v/, "").split(".").map(Number);

  for (let index = 0; index < 3; index++) {
    const left = pa[index] || 0;
    const right = pb[index] || 0;
    if (left !== right) return left - right;
  }

  return 0;
}

async function getInstalledVersion(): Promise<string | null> {
  try {
    const { stdout } = await exec("which meridian", { timeout: 3000 });
    const binPath = stdout.trim();
    if (!binPath) return null;

    const resolved = realpathSync(binPath);
    const binDirectory = dirname(resolved);

    const possiblePaths = [
      join(binDirectory, "..", "lib", "node_modules", "@rynfar", "meridian", "package.json"),
      join(binDirectory, "..", "node_modules", "@rynfar", "meridian", "package.json"),
      join(binDirectory, "package.json"),
      join(binDirectory, "..", "package.json"),
    ];

    for (const packageJsonPath of possiblePaths) {
      try {
        const content = await readFile(packageJsonPath, "utf8");
        const parsed: unknown = JSON.parse(content);
        if (
          typeof parsed === "object" &&
          parsed !== null &&
          (parsed as Record<string, unknown>).name === "@rynfar/meridian" &&
          typeof (parsed as Record<string, unknown>).version === "string"
        ) {
          return (parsed as Record<string, string>).version;
        }
      } catch {
        // Try the next candidate path.
      }
    }
  } catch {
    // Fall through.
  }

  return null;
}

async function getLatestVersion(): Promise<string | null> {
  try {
    const { stdout } = await exec("npm view @rynfar/meridian version", {
      timeout: 10000,
    });
    return stdout.trim();
  } catch {
    return null;
  }
}

export async function checkVersion(): Promise<VersionStatus> {
  const [installed, latest] = await Promise.all([
    getInstalledVersion(),
    getLatestVersion(),
  ]);

  return {
    installed,
    latest,
    updateAvailable:
      installed !== null && latest !== null && compareSemver(installed, latest) < 0,
  };
}
