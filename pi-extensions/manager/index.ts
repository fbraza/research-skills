import type { ExtensionAPI, ExtensionCommandContext } from "@mariozechner/pi-coding-agent";
import type { OverlayResult } from "./constants.ts";
import { SkillManagerOverlay } from "./overlay.ts";

export { getLocalSkillsPath, installManagedSkills, listInstalledSkills, pathExists } from "./data.ts";

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
				try {
					await ctx.reload();
				} catch {
					// reload may fail (e.g. extension re-load issue) — don't
					// let an unhandled error leave the command unregistered
				}
				return;
			}
		},
	});
}
