import type { CwdKey, DayAgg, DowKey, ModelKey, RangeAgg, RGB, TodKey } from "./types.ts";
import { DOW_NAMES, DOW_PALETTE, PALETTE, TOD_BUCKETS, TOD_PALETTE } from "./constants.ts";
import { addDaysLocal, localMidnight, sortMapByValueDesc, toLocalDayKey } from "./utils.ts";
import type { ParsedSession } from "./types.ts";

export function buildRangeAgg(days: number, now: Date): RangeAgg {
	const end = localMidnight(now);
	const start = addDaysLocal(end, -(days - 1));
	const outDays: DayAgg[] = [];
	const dayByKey = new Map<string, DayAgg>();

	for (let i = 0; i < days; i++) {
		const d = addDaysLocal(start, i);
		const dayKeyLocal = toLocalDayKey(d);
		const day: DayAgg = {
			date: d,
			dayKeyLocal,
			sessions: 0,
			messages: 0,
			tokens: 0,
			totalCost: 0,
			costByModel: new Map(),
			sessionsByModel: new Map(),
			messagesByModel: new Map(),
			tokensByModel: new Map(),
			sessionsByCwd: new Map(),
			messagesByCwd: new Map(),
			tokensByCwd: new Map(),
			costByCwd: new Map(),
			sessionsByTod: new Map(),
			messagesByTod: new Map(),
			tokensByTod: new Map(),
			costByTod: new Map(),
		};
		outDays.push(day);
		dayByKey.set(dayKeyLocal, day);
	}

	return {
		days: outDays,
		dayByKey,
		sessions: 0,
		totalMessages: 0,
		totalTokens: 0,
		totalCost: 0,
		modelCost: new Map(),
		modelSessions: new Map(),
		modelMessages: new Map(),
		modelTokens: new Map(),
		cwdCost: new Map(),
		cwdSessions: new Map(),
		cwdMessages: new Map(),
		cwdTokens: new Map(),
		dowCost: new Map(),
		dowSessions: new Map(),
		dowMessages: new Map(),
		dowTokens: new Map(),
		todCost: new Map(),
		todSessions: new Map(),
		todMessages: new Map(),
		todTokens: new Map(),
	};
}

export function addSessionToRange(range: RangeAgg, session: ParsedSession): void {
	const day = range.dayByKey.get(session.dayKeyLocal);
	if (!day) return;

	range.sessions += 1;
	range.totalMessages += session.messages;
	range.totalTokens += session.tokens;
	range.totalCost += session.totalCost;
	day.sessions += 1;
	day.messages += session.messages;
	day.tokens += session.tokens;
	day.totalCost += session.totalCost;

	// Sessions-per-model (presence)
	for (const mk of session.modelsUsed) {
		day.sessionsByModel.set(mk, (day.sessionsByModel.get(mk) ?? 0) + 1);
		range.modelSessions.set(mk, (range.modelSessions.get(mk) ?? 0) + 1);
	}

	// Messages-per-model
	for (const [mk, n] of session.messagesByModel.entries()) {
		day.messagesByModel.set(mk, (day.messagesByModel.get(mk) ?? 0) + n);
		range.modelMessages.set(mk, (range.modelMessages.get(mk) ?? 0) + n);
	}

	// Tokens-per-model
	for (const [mk, n] of session.tokensByModel.entries()) {
		day.tokensByModel.set(mk, (day.tokensByModel.get(mk) ?? 0) + n);
		range.modelTokens.set(mk, (range.modelTokens.get(mk) ?? 0) + n);
	}

	// Cost-per-model
	for (const [mk, cost] of session.costByModel.entries()) {
		day.costByModel.set(mk, (day.costByModel.get(mk) ?? 0) + cost);
		range.modelCost.set(mk, (range.modelCost.get(mk) ?? 0) + cost);
	}

	// CWD aggregation
	const cwd = session.cwd;
	if (cwd) {
		day.sessionsByCwd.set(cwd, (day.sessionsByCwd.get(cwd) ?? 0) + 1);
		range.cwdSessions.set(cwd, (range.cwdSessions.get(cwd) ?? 0) + 1);
		day.messagesByCwd.set(cwd, (day.messagesByCwd.get(cwd) ?? 0) + session.messages);
		range.cwdMessages.set(cwd, (range.cwdMessages.get(cwd) ?? 0) + session.messages);
		day.tokensByCwd.set(cwd, (day.tokensByCwd.get(cwd) ?? 0) + session.tokens);
		range.cwdTokens.set(cwd, (range.cwdTokens.get(cwd) ?? 0) + session.tokens);
		day.costByCwd.set(cwd, (day.costByCwd.get(cwd) ?? 0) + session.totalCost);
		range.cwdCost.set(cwd, (range.cwdCost.get(cwd) ?? 0) + session.totalCost);
	}

	// Day-of-week aggregation
	const dow = session.dow;
	range.dowSessions.set(dow, (range.dowSessions.get(dow) ?? 0) + 1);
	range.dowMessages.set(dow, (range.dowMessages.get(dow) ?? 0) + session.messages);
	range.dowTokens.set(dow, (range.dowTokens.get(dow) ?? 0) + session.tokens);
	range.dowCost.set(dow, (range.dowCost.get(dow) ?? 0) + session.totalCost);

	// Time-of-day aggregation
	const tod = session.tod;
	day.sessionsByTod.set(tod, (day.sessionsByTod.get(tod) ?? 0) + 1);
	day.messagesByTod.set(tod, (day.messagesByTod.get(tod) ?? 0) + session.messages);
	day.tokensByTod.set(tod, (day.tokensByTod.get(tod) ?? 0) + session.tokens);
	day.costByTod.set(tod, (day.costByTod.get(tod) ?? 0) + session.totalCost);
	range.todSessions.set(tod, (range.todSessions.get(tod) ?? 0) + 1);
	range.todMessages.set(tod, (range.todMessages.get(tod) ?? 0) + session.messages);
	range.todTokens.set(tod, (range.todTokens.get(tod) ?? 0) + session.tokens);
	range.todCost.set(tod, (range.todCost.get(tod) ?? 0) + session.totalCost);
}

export function choosePaletteFromLast30Days(range30: RangeAgg, topN = 4): {
	modelColors: Map<ModelKey, RGB>;
	otherColor: RGB;
	orderedModels: ModelKey[];
} {
	// Prefer cost if any cost exists, else tokens, else messages, else sessions.
	const costSum = [...range30.modelCost.values()].reduce((a, b) => a + b, 0);
	const popularity =
		costSum > 0
			? range30.modelCost
			: range30.totalTokens > 0
				? range30.modelTokens
				: range30.totalMessages > 0
					? range30.modelMessages
					: range30.modelSessions;

	const sorted = sortMapByValueDesc(popularity);
	const orderedModels = sorted.slice(0, topN).map((x) => x.key);
	const modelColors = new Map<ModelKey, RGB>();
	for (let i = 0; i < orderedModels.length; i++) {
		modelColors.set(orderedModels[i], PALETTE[i % PALETTE.length]);
	}
	return {
		modelColors,
		otherColor: { r: 160, g: 160, b: 160 },
		orderedModels,
	};
}

export function chooseCwdPaletteFromLast30Days(range30: RangeAgg, topN = 4): {
	cwdColors: Map<CwdKey, RGB>;
	otherColor: RGB;
	orderedCwds: CwdKey[];
} {
	const costSum = [...range30.cwdCost.values()].reduce((a, b) => a + b, 0);

	const popularity =
		costSum > 0
			? range30.cwdCost
			: range30.totalTokens > 0
				? range30.cwdTokens
				: range30.totalMessages > 0
					? range30.cwdMessages
					: range30.cwdSessions;

	const sorted = sortMapByValueDesc(popularity);
	const orderedCwds = sorted.slice(0, topN).map((x) => x.key);
	const cwdColors = new Map<CwdKey, RGB>();
	for (let i = 0; i < orderedCwds.length; i++) {
		cwdColors.set(orderedCwds[i], PALETTE[i % PALETTE.length]);
	}
	return {
		cwdColors,
		otherColor: { r: 160, g: 160, b: 160 },
		orderedCwds,
	};
}

export function buildDowPalette(): { dowColors: Map<DowKey, RGB>; orderedDows: DowKey[] } {
	const dowColors = new Map<DowKey, RGB>();
	for (let i = 0; i < DOW_NAMES.length; i++) {
		dowColors.set(DOW_NAMES[i], DOW_PALETTE[i]);
	}
	return { dowColors, orderedDows: [...DOW_NAMES] };
}

export function buildTodPalette(): { todColors: Map<TodKey, RGB>; orderedTods: TodKey[] } {
	const todColors = new Map<TodKey, RGB>();
	const orderedTods: TodKey[] = [];
	for (const b of TOD_BUCKETS) {
		const c = TOD_PALETTE.get(b.key);
		if (c) todColors.set(b.key, c);
		orderedTods.push(b.key);
	}
	return { todColors, orderedTods };
}
