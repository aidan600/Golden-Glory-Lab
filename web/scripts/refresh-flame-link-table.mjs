import { readFile, writeFile } from "node:fs/promises";
import { isDeepStrictEqual } from "node:util";

// Offline app data refresh. Read pinned PoB text records without running Lua.
const tablePath = new URL("../site/data/flame-link-level-table-v2.json", import.meta.url);
const table = JSON.parse(await readFile(tablePath, "utf8"));
const write = process.argv.length === 3 && process.argv[2] === "--write";
if (process.argv.length > 2 && !write) {
  throw new Error("Usage: node web/scripts/refresh-flame-link-table.mjs [--write]");
}

const { sourceCommitSha, recordLocations } = table.provenance;
const sourceRoot = `https://raw.githubusercontent.com/PathOfBuildingCommunity/PathOfBuilding/${sourceCommitSha}/`;
async function readSource(record) {
  const url = new URL(recordLocations[record].split("#")[0], sourceRoot);
  const response = await fetch(url, { signal: AbortSignal.timeout(30_000) });
  if (!response.ok) {
    throw new Error(`Could not read ${url} (HTTP ${response.status})`);
  }
  return response.text();
}

function capture(text, pattern) {
  const match = text.match(pattern);
  if (!match) {
    throw new Error(`Review the pinned source record. Missing ${pattern}`);
  }
  return match[1];
}

const [skills, constants, tree] = await Promise.all([
  readSource("skill"),
  readSource("constants"),
  readSource("goldenGlory"),
]);
const skill = capture(skills, /^skills\["FlameLink"\] = \{([\s\S]*?)^\}/m);
const goldenGlory = capture(tree, /^\t\t\[31517\] = \{([\s\S]*?)^\t\t\},/m);
const maximumLifePercent = Number(capture(skill, /"flame_link_added_fire_damage_from_life_%", (\d+)/));
const goldenGloryLightRadiusPercent = Number(capture(goldenGlory, /on your Mercenary at (\d+)% of their value/));
const base = Number(capture(skill, /\bbaseEffectiveness = ([\d.]+)/));
const incremental = Number(capture(skill, /\bincrementalEffectiveness = ([\d.]+)/));
const globalBase = Number(capture(constants, /\["SkillDamageBaseEffectiveness"\] = ([\d.]+)/));
const globalIncremental = Number(capture(constants, /\["SkillDamageIncrementalEffectiveness"\] = ([\d.]+)/));
const rowPattern = /\[(\d+)\] = \{ ([\d.]+), ([\d.]+), \d+, levelRequirement = (\d+), statInterpolation = \{ 3, 3, 1, \}/g;
const rows = [...skill.matchAll(rowPattern)].map((match) => {
  const [level, minimumWeight, maximumWeight, requirementLevel] = match.slice(1).map(Number);
  const actorOffset = requirementLevel - 1;
  // PoB's effectiveness interpolation applied at this gem row's requirement.
  const effectiveness = (globalBase + globalIncremental * actorOffset)
    * base * (1 + incremental) ** actorOffset;
  return {
    level,
    requirementLevel,
    flatMin: Math.round(effectiveness * minimumWeight),
    flatMax: Math.round(effectiveness * maximumWeight),
  };
});

const officialAnchors = [
  { level: 1, requirementLevel: 34, flatMin: 36, flatMax: 54 },
  { level: 20, requirementLevel: 70, flatMin: 219, flatMax: 329 },
];
const mechanics = { maximumLifePercent, goldenGloryLightRadiusPercent };
const updated = {
  ...table,
  mechanics,
  tableBounds: { minimumLevel: 1, maximumLevel: rows.length, rowCount: rows.length },
  compactAnchors: officialAnchors,
  rows,
};

const previousRows = new Map(table.rows.map((row) => [row.level, row]));
const nextRows = new Map(rows.map((row) => [row.level, row]));
const report = {
  verifiedLevels: rows.length,
  addedLevels: rows.filter((row) => !previousRows.has(row.level)).map((row) => row.level),
  removedLevels: table.rows.filter((row) => !nextRows.has(row.level)).map((row) => row.level),
  changedLevels: rows
    .filter((row) => previousRows.has(row.level) && !isDeepStrictEqual(previousRows.get(row.level), row))
    .map((row) => ({ previous: previousRows.get(row.level), next: row })),
  changedMechanics: isDeepStrictEqual(table.mechanics, mechanics) ? null : { previous: table.mechanics, next: mechanics },
  changedAvailability: !isDeepStrictEqual(table.tableBounds, updated.tableBounds),
  requiresReview: [],
};
if (rows.length !== 40 || rows.some((row, index) => row.level !== index + 1 || row.flatMin > row.flatMax)) {
  report.requiresReview.push("Expected 40 ascending Flame Link rows with valid damage ranges.");
}
if (officialAnchors.some((anchor) => !isDeepStrictEqual(anchor, nextRows.get(anchor.level)))) {
  report.requiresReview.push("Pinned rows disagree with the GGG patch-note damage anchors.");
}
if (maximumLifePercent !== 3 || goldenGloryLightRadiusPercent !== 50) {
  report.requiresReview.push("Pinned Flame Link or Golden Glory coefficients disagree with the GGG patch notes.");
}
console.log(JSON.stringify(report, null, 2));
const unchanged = isDeepStrictEqual(table, updated);
if (report.requiresReview.length > 0 || (!write && !unchanged)) {
  process.exitCode = 1;
} else if (write && !unchanged) {
  await writeFile(tablePath, JSON.stringify(updated, null, 2) + "\n");
}
