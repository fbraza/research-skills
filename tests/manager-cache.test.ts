import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { REMOTE_REPO, type ExecFn, type ExecResult } from "../pi-extensions/manager/constants.ts";
import { ensureCache, pathExists } from "../pi-extensions/manager/data.ts";

function execResult(code: number, stdout = "", stderr = ""): ExecResult {
	return { code, stdout, stderr };
}

function createExecMock(
	handler: (command: string, args: string[], callIndex: number) => Promise<ExecResult> | ExecResult,
): { exec: ExecFn; calls: Array<{ command: string; args: string[] }> } {
	const calls: Array<{ command: string; args: string[] }> = [];
	const exec: ExecFn = async (command, args) => {
		calls.push({ command, args: [...args] });
		return handler(command, args, calls.length - 1);
	};
	return { exec, calls };
}

async function createTempRoot(): Promise<string> {
	return fs.mkdtemp(path.join(os.tmpdir(), "manager-cache-test-"));
}

test("ensureCache clones when the cache directory is missing", async () => {
	const tempRoot = await createTempRoot();
	const cacheDir = path.join(tempRoot, "cache");
	const cloneArgs = ["clone", "--depth", "1", `https://github.com/${REMOTE_REPO}.git`, cacheDir];
	const { exec, calls } = createExecMock((command, args) => {
		assert.equal(command, "git");
		assert.deepEqual(args, cloneArgs);
		return execResult(0);
	});

	try {
		const result = await ensureCache(exec, cacheDir);
		assert.deepEqual(result, { rebuilt: false });
		assert.deepEqual(calls, [{ command: "git", args: cloneArgs }]);
	} finally {
		await fs.rm(tempRoot, { recursive: true, force: true });
	}
});

test("ensureCache validates, fetches, and resets a healthy cache", async () => {
	const tempRoot = await createTempRoot();
	const cacheDir = path.join(tempRoot, "cache");
	await fs.mkdir(cacheDir, { recursive: true });
	const expectedCalls = [
		["-C", cacheDir, "rev-parse", "--is-inside-work-tree"],
		["-C", cacheDir, "fetch", "origin", "main", "--depth", "1"],
		["-C", cacheDir, "reset", "--hard", "origin/main"],
	];
	const { exec, calls } = createExecMock((_command, _args, callIndex) => {
		switch (callIndex) {
			case 0:
				return execResult(0, "true\n");
			case 1:
				return execResult(0);
			case 2:
				return execResult(0);
			default:
				throw new Error(`Unexpected git call #${callIndex}`);
		}
	});

	try {
		const result = await ensureCache(exec, cacheDir);
		assert.deepEqual(result, { rebuilt: false });
		assert.deepEqual(
			calls.map((call) => call.args),
			expectedCalls,
		);
	} finally {
		await fs.rm(tempRoot, { recursive: true, force: true });
	}
});

test("ensureCache removes an invalid cache and reclones it", async () => {
	const tempRoot = await createTempRoot();
	const cacheDir = path.join(tempRoot, "cache");
	await fs.mkdir(path.join(cacheDir, ".git"), { recursive: true });
	await fs.writeFile(path.join(cacheDir, ".git", "HEAD"), "broken");
	const cloneArgs = ["clone", "--depth", "1", `https://github.com/${REMOTE_REPO}.git`, cacheDir];
	const { exec, calls } = createExecMock((_command, _args, callIndex) => {
		switch (callIndex) {
			case 0:
				return execResult(128, "", "fatal: not a git repository (or any of the parent directories): .git");
			case 1:
				return execResult(0);
			default:
				throw new Error(`Unexpected git call #${callIndex}`);
		}
	});

	try {
		const result = await ensureCache(exec, cacheDir);
		assert.deepEqual(result, {
			rebuilt: true,
			message: "Detected an invalid local skill cache and rebuilt it automatically.",
		});
		assert.deepEqual(calls[0]?.args, ["-C", cacheDir, "rev-parse", "--is-inside-work-tree"]);
		assert.deepEqual(calls[1]?.args, cloneArgs);
		assert.equal(await pathExists(cacheDir), false);
	} finally {
		await fs.rm(tempRoot, { recursive: true, force: true });
	}
});

test("ensureCache surfaces non-recoverable fetch failures clearly", async () => {
	const tempRoot = await createTempRoot();
	const cacheDir = path.join(tempRoot, "cache");
	await fs.mkdir(cacheDir, { recursive: true });
	const { exec, calls } = createExecMock((_command, _args, callIndex) => {
		switch (callIndex) {
			case 0:
				return execResult(0, "true\n");
			case 1:
				return execResult(128, "", "fatal: unable to access 'https://github.com/fbraza/research-skills.git/': Could not resolve host: github.com");
			default:
				throw new Error(`Unexpected git call #${callIndex}`);
		}
	});

	try {
		await assert.rejects(() => ensureCache(exec, cacheDir), {
			message:
				"Failed to refresh skill cache: fatal: unable to access 'https://github.com/fbraza/research-skills.git/': Could not resolve host: github.com",
		});
		assert.equal(calls.length, 2);
		assert.deepEqual(calls[1]?.args, ["-C", cacheDir, "fetch", "origin", "main", "--depth", "1"]);
	} finally {
		await fs.rm(tempRoot, { recursive: true, force: true });
	}
});

test("ensureCache reports clone failures after invalid-cache recovery", async () => {
	const tempRoot = await createTempRoot();
	const cacheDir = path.join(tempRoot, "cache");
	await fs.mkdir(cacheDir, { recursive: true });
	const { exec } = createExecMock((_command, _args, callIndex) => {
		switch (callIndex) {
			case 0:
				return execResult(128, "", "fatal: not a git repository (or any of the parent directories): .git");
			case 1:
				return execResult(128, "", "fatal: repository 'https://github.com/fbraza/research-skills.git/' not found");
			default:
				throw new Error(`Unexpected git call #${callIndex}`);
		}
	});

	try {
		await assert.rejects(
			() => ensureCache(exec, cacheDir),
			(error: unknown) =>
				error instanceof Error &&
				error.message.includes(`Detected an invalid skill cache at ${cacheDir}.`) &&
				error.message.includes("Tried to rebuild the cache, but cloning failed.") &&
				error.message.includes("Failed to clone skill repository: fatal: repository 'https://github.com/fbraza/research-skills.git/' not found"),
		);
	} finally {
		await fs.rm(tempRoot, { recursive: true, force: true });
	}
});

test("ensureCache rebuilds the cache after a recoverable git corruption error", async () => {
	const tempRoot = await createTempRoot();
	const cacheDir = path.join(tempRoot, "cache");
	await fs.mkdir(cacheDir, { recursive: true });
	const cloneArgs = ["clone", "--depth", "1", `https://github.com/${REMOTE_REPO}.git`, cacheDir];
	const { exec, calls } = createExecMock((_command, _args, callIndex) => {
		switch (callIndex) {
			case 0:
				return execResult(0, "true\n");
			case 1:
				return execResult(128, "", "fatal: bad object refs/remotes/origin/main");
			case 2:
				return execResult(0);
			default:
				throw new Error(`Unexpected git call #${callIndex}`);
		}
	});

	try {
		const result = await ensureCache(exec, cacheDir);
		assert.deepEqual(result, {
			rebuilt: true,
			message: "Detected a broken local skill cache and rebuilt it automatically.",
		});
		assert.deepEqual(calls[2]?.args, cloneArgs);
		assert.equal(await pathExists(cacheDir), false);
	} finally {
		await fs.rm(tempRoot, { recursive: true, force: true });
	}
});
