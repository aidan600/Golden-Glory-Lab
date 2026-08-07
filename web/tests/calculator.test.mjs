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
  assert.equal(result.flameLinkMin, 671);
  assert.equal(result.flameLinkMax, 830);
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
  assert.equal(result.flameLinkMin, 1692);
  assert.equal(result.flameLinkMax, 1988);
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
  assert.equal(result.enmityPenetration, 170);
  assert.equal(result.enmityError, null);
});

test("D. Enmity cap at 200", () => {
  const result = evaluateManualCalculator(fields(), levelTable);
  assert.equal(result.finalUncappedFireResistance, "320");
  assert.equal(result.overcappedFireResistance, "235");
  assert.equal(result.enmityPenetration, 200);
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

  assert.equal(breakdown.addJewel(), true);
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

  // Apply Total semantics: total lexeme is what Calculator field receives.
  const applied = breakdown.total().formatNetPct();
  assert.equal(applied, "15");

  breakdown.reset();
  assert.equal(breakdown.jewels.length, INITIAL_JEWEL_COUNT);
  assert.ok(breakdown.total().isZero());
  for (const name of FIXED_LIGHT_RADIUS_SLOTS) {
    assert.ok(breakdown.slots[name].isZero());
  }
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
  assert.equal(result.linkEffectMultiplier, "1.31");
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
  assert.equal(result.flameLinkMin, 3878);
  assert.equal(result.flameLinkMax, 4423);
  assert.equal(result.preEnmityFireResistance, "687");
  assert.equal(result.finalUncappedFireResistance, "274");
  assert.equal(result.overcappedFireResistance, "196");
  assert.equal(result.enmityPenetration, 196);
});
