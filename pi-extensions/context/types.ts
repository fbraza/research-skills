export type SkillIndexEntry = {
	name: string;
	skillFilePath: string;
	skillDir: string;
};

export type SkillLoadedEntryData = {
	name: string;
	path: string;
};

export type ContextViewData = {
	usage:
		| {
			// message-based context usage estimate from ctx.getContextUsage()
			messageTokens: number;
			contextWindow: number;
			// effective usage incl. a rough tool-definition estimate
			effectiveTokens: number;
			percent: number;
			remainingTokens: number;
			systemPromptTokens: number;
			agentTokens: number;
			toolsTokens: number;
			activeTools: number;
		}
		| null;
	agentFiles: string[];
	extensions: string[];
	skills: string[];
	loadedSkills: string[];
	session: { totalTokens: number; totalCost: number };
};
