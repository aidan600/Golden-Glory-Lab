/**
 * WEB-001 regression tests for the browser calculator seam.
 * Run: node --test web/tests/calculator.test.mjs
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import {
  Dec,
  FIXED_LIGHT_RADIUS_SLOTS,
  INITIAL_JEWEL_COUNT,
  LightRadiusBreakdown,
  compareFlameLink,
  evaluateManualCalculator,
  parseDecimalText,
  parseFlameLinkLevelTable,
} from "../site/calculator.mjs";

function loadLevelTable(version) {
  const url = new URL(`../site/data/flame-link-level-table-${version}.json`, import.meta.url);
  return parseFlameLinkLevelTable(JSON.parse(readFileSync(url, "utf8")));
}

const levelTable = loadLevelTable("v2");
const previousLevelTable = loadLevelTable("v1");

function fields(overrides = {}) {
  return {
    maximumLife: "5000",
    increasedLightRadiusPct: "40",
    otherLinkSkillBuffEffectPct: "0",
    flameLinkLevel: "23",
    goldenGloryAllocated: true,
    powerfulBondActive: false,
    inspiringBondActive: false,
    totalFireResistanceOnGear: "300",
    luminaryAuraFireResistance: "100",
    enmityReducedFireResistance: "20",
    maximumFireResistance: "85",
    enmityEquipped: true,
    ...overrides,
  };
}

test("The bundled 3.30 table records current mechanics and flat damage anchors", () => {
  assert.equal(levelTable.gameVersion, "Path of Exile 1 3.30.0");
  assert.equal(levelTable.maximumLifePercent.toLexeme(), "3");
  assert.equal(levelTable.goldenGloryLightRadiusPercent.toLexeme(), "50");
  assert.equal(levelTable.minimumLevel, 1);
  assert.equal(levelTable.maximumLevel, 40);
  assert.equal(levelTable.rows.size, 40);
  const anchors = [[1, "36", "54"], [20, "219", "329"], [40, "823", "1235"]];
  for (const [level, min, max] of anchors) {
    const row = levelTable.rows.get(level);
    assert.equal(row.flatMin.toLexeme(), min);
    assert.equal(row.flatMax.toLexeme(), max);
  }
});

test("A. Flame Link known vector", () => {
  const result = evaluateManualCalculator(fields(), levelTable);
  assert.equal(result.flameLinkError, null);
  assert.equal(result.netLinkSkillBuffEffectPct, "20");
  assert.equal(result.linkEffectMultiplier, "1.20");
  assert.equal(result.flameLinkMin, 526n);
  assert.equal(result.flameLinkMax, 698n);
});

test("Flame Link comparison uses the same loadout and the 3.29 damage as baseline", () => {
  const input = fields({ increasedLightRadiusPct: "100", flameLinkLevel: "20" });
  const current = evaluateManualCalculator(input, levelTable);
  const comparison = compareFlameLink(input, previousLevelTable, current);
  assert.equal(previousLevelTable.gameVersion, "Path of Exile 1 3.29.1");
  assert.equal(comparison.previous.linkEffectMultiplier, "2.00");
  assert.deepEqual([comparison.previous.flameLinkMin, comparison.previous.flameLinkMax], [838n, 1008n]);
  assert.equal(current.linkEffectMultiplier, "1.50");
  assert.deepEqual([current.flameLinkMin, current.flameLinkMax], [554n, 719n]);
  assert.deepEqual(comparison.minimumChange, { amount: -284n, percent: "-33.9" });
  assert.deepEqual(comparison.maximumChange, { amount: -289n, percent: "-28.7" });
});

test("Flame Link comparison reports gains when the higher 3.30 base dominates", () => {
  const input = fields({ maximumLife: "0", flameLinkLevel: "1", goldenGloryAllocated: false });
  const current = evaluateManualCalculator(input, levelTable);
  const comparison = compareFlameLink(input, previousLevelTable, current);
  assert.deepEqual(comparison.minimumChange, { amount: 13n, percent: "56.5" });
  assert.deepEqual(comparison.maximumChange, { amount: 19n, percent: "54.3" });
});

test("Flame Link comparison with zero baseline omits percentage changes", () => {
  const input = fields({ maximumLife: "0", flameLinkLevel: "1", increasedLightRadiusPct: "-100" });
  const current = evaluateManualCalculator(input, levelTable);
  const comparison = compareFlameLink(input, previousLevelTable, current);
  assert.deepEqual(comparison.minimumChange, { amount: 18n, percent: null });
  assert.deepEqual(comparison.maximumChange, { amount: 27n, percent: null });
});

test("Flame Link comparison with an unsupported baseline withholds both changes", () => {
  const input = fields({ increasedLightRadiusPct: "-120" });
  const current = evaluateManualCalculator(input, levelTable);
  const comparison = compareFlameLink(input, previousLevelTable, current);
  assert.equal(current.flameLinkError, null);
  assert.equal(comparison.previous.flameLinkError, "Link Effect Multiplier below zero is unsupported");
  assert.equal(comparison.minimumChange, null);
  assert.equal(comparison.maximumChange, null);
});

test("B. Larger Flame Link vector", () => {
  const result = evaluateManualCalculator(
    fields({
      maximumLife: "8432",
      increasedLightRadiusPct: "120",
      otherLinkSkillBuffEffectPct: "40",
    }),
    levelTable,
  );
  assert.equal(result.flameLinkError, null);
  assert.equal(result.netLinkSkillBuffEffectPct, "100");
  assert.equal(result.linkEffectMultiplier, "2.00");
  assert.equal(result.flameLinkMin, 1082n);
  assert.equal(result.flameLinkMax, 1370n);
});

test("C. Enmity truncation regression", () => {
  const result = evaluateManualCalculator(
    fields({
      totalFireResistanceOnGear: "633",
      luminaryAuraFireResistance: "0",
      enmityReducedFireResistance: "61",
      maximumFireResistance: "76",
    }),
    levelTable,
  );
  assert.equal(result.preEnmityFireResistance, "633");
  assert.equal(result.finalUncappedFireResistance, "246");
  assert.equal(result.overcappedFireResistance, "170");
  assert.equal(result.enmityPenetration, 170n);
  assert.equal(result.enmityError, null);
});

test("D. Enmity cap at 200", () => {
  const result = evaluateManualCalculator(fields(), levelTable);
  assert.equal(result.finalUncappedFireResistance, "320");
  assert.equal(result.overcappedFireResistance, "235");
  assert.equal(result.enmityPenetration, 200n);
});

test("E. Golden Glory off excludes Light Radius", () => {
  const result = evaluateManualCalculator(
    fields({ goldenGloryAllocated: false }),
    levelTable,
  );
  assert.equal(result.netLinkSkillBuffEffectPct, "0");
  assert.equal(result.linkEffectMultiplier, "1.00");
});

test("F. Bonds each add +20 percentage points", () => {
  const base = evaluateManualCalculator(fields(), levelTable);
  const powerful = evaluateManualCalculator(
    fields({ powerfulBondActive: true }),
    levelTable,
  );
  const inspiring = evaluateManualCalculator(
    fields({ inspiringBondActive: true }),
    levelTable,
  );
  assert.equal(base.netLinkSkillBuffEffectPct, "20");
  assert.equal(powerful.netLinkSkillBuffEffectPct, "40");
  assert.equal(inspiring.netLinkSkillBuffEffectPct, "40");
});

test("G. Light Radius Breakdown behavior", () => {
  const breakdown = new LightRadiusBreakdown();
  assert.equal(FIXED_LIGHT_RADIUS_SLOTS.length, 11);
  assert.equal(breakdown.jewels.length, INITIAL_JEWEL_COUNT);
  assert.ok(breakdown.total().isZero());

  breakdown.addJewel();
  assert.equal(breakdown.jewels.length, INITIAL_JEWEL_COUNT + 1);
  assert.equal(breakdown.canRemoveJewel(INITIAL_JEWEL_COUNT), true);
  assert.equal(breakdown.canRemoveJewel(0), false);

  breakdown.slots["Helmet"] = Dec.fromString("10");
  breakdown.jewels[0] = Dec.fromString("5");
  breakdown.jewels[INITIAL_JEWEL_COUNT] = Dec.fromString("7");
  assert.equal(breakdown.total().toLexeme(), "22");

  breakdown.removeJewel(INITIAL_JEWEL_COUNT);
  assert.equal(breakdown.jewels.length, INITIAL_JEWEL_COUNT);
  assert.equal(breakdown.total().toLexeme(), "15");

  const applied = breakdown.total().formatNetPct();
  assert.equal(applied, "15");

  breakdown.reset();
  assert.equal(breakdown.jewels.length, INITIAL_JEWEL_COUNT);
  assert.ok(breakdown.total().isZero());
  for (const name of FIXED_LIGHT_RADIUS_SLOTS) {
    assert.ok(breakdown.slots[name].isZero());
  }
});

test("G2. More than 10 jewel rows allowed", () => {
  const breakdown = new LightRadiusBreakdown();
  for (let i = 0; i < 12; i++) {
    breakdown.addJewel();
  }
  assert.equal(breakdown.jewels.length, INITIAL_JEWEL_COUNT + 12);
  breakdown.jewels[10] = Dec.fromString("3");
  breakdown.jewels[14] = Dec.fromString("4");
  assert.equal(breakdown.total().toLexeme(), "7");
  assert.equal(breakdown.canRemoveJewel(10), true);
  breakdown.removeJewel(10);
  assert.equal(breakdown.jewels.length, INITIAL_JEWEL_COUNT + 11);
  assert.equal(breakdown.total().toLexeme(), "4");
  breakdown.reset();
  assert.equal(breakdown.jewels.length, INITIAL_JEWEL_COUNT);
});

test("H. Signed and fractional parsing accepted", () => {
  const signed = parseDecimalText("-12.5");
  assert.equal(signed.lexeme, "-12.5");
  assert.equal(signed.value.toLexeme(), "-12.5");

  const fractional = parseDecimalText("3.75");
  assert.equal(fractional.lexeme, "3.75");

  const result = evaluateManualCalculator(
    fields({
      increasedLightRadiusPct: "40.5",
      otherLinkSkillBuffEffectPct: "-10",
      goldenGloryAllocated: true,
    }),
    levelTable,
  );
  assert.equal(result.flameLinkError, null);
  assert.equal(result.netLinkSkillBuffEffectPct, "10.25");
  assert.equal(result.linkEffectMultiplier, "1.10");
  assert.equal(result.flameLinkMin, 483n);
  assert.equal(result.flameLinkMax, 642n);
});

test("Golden Glory applies half a net Light Radius reduction", () => {
  const result = evaluateManualCalculator(
    fields({
      maximumLife: "0",
      flameLinkLevel: "20",
      increasedLightRadiusPct: "-50.5",
    }),
    levelTable,
  );
  assert.equal(result.flameLinkError, null);
  assert.equal(result.netLinkSkillBuffEffectPct, "-25.25");
  assert.equal(result.linkEffectMultiplier, "0.75");
  assert.equal(result.flameLinkMin, 164n);
  assert.equal(result.flameLinkMax, 246n);
});

test("Flame Link rounds exact ties after applying the life component", () => {
  const result = evaluateManualCalculator(
    fields({
      maximumLife: "50",
      flameLinkLevel: "1",
      goldenGloryAllocated: false,
    }),
    levelTable,
  );
  assert.equal(result.flameLinkError, null);
  assert.equal(result.flameLinkMin, 38n);
  assert.equal(result.flameLinkMax, 56n);
});

test("H2. Blank Other Link Skill Buff Effect equals explicit 0", () => {
  const blanked = evaluateManualCalculator(
    fields({ otherLinkSkillBuffEffectPct: "" }),
    levelTable,
  );
  const explicit = evaluateManualCalculator(
    fields({ otherLinkSkillBuffEffectPct: "0" }),
    levelTable,
  );
  assert.equal(blanked.flameLinkError, null);
  assert.equal(blanked.netLinkSkillBuffEffectPct, explicit.netLinkSkillBuffEffectPct);
  assert.equal(blanked.linkEffectMultiplier, explicit.linkEffectMultiplier);
  assert.equal(blanked.flameLinkMin, explicit.flameLinkMin);
  assert.equal(blanked.flameLinkMax, explicit.flameLinkMax);
  assert.equal(blanked.netLinkSkillBuffEffectPct, "20");
  assert.equal(blanked.linkEffectMultiplier, "1.20");
  assert.equal(blanked.flameLinkMin, 526n);
  assert.equal(blanked.flameLinkMax, 698n);
});

test("H3. Multiplier display uses HALF_EVEN (not HALF_UP)", () => {
  // 1.305 → hundredths digit even → stays 1.30
  assert.equal(Dec.fromString("1.305").formatMultiplier(), "1.30");
  // 1.315 → hundredths digit odd → rounds to 1.32
  assert.equal(Dec.fromString("1.315").formatMultiplier(), "1.32");
  // Negative near-zero: sign must come from scaled coeff, not truncated whole=0.
  assert.equal(Dec.fromString("-0.006").formatMultiplier(), "-0.01");
  assert.equal(Dec.fromString("-0.005").formatMultiplier(), "-0.00");
  // Flame Link modelled damage remains HALF_UP (0.5 → up), independent of display.
  assert.equal(Dec.fromString("625.5").roundHalfUpInt(), 626n);
});

test("I. Exact /100 preserves >64 fractional digits", () => {
  // 70 significant fractional digits — old DIV_SCALE=64 would truncate.
  const frac = "1".repeat(70);
  assert.ok(frac.length > 64);
  const value = Dec.fromString(`0.${frac}`);
  assert.equal(value.scale, 70);
  const divided = value.divBy100();
  // Exact: scale increases by 2, coeff unchanged (no truncation).
  assert.equal(divided.coeff, value.coeff);
  assert.equal(divided.scale, 72);
  assert.equal(divided.toLexeme(), `0.00${frac}`);

  // Link Effect Multiplier path: net.divBy100() must keep all digits before quantize.
  const net = Dec.fromString(`40.${frac}`);
  const dividedNet = net.divBy100();
  assert.equal(dividedNet.coeff, net.coeff);
  assert.equal(dividedNet.scale, net.scale + 2);
  const multiplier = Dec.fromInt(1).add(dividedNet);
  assert.equal(multiplier.scale, 72);
  assert.notEqual(multiplier.coeff, Dec.fromString("0.40").add(Dec.fromInt(1)).coeff);
  // Display still quantizes to two decimals.
  assert.equal(multiplier.formatMultiplier(), "1.40");
});

test("J. Enmity beyond Number.MAX_SAFE_INTEGER stays exact", () => {
  const gear = "9007199254740993";
  const maximum = "9007199254740992";
  // IEEE-754 Number collapses both to the same value.
  assert.equal(Number(gear), Number(maximum));

  const result = evaluateManualCalculator(
    fields({
      totalFireResistanceOnGear: gear,
      luminaryAuraFireResistance: "0",
      enmityReducedFireResistance: "0",
      maximumFireResistance: maximum,
      enmityEquipped: true,
    }),
    levelTable,
  );
  assert.equal(result.finalUncappedFireResistance, "9007199254740993");
  assert.equal(result.overcappedFireResistance, "1");
  assert.equal(result.enmityPenetration, 1n);
  assert.equal(result.enmityError, null);
});

test("K. Link Effect Multiplier exactly 0 yields 0-0 Flame Link", () => {
  const result = evaluateManualCalculator(
    fields({
      increasedLightRadiusPct: "0",
      otherLinkSkillBuffEffectPct: "-100",
      goldenGloryAllocated: false,
    }),
    levelTable,
  );
  assert.equal(result.flameLinkError, null);
  assert.equal(result.linkEffectMultiplier, "0.00");
  assert.equal(result.flameLinkMin, 0n);
  assert.equal(result.flameLinkMax, 0n);
});

test("L. Link Effect Multiplier below 0 is unsupported", () => {
  const result = evaluateManualCalculator(
    fields({
      increasedLightRadiusPct: "0",
      otherLinkSkillBuffEffectPct: "-150",
      goldenGloryAllocated: false,
    }),
    levelTable,
  );
  assert.equal(result.flameLinkMin, null);
  assert.equal(result.flameLinkMax, null);
  assert.match(result.flameLinkError || "", /unsupported/i);
});

test("Owner screenshot sample vector", () => {
  const result = evaluateManualCalculator(
    fields({
      maximumLife: "15751",
      increasedLightRadiusPct: "254",
      otherLinkSkillBuffEffectPct: "0",
      flameLinkLevel: "26",
      goldenGloryAllocated: true,
      powerfulBondActive: false,
      inspiringBondActive: false,
      totalFireResistanceOnGear: "687",
      luminaryAuraFireResistance: "",
      enmityReducedFireResistance: "60",
      maximumFireResistance: "78",
      enmityEquipped: true,
    }),
    levelTable,
  );
  assert.equal(result.netLinkSkillBuffEffectPct, "127");
  assert.equal(result.linkEffectMultiplier, "2.27");
  assert.equal(result.flameLinkMin, 1928n);
  assert.equal(result.flameLinkMax, 2357n);
  assert.equal(result.preEnmityFireResistance, "687");
  assert.equal(result.finalUncappedFireResistance, "274");
  assert.equal(result.overcappedFireResistance, "196");
  assert.equal(result.enmityPenetration, 196n);
});
