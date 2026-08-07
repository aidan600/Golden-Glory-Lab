/**
 * WEB-001 regression tests for the browser calculator seam.
 * Run: node --test web/tests/calculator.test.mjs
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

import {
  Dec,
  FIXED_LIGHT_RADIUS_SLOTS,
  INITIAL_JEWEL_COUNT,
  LightRadiusBreakdown,
  evaluateManualCalculator,
  parseDecimalText,
  parseFlameLinkLevelTable,
} from "../site/calculator.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const tableJson = JSON.parse(
  readFileSync(
    join(__dirname, "../site/data/flame-link-level-table-v1.json"),
    "utf8",
  ),
);
const levelTable = parseFlameLinkLevelTable(tableJson);

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

test("A. Flame Link known vector", () => {
  const result = evaluateManualCalculator(fields(), levelTable);
  assert.equal(result.flameLinkError, null);
  assert.equal(result.netLinkSkillBuffEffectPct, "40");
  assert.equal(result.linkEffectMultiplier, "1.40");
  assert.equal(result.flameLinkMin, 671n);
  assert.equal(result.flameLinkMax, 830n);
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
  assert.equal(result.netLinkSkillBuffEffectPct, "160");
  assert.equal(result.linkEffectMultiplier, "2.60");
  assert.equal(result.flameLinkMin, 1692n);
  assert.equal(result.flameLinkMax, 1988n);
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
  assert.equal(base.netLinkSkillBuffEffectPct, "40");
  assert.equal(powerful.netLinkSkillBuffEffectPct, "60");
  assert.equal(inspiring.netLinkSkillBuffEffectPct, "60");
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
  assert.equal(result.netLinkSkillBuffEffectPct, "30.5");
  // Exact multiplier 1.305; desktop Decimal.quantize("0.01") is HALF_EVEN → 1.30
  assert.equal(result.linkEffectMultiplier, "1.30");
  assert.equal(result.flameLinkMin, 625n);
  assert.equal(result.flameLinkMax, 774n);
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
  assert.equal(blanked.netLinkSkillBuffEffectPct, "40");
  assert.equal(blanked.linkEffectMultiplier, "1.40");
  assert.equal(blanked.flameLinkMin, 671n);
  assert.equal(blanked.flameLinkMax, 830n);
});

test("H3. Multiplier display uses HALF_EVEN (not HALF_UP)", () => {
  // 1.305 → hundredths digit even → stays 1.30
  assert.equal(Dec.fromString("1.305").formatMultiplier(), "1.30");
  // 1.315 → hundredths digit odd → rounds to 1.32
  assert.equal(Dec.fromString("1.315").formatMultiplier(), "1.32");
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
  assert.equal(result.netLinkSkillBuffEffectPct, "254");
  assert.equal(result.linkEffectMultiplier, "3.54");
  assert.equal(result.flameLinkMin, 3878n);
  assert.equal(result.flameLinkMax, 4423n);
  assert.equal(result.preEnmityFireResistance, "687");
  assert.equal(result.finalUncappedFireResistance, "274");
  assert.equal(result.overcappedFireResistance, "196");
  assert.equal(result.enmityPenetration, 196n);
});
