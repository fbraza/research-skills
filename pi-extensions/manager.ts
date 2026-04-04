import type { ExtensionAPI, ExtensionCommandContext, Theme } from "@mariozechner/pi-coding-agent";
import type { TUI } from "@mariozechner/pi-tui";
import { Key, matchesKey, truncateToWidth, visibleWidth, wrapTextWithAnsi } from "@mariozechner/pi-tui";
import fs from "node:fs/promises";
import { existsSync } from "node:fs";
import os from "node:os";
import path from "node:path";

const REMOTE_REPO = "fbraza/research-skills";
const REMOTE_SKILLS_PATH = "skills";
const LOCAL_SKILLS_DIR = path.join(".agents", "skills");
const CACHE_DIR = path.join(os.tmpdir(), "bio-skills-cache");
const ALL_ID = "__all__";
const SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];

interface ExecResult {
	stdout: string;
	stderr: string;
	code: number;
	killed?: boolean;
}

type ExecFn = (command: string, args: string[], options?: { timeout?: number; signal?: AbortSignal }) => Promise<ExecResult>;

type Screen = "mode" | "loading" | "list" | "empty" | "error" | "progress";
type ActionMode = "install" | "update" | "remove";
type ProgressStatus = "waiting" | "running" | "done" | "failed";

interface ProgressItem {
	name: string;
	status: ProgressStatus;
	error?: string;
}

interface OverlayResult {
	changed: boolean;
}

interface ListRow {
	id: string;
	label: string;
	description?: string;
}

function normalizeError(error: unknown): string {
	if (error instanceof Error && error.message) return error.message;
	return String(error);
}

function padRight(text: string, width: number): string {
	const diff = Math.max(0, width - visibleWidth(text));
	return text + " ".repeat(diff);
}

function centerText(text: string, width: number): string {
	const truncated = truncateToWidth(text, width, "");
	const diff = Math.max(0, width - visibleWidth(truncated));
	const left = Math.floor(diff / 2);
	return " ".repeat(left) + truncated + " ".repeat(diff - left);
}

function boxedLine(content: string, innerWidth: number): string {
	return `│ ${padRight(truncateToWidth(content, innerWidth, ""), innerWidth)} │`;
}

function wrapLine(line: string, width: number): string[] {
	const wrapped = wrapTextWithAnsi(line, width);
	return wrapped.length > 0 ? wrapped : [""];
}

function renderPanel(
	width: number,
	title: string,
	bodyLines: string[],
	footerLines: string[] = [],
	subtitle?: string,
): string[] {
	const panelWidth = Math.max(24, width);
	const innerWidth = Math.max(20, panelWidth - 4);
	const lines: string[] = [];
	lines.push(`╭${"─".repeat(panelWidth - 2)}╮`);
	lines.push(boxedLine(centerText(title, innerWidth), innerWidth));
	if (subtitle) lines.push(boxedLine(subtitle, innerWidth));
	lines.push(`├${"─".repeat(panelWidth - 2)}┤`);
	for (const line of bodyLines.length > 0 ? bodyLines : [""]) {
		for (const wrapped of wrapLine(line, innerWidth)) lines.push(boxedLine(wrapped, innerWidth));
	}
	if (footerLines.length > 0) {
		lines.push(`├${"─".repeat(panelWidth - 2)}┤`);
		for (const line of footerLines) {
			for (const wrapped of wrapLine(line, innerWidth)) lines.push(boxedLine(wrapped, innerWidth));
		}
	}
	lines.push(`╰${"─".repeat(panelWidth - 2)}╯`);
	return lines.map((line) => truncateToWidth(line, panelWidth, ""));
}

export function getLocalSkillsPath(cwd: string): string {
	return path.join(cwd, LOCAL_SKILLS_DIR);
}

export async function pathExists(filePath: string): Promise<boolean> {
	try {
		await fs.access(filePath);
		return true;
	} catch {
		return false;
	}
}

export async function listInstalledSkills(cwd: string): Promise<string[]> {
	const skillsDir = getLocalSkillsPath(cwd);
	if (!(await pathExists(skillsDir))) return [];

	const entries = await fs.readdir(skillsDir, { withFileTypes: true });
	const installed: string[] = [];
	for (const entry of entries) {
		if (!entry.isDirectory()) continue;
		const skillDir = path.join(skillsDir, entry.name);
		const skillFile = path.join(skillDir, "SKILL.md");
		if (await pathExists(skillFile)) installed.push(entry.name);
	}
	return installed.sort((a, b) => a.localeCompare(b));
}

async function ensureGhAuthenticated(exec: ExecFn): Promise<void> {
	try {
		const result = await exec("gh", ["auth", "status"], { timeout: 20_000 });
		if (result.code !== 0) {
			throw new Error("GitHub CLI (`gh`) is required. Run `gh auth login` first.");
		}
	} catch (error) {
		throw new Error(`GitHub CLI (gh) is required and must be authenticated. ${normalizeError(error)}`);
	}
}

async function listRemoteSkills(exec: ExecFn): Promise<string[]> {
	await ensureGhAuthenticated(exec);
	const result = await exec("gh", ["api", `repos/${REMOTE_REPO}/contents/${REMOTE_SKILLS_PATH}`], { timeout: 30_000 });
	if (result.code !== 0) {
		throw new Error(result.stderr.trim() || result.stdout.trim() || "Failed to fetch remote skill list.");
	}

	let payload: Array<{ name?: string; type?: string }> = [];
	try {
		payload = JSON.parse(result.stdout);
	} catch (error) {
		throw new Error(`Failed to parse GitHub API response: ${normalizeError(error)}`);
	}

	return payload
		.filter((entry) => entry.type === "dir" && typeof entry.name === "string")
		.map((entry) => entry.name as string)
		.sort((a, b) => a.localeCompare(b));
}

export async function ensureCache(exec: ExecFn): Promise<void> {
	const gitDir = path.join(CACHE_DIR, ".git");
	if (existsSync(gitDir)) {
		const fetchResult = await exec("git", ["-C", CACHE_DIR, "fetch", "origin", "main", "--depth", "1"], { timeout: 60_000 });
		if (fetchResult.code !== 0) {
			throw new Error(fetchResult.stderr.trim() || fetchResult.stdout.trim() || "Failed to refresh skill cache.");
		}
		const resetResult = await exec("git", ["-C", CACHE_DIR, "reset", "--hard", "origin/main"], { timeout: 60_000 });
		if (resetResult.code !== 0) {
			throw new Error(resetResult.stderr.trim() || resetResult.stdout.trim() || "Failed to reset skill cache.");
		}
		return;
	}

	const cloneResult = await exec(
		"git",
		["clone", "--depth", "1", `https://github.com/${REMOTE_REPO}.git`, CACHE_DIR],
		{ timeout: 120_000 },
	);
	if (cloneResult.code !== 0) {
		throw new Error(cloneResult.stderr.trim() || cloneResult.stdout.trim() || "Failed to clone skill repository.");
	}
}

export async function ensureLocalSkillsDir(cwd: string): Promise<string> {
	const skillsDir = getLocalSkillsPath(cwd);
	await fs.mkdir(skillsDir, { recursive: true });
	return skillsDir;
}

export async function copySkillFromCache(name: string, cwd: string): Promise<void> {
	const targetDir = await ensureLocalSkillsDir(cwd);
	const sourceDir = path.join(CACHE_DIR, REMOTE_SKILLS_PATH, name);
	const destinationDir = path.join(targetDir, name);
	if (!(await pathExists(sourceDir))) {
		throw new Error(`Skill '${name}' was not found in the cache.`);
	}
	await fs.rm(destinationDir, { recursive: true, force: true });
	await fs.cp(sourceDir, destinationDir, { recursive: true });
}

export async function removeLocalSkill(name: string, cwd: string): Promise<void> {
	const destinationDir = path.join(getLocalSkillsPath(cwd), name);
	await fs.rm(destinationDir, { recursive: true, force: true });
}

export async function installManagedSkills(exec: ExecFn, cwd: string, names: string[]): Promise<void> {
	if (names.length === 0) return;
	await ensureCache(exec);
	for (const name of names) {
		await copySkillFromCache(name, cwd);
	}
}

class SkillManagerOverlay {
	private readonly modeItems = ["Install skills", "Update skills", "Remove skills"];
	private screen: Screen = "mode";
	private modeCursor = 0;
	private actionMode: ActionMode | null = null;
	private listItems: string[] = [];
	private selected = new Set<string>();
	private cursor = 0;
	private filter = "";
	private filterFocused = false;
	private installedCount = 0;
	private availableCount = 0;
	private changed = false;
	private spinnerIndex = 0;
	private spinnerTimer: NodeJS.Timeout | null = null;
	private loadingMessage = "";
	private errorMessage = "";
	private retryAction: (() => void) | null = null;
	private emptyMessage = "";
	private progressItems: ProgressItem[] = [];
	private progressDone = false;
	private cancelRequested = false;
	private viewToken = 0;
	private cachedWidth?: number;
	private cachedLines?: string[];

	constructor(
		private readonly tui: TUI,
		private readonly theme: Theme,
		private readonly ctx: ExtensionCommandContext,
		private readonly exec: ExecFn,
		private readonly finish: (result: OverlayResult) => void,
	) {}

	invalidate(): void {
		this.cachedWidth = undefined;
		this.cachedLines = undefined;
	}

	handleInput(data: string): void {
		if (this.screen === "mode") {
			this.handleModeInput(data);
			return;
		}
		if (this.screen === "loading") {
			if (matchesKey(data, Key.escape)) this.showMode();
			return;
		}
		if (this.screen === "error") {
			if (matchesKey(data, Key.enter) && this.retryAction) {
				this.retryAction();
				return;
			}
			if (matchesKey(data, Key.escape) || matchesKey(data, Key.enter)) this.showMode();
			return;
		}
		if (this.screen === "empty") {
			if (matchesKey(data, Key.escape) || matchesKey(data, Key.enter)) this.showMode();
			return;
		}
		if (this.screen === "list") {
			this.handleListInput(data);
			return;
		}
		if (this.screen === "progress") {
			this.handleProgressInput(data);
		}
	}

	render(width: number): string[] {
		if (this.cachedLines && this.cachedWidth === width) return this.cachedLines;
		const panelWidth = Math.max(52, Math.min(width, 92));
		const lines = this.renderCurrent(panelWidth);
		this.cachedWidth = width;
		this.cachedLines = lines;
		return lines;
	}

	private requestRender(): void {
		this.invalidate();
		this.tui.requestRender();
	}

	private setSpinner(active: boolean): void {
		if (!active) {
			if (this.spinnerTimer) clearInterval(this.spinnerTimer);
			this.spinnerTimer = null;
			this.spinnerIndex = 0;
			return;
		}
		if (this.spinnerTimer) return;
		this.spinnerTimer = setInterval(() => {
			this.spinnerIndex = (this.spinnerIndex + 1) % SPINNER_FRAMES.length;
			this.requestRender();
		}, 100);
	}

	private currentSpinner(): string {
		return SPINNER_FRAMES[this.spinnerIndex] || SPINNER_FRAMES[0]!;
	}

	private renderCurrent(width: number): string[] {
		switch (this.screen) {
			case "mode":
				return this.renderMode(width);
			case "loading":
				return this.renderLoading(width);
			case "list":
				return this.renderList(width);
			case "empty":
				return this.renderEmpty(width);
			case "error":
				return this.renderError(width);
			case "progress":
				return this.renderProgress(width);
		}
	}

	private renderMode(width: number): string[] {
		const body = [
			"",
			...this.modeItems.map((item, index) => {
				const line = `${index === this.modeCursor ? "▸" : " "}  ${item}`;
				return index === this.modeCursor ? this.theme.bg("selectedBg", line) : line;
			}),
			"",
		];
		const footer = ["↑↓ navigate  •  enter select", "esc cancel"];
		return renderPanel(width, this.theme.fg("accent", this.theme.bold("Bio-Skills Manager")), body, footer);
	}

	private renderLoading(width: number): string[] {
		const title = this.actionMode === "install" ? "Install Skills" : this.actionMode === "update" ? "Update Skills" : "Remove Skills";
		const body = ["", ` ${this.theme.fg("accent", this.currentSpinner())} ${this.loadingMessage}`, ""];
		return renderPanel(width, this.theme.bold(title), body, ["esc back"]);
	}

	private renderEmpty(width: number): string[] {
		const title = this.actionMode === "update" ? "Update Skills" : "Remove Skills";
		const body = ["", this.emptyMessage, ""];
		return renderPanel(width, this.theme.bold(title), body, ["enter back  •  esc back"]);
	}

	private renderError(width: number): string[] {
		const body = ["", ...wrapLine(this.theme.fg("error", this.errorMessage), width - 4), ""];
		const footer = this.retryAction ? ["enter retry  •  esc back"] : ["enter back  •  esc back"];
		return renderPanel(width, this.theme.fg("error", this.theme.bold("Skill Manager Error")), body, footer);
	}

	private renderList(width: number): string[] {
		const title = this.actionMode === "install" ? "Install Skills" : this.actionMode === "update" ? "Update Skills" : "Remove Skills";
		const subtitle =
			this.actionMode === "install"
				? `${this.installedCount} installed  •  ${this.availableCount} available`
				: `${this.listItems.length} skills installed`;
		const rows = this.getVisibleRows();
		const body: string[] = [];
		if (this.actionMode === "install") {
			const filterText = this.filterFocused
				? this.theme.fg("accent", `/ ${this.filter || ""}█`)
				: this.filter
					? `/ ${this.filter}`
					: this.theme.fg("dim", "/  filter...");
			body.push(filterText, "");
		}
		if (rows.length === 0) {
			body.push(this.theme.fg("warning", "No skills match the current filter."));
		} else {
			for (let index = 0; index < rows.length; index++) {
				const row = rows[index]!;
				const isSelected = row.id === ALL_ID ? this.areAllSelected() : this.selected.has(row.id);
				const allState = row.id === ALL_ID ? (this.areAllSelected() ? "all" : this.selected.size > 0 ? "partial" : "none") : null;
				const checkbox =
					allState === "partial"
						? this.theme.fg("warning", "[~]")
						: isSelected
							? this.theme.fg("success", "[x]")
							: this.theme.fg("dim", "[ ]");
				const prefix = index === this.cursor ? "▸" : " ";
				const description = row.description ? `  ${this.theme.fg("muted", row.description)}` : "";
				let line = `${prefix} ${checkbox} ${row.label}${description}`;
				if (index === this.cursor) line = this.theme.bg("selectedBg", line);
				body.push(line);
				if (this.actionMode === "update" && row.id === ALL_ID) {
					body.push(this.theme.fg("dim", "  ───────────────────────────────"));
				}
			}
		}
		body.push("");
		const selectedCount = this.selected.size;
		const footer =
			this.actionMode === "install"
				? [
					"↑↓ navigate  •  space toggle",
					"/ search  •  a select all  •  A deselect all",
					selectedCount > 0 ? `enter confirm (${selectedCount} selected)  •  esc back` : this.theme.fg("dim", "enter confirm (0 selected)  •  esc back"),
				]
				: [
					"↑↓ navigate  •  space toggle",
					selectedCount > 0 ? `enter confirm (${selectedCount} selected)  •  esc back` : this.theme.fg("dim", "enter confirm (0 selected)  •  esc back"),
				];
		return renderPanel(width, this.theme.bold(title), body, footer, subtitle);
	}

	private renderProgress(width: number): string[] {
		const verb = this.actionMode === "install" ? "Installing" : this.actionMode === "update" ? "Updating" : "Removing";
		const complete = this.progressItems.filter((item) => item.status === "done" || item.status === "failed").length;
		const body: string[] = [""];
		for (const item of this.progressItems) {
			let icon = this.theme.fg("dim", "○");
			if (item.status === "running") icon = this.theme.fg("accent", this.currentSpinner());
			if (item.status === "done") icon = this.theme.fg("success", "✓");
			if (item.status === "failed") icon = this.theme.fg("error", "✗");
			body.push(` ${icon}  ${item.name}`);
			if (item.error) body.push(`    ${this.theme.fg("error", item.error)}`);
		}
		body.push("");
		if (this.progressDone) {
			body.push(this.cancelRequested ? this.theme.fg("warning", "Cancelled. Press any key to close.") : this.theme.fg("success", "Done! Press any key to close."));
		} else if (this.cancelRequested) {
			body.push(this.theme.fg("warning", "Cancel requested. Waiting for current operation to finish..."));
		} else {
			body.push(`${complete} / ${this.progressItems.length} complete`);
			body.push(this.theme.fg("dim", "esc cancels after the current in-flight skill"));
		}
		body.push("");
		return renderPanel(width, this.theme.bold(`${verb} ${this.progressItems.length} skill${this.progressItems.length === 1 ? "" : "s"}...`), body);
	}

	private handleModeInput(data: string): void {
		if (matchesKey(data, Key.up) && this.modeCursor > 0) {
			this.modeCursor--;
			this.requestRender();
			return;
		}
		if (matchesKey(data, Key.down) && this.modeCursor < this.modeItems.length - 1) {
			this.modeCursor++;
			this.requestRender();
			return;
		}
		if (matchesKey(data, Key.enter)) {
			if (this.modeCursor === 0) this.enterInstall();
			if (this.modeCursor === 1) this.enterUpdate();
			if (this.modeCursor === 2) this.enterRemove();
			return;
		}
		if (matchesKey(data, Key.escape)) {
			this.finish({ changed: this.changed });
		}
	}

	private handleListInput(data: string): void {
		if (this.filterFocused) {
			this.handleFilterInput(data);
			return;
		}
		const rows = this.getVisibleRows();
		if (matchesKey(data, Key.up) && this.cursor > 0) {
			this.cursor--;
			this.requestRender();
			return;
		}
		if (matchesKey(data, Key.down) && this.cursor < rows.length - 1) {
			this.cursor++;
			this.requestRender();
			return;
		}
		if (matchesKey(data, Key.space)) {
			this.toggleCurrent();
			return;
		}
		if (data === "a") {
			for (const row of rows) if (row.id !== ALL_ID) this.selected.add(row.id);
			this.requestRender();
			return;
		}
		if (data === "A") {
			for (const row of rows) if (row.id !== ALL_ID) this.selected.delete(row.id);
			this.requestRender();
			return;
		}
		if (this.actionMode === "install" && data === "/") {
			this.filterFocused = true;
			this.requestRender();
			return;
		}
		if (matchesKey(data, Key.enter)) {
			if (this.selected.size > 0) this.startProgress();
			return;
		}
		if (matchesKey(data, Key.escape)) {
			this.showMode();
		}
	}

	private handleFilterInput(data: string): void {
		if (matchesKey(data, Key.escape)) {
			this.filter = "";
			this.filterFocused = false;
			this.cursor = 0;
			this.requestRender();
			return;
		}
		if (matchesKey(data, Key.enter)) {
			this.filterFocused = false;
			this.requestRender();
			return;
		}
		if (matchesKey(data, Key.backspace)) {
			this.filter = this.filter.slice(0, -1);
			this.cursor = 0;
			this.requestRender();
			return;
		}
		if (data.length === 1 && data >= " ") {
			this.filter += data;
			this.cursor = 0;
			this.requestRender();
		}
	}

	private handleProgressInput(data: string): void {
		if (!this.progressDone) {
			if (matchesKey(data, Key.escape)) {
				this.cancelRequested = true;
				this.requestRender();
			}
			return;
		}
		this.finish({ changed: this.changed });
	}

	private getVisibleRows(): ListRow[] {
		let items = this.listItems;
		if (this.actionMode === "install" && this.filter.trim()) {
			const needle = this.filter.trim().toLowerCase();
			items = items.filter((item) => item.toLowerCase().includes(needle));
		}
		const rows: ListRow[] = items.map((item) => ({ id: item, label: item }));
		if (this.actionMode === "update") {
			rows.unshift({ id: ALL_ID, label: "All", description: "(update everything)" });
		}
		if (this.cursor >= rows.length) this.cursor = Math.max(0, rows.length - 1);
		return rows;
	}

	private areAllSelected(): boolean {
		return this.listItems.length > 0 && this.listItems.every((item) => this.selected.has(item));
	}

	private toggleCurrent(): void {
		const row = this.getVisibleRows()[this.cursor];
		if (!row) return;
		if (row.id === ALL_ID) {
			if (this.areAllSelected()) this.selected.clear();
			else this.selected = new Set(this.listItems);
			this.requestRender();
			return;
		}
		if (this.selected.has(row.id)) this.selected.delete(row.id);
		else this.selected.add(row.id);
		this.requestRender();
	}

	private showMode(): void {
		this.viewToken++;
		this.setSpinner(false);
		this.screen = "mode";
		this.actionMode = null;
		this.retryAction = null;
		this.filter = "";
		this.filterFocused = false;
		this.selected.clear();
		this.cursor = 0;
		this.requestRender();
	}

	private showError(message: string, retryAction?: () => void): void {
		this.setSpinner(false);
		this.screen = "error";
		this.errorMessage = message;
		this.retryAction = retryAction ?? null;
		this.requestRender();
	}

	private async enterInstall(): Promise<void> {
		this.actionMode = "install";
		this.screen = "loading";
		this.loadingMessage = "Fetching skill list from GitHub";
		this.retryAction = () => void this.enterInstall();
		this.setSpinner(true);
		this.requestRender();
		const token = ++this.viewToken;
		try {
			const [installed, remote] = await Promise.all([listInstalledSkills(this.ctx.cwd), listRemoteSkills(this.exec)]);
			if (token !== this.viewToken || this.screen !== "loading" || this.actionMode !== "install") return;
			const installedSet = new Set(installed);
			this.listItems = remote.filter((name) => !installedSet.has(name));
			this.installedCount = installed.length;
			this.availableCount = remote.length;
			this.selected.clear();
			this.cursor = 0;
			this.filter = "";
			this.filterFocused = false;
			this.setSpinner(false);
			this.screen = "list";
			this.requestRender();
		} catch (error) {
			if (token !== this.viewToken) return;
			this.showError(normalizeError(error), () => void this.enterInstall());
		}
	}

	private async enterUpdate(): Promise<void> {
		this.actionMode = "update";
		try {
			this.listItems = await listInstalledSkills(this.ctx.cwd);
			this.selected.clear();
			this.cursor = 0;
			if (this.listItems.length === 0) {
				this.screen = "empty";
				this.emptyMessage = "No skills installed yet. Use Install to add skills.";
			} else {
				this.screen = "list";
			}
			this.requestRender();
		} catch (error) {
			this.showError(normalizeError(error), () => void this.enterUpdate());
		}
	}

	private async enterRemove(): Promise<void> {
		this.actionMode = "remove";
		try {
			this.listItems = await listInstalledSkills(this.ctx.cwd);
			this.selected.clear();
			this.cursor = 0;
			if (this.listItems.length === 0) {
				this.screen = "empty";
				this.emptyMessage = "No skills installed yet. Use Install to add skills.";
			} else {
				this.screen = "list";
			}
			this.requestRender();
		} catch (error) {
			this.showError(normalizeError(error), () => void this.enterRemove());
		}
	}

	private startProgress(): void {
		const names = Array.from(this.selected).sort((a, b) => a.localeCompare(b));
		this.progressItems = names.map((name) => ({ name, status: "waiting" }));
		this.progressDone = false;
		this.cancelRequested = false;
		this.screen = "progress";
		this.setSpinner(true);
		this.requestRender();
		void this.runProgress(names);
	}

	private async runProgress(names: string[]): Promise<void> {
		try {
			if (this.actionMode === "install" || this.actionMode === "update") {
				await ensureCache(this.exec);
			}

			for (let index = 0; index < names.length; index++) {
				if (this.cancelRequested) break;
				const name = names[index]!;
				this.progressItems[index] = { name, status: "running" };
				this.requestRender();
				try {
					if (this.actionMode === "remove") {
						await removeLocalSkill(name, this.ctx.cwd);
					} else {
						await copySkillFromCache(name, this.ctx.cwd);
					}
					this.progressItems[index] = { name, status: "done" };
					this.changed = true;
				} catch (error) {
					this.progressItems[index] = { name, status: "failed", error: normalizeError(error) };
				}
				this.requestRender();
			}
		} finally {
			this.progressDone = true;
			this.setSpinner(false);
			this.requestRender();
		}
	}
}

export default function managerExtension(pi: ExtensionAPI) {
	pi.registerCommand("skills", {
		description: "Install, update, or remove skills from fbraza/bio-skills",
		handler: async (_args, ctx) => {
			const result = await ctx.ui.custom<OverlayResult>(
				(tui, theme, _kb, done) => new SkillManagerOverlay(tui, theme, ctx, pi.exec.bind(pi), done),
				{
					overlay: true,
					overlayOptions: {
						width: "60%",
						minWidth: 52,
						maxHeight: "80%",
						anchor: "center",
					},
				},
			);

			if (result?.changed) {
				await ctx.reload();
				return;
			}
		},
	});
}
