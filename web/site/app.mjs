/**
 * Golden Glory Calculator — browser UI shell.
 * Relative module/asset paths for GitHub Pages project hosting.
 */

import {
  Dec,
  FIXED_LIGHT_RADIUS_SLOTS,
  INITIAL_JEWEL_COUNT,
  LightRadiusBreakdown,
  compareFlameLink,
  defaultManualCalculatorInput,
  evaluateManualCalculator,
  parseDecimalText,
  parseFlameLinkLevelTable,
} from "./calculator.mjs?v=3.30.0";

const DASH = "\u2014";
const ASSET = "./assets/icons";

const SLOT_ICONS = {
  Helmet: "helmet.png",
  "Body Armour": "body_armour.png",
  Boots: "boots.png",
  "Main Hand": "main_hand.png",
  "Off Hand": "off_hand.png",
  Amulet: "amulet.png",
  "Ring 1": "ring.png",
  "Ring 2": "ring.png",
  Belt: "belt.png",
  "Passive Tree / Ascendancy": "passive_tree.png",
  "Other / Misc": "other.png",
};

const els = {
  tabs: [...document.querySelectorAll(".tab")],
  viewCalculator: document.getElementById("view-calculator"),
  viewBreakdown: document.getElementById("view-breakdown"),
  maximumLife: document.getElementById("maximum-life"),
  lightRadius: document.getElementById("light-radius"),
  otherLink: document.getElementById("other-link"),
  flameLinkLevel: document.getElementById("flame-link-level"),
  goldenGlory: document.getElementById("golden-glory"),
  powerfulBond: document.getElementById("powerful-bond"),
  inspiringBond: document.getElementById("inspiring-bond"),
  gearFireRes: document.getElementById("gear-fire-res"),
  auraFireRes: document.getElementById("aura-fire-res"),
  enmityReduced: document.getElementById("enmity-reduced"),
  maximumFireRes: document.getElementById("maximum-fire-res"),
  enmityEquipped: document.getElementById("enmity-equipped"),
  preEnmityDisplay: document.getElementById("pre-enmity-display"),
  finalUncappedDisplay: document.getElementById("final-uncapped-display"),
  overcappedDisplay: document.getElementById("overcapped-display"),
  enmitySectionError: document.getElementById("enmity-section-error"),
  resultNetEffect: document.getElementById("result-net-effect"),
  resultMultiplier: document.getElementById("result-multiplier"),
  resultFlameLink: document.getElementById("result-flame-link"),
  resultEnmity: document.getElementById("result-enmity"),
  flameError: document.getElementById("flame-error"),
  flameGameVersion: document.getElementById("flame-game-version"),
  flameMaximumLifePercent: document.getElementById("flame-maximum-life-percent"),
  goldenGloryLightRadiusPercent: document.getElementById(
    "golden-glory-light-radius-percent",
  ),
  compareFlameLink: document.getElementById("compare-flame-link"),
  flameComparison: document.getElementById("flame-comparison"),
  comparisonStatus: document.getElementById("flame-comparison-status"),
  comparisonResults: document.getElementById("flame-comparison-results"),
  previousDamage: document.getElementById("flame-damage-329"),
  currentDamage: document.getElementById("flame-damage-330"),
  previousMultiplier: document.getElementById("flame-multiplier-329"),
  currentMultiplier: document.getElementById("flame-multiplier-330"),
  minimumChange: document.getElementById("flame-change-min"),
  maximumChange: document.getElementById("flame-change-max"),
  enmityError: document.getElementById("enmity-error"),
  btnResetCalculator: document.getElementById("btn-reset-calculator"),
  slotRows: document.getElementById("slot-rows"),
  jewelRows: document.getElementById("jewel-rows"),
  btnAddJewel: document.getElementById("btn-add-jewel"),
  breakdownTotal: document.getElementById("breakdown-total"),
  btnApplyTotal: document.getElementById("btn-apply-total"),
  btnResetBreakdown: document.getElementById("btn-reset-breakdown"),
};

/** @type {ReturnType<typeof parseFlameLinkLevelTable> | null} */
let levelTable = null;
/** @type {ReturnType<typeof parseFlameLinkLevelTable> | null} */
let previousLevelTable = null;
let loadingPreviousTable = false;
const breakdown = new LightRadiusBreakdown();
/** @type {HTMLInputElement[]} */
let slotInputs = [];
/** @type {{ input: HTMLInputElement, removeBtn: HTMLButtonElement | null }[]} */
let jewelControls = [];

function setError(node, message) {
  if (!message) {
    node.hidden = true;
    node.textContent = "";
    return;
  }
  node.hidden = false;
  node.textContent = message;
}

function readCalculatorFields() {
  return {
    maximumLife: els.maximumLife.value,
    increasedLightRadiusPct: els.lightRadius.value,
    otherLinkSkillBuffEffectPct: els.otherLink.value,
    flameLinkLevel: els.flameLinkLevel.value,
    goldenGloryAllocated: els.goldenGlory.checked,
    powerfulBondActive: els.powerfulBond.checked,
    inspiringBondActive: els.inspiringBond.checked,
    totalFireResistanceOnGear: els.gearFireRes.value,
    luminaryAuraFireResistance: els.auraFireRes.value,
    enmityReducedFireResistance: els.enmityReduced.value,
    maximumFireResistance: els.maximumFireRes.value,
    enmityEquipped: els.enmityEquipped.checked,
  };
}

function writeCalculatorFields(fields) {
  els.maximumLife.value = fields.maximumLife;
  els.lightRadius.value = fields.increasedLightRadiusPct;
  els.otherLink.value = fields.otherLinkSkillBuffEffectPct;
  els.flameLinkLevel.value = fields.flameLinkLevel;
  els.goldenGlory.checked = fields.goldenGloryAllocated;
  els.powerfulBond.checked = fields.powerfulBondActive;
  els.inspiringBond.checked = fields.inspiringBondActive;
  els.gearFireRes.value = fields.totalFireResistanceOnGear;
  els.auraFireRes.value = fields.luminaryAuraFireResistance;
  els.enmityReduced.value = fields.enmityReducedFireResistance;
  els.maximumFireRes.value = fields.maximumFireResistance;
  els.enmityEquipped.checked = fields.enmityEquipped;
}

function flameDamageRange(result) {
  return result.flameLinkMin == null || result.flameLinkMax == null
    ? DASH
    : `${result.flameLinkMin}-${result.flameLinkMax}`;
}

function multiplierText(multiplier) {
  return multiplier == null ? DASH : `${multiplier}x`;
}

function comparisonChangeText(change) {
  if (change == null) return DASH;
  const amount = `${change.amount > 0n ? "+" : ""}${change.amount}`;
  const percent = change.percent == null
    ? DASH
    : `${Number(change.percent) > 0 ? "+" : ""}${change.percent}%`;
  return `${amount} (${percent})`.replaceAll("-", "\u2212");
}

function renderFlameLinkComparison(fields, current) {
  const visible = els.compareFlameLink.checked;
  els.flameComparison.hidden = !visible;
  if (!visible) return;

  if (!previousLevelTable) {
    els.comparisonResults.hidden = true;
    els.comparisonStatus.textContent = loadingPreviousTable
      ? "Loading 3.29 Flame Link data…"
      : "Could not load 3.29 data. Turn the comparison off and on to retry.";
    return;
  }

  const { previous, minimumChange, maximumChange } = compareFlameLink(
    fields,
    previousLevelTable,
    current,
  );
  const hasDamage = previous.flameLinkMin != null || current.flameLinkMin != null;
  els.comparisonResults.hidden = !hasDamage;
  if (!hasDamage) {
    els.comparisonStatus.textContent = "Check the Flame Link inputs to compare damage.";
    return;
  }

  els.previousDamage.textContent = flameDamageRange(previous);
  els.currentDamage.textContent = flameDamageRange(current);
  els.previousMultiplier.textContent = multiplierText(previous.linkEffectMultiplier);
  els.currentMultiplier.textContent = multiplierText(current.linkEffectMultiplier);
  els.minimumChange.textContent = comparisonChangeText(minimumChange);
  els.maximumChange.textContent = comparisonChangeText(maximumChange);

  let status = "";
  if (previous.flameLinkError) {
    status = `3.29 result unavailable. ${previous.flameLinkError}`;
  } else if (current.flameLinkError) {
    status = "3.30 result unavailable. Check the Flame Link inputs.";
  } else if (minimumChange?.percent === null || maximumChange?.percent === null) {
    status = "A percentage change requires nonzero 3.29 damage.";
  }
  els.comparisonStatus.textContent = status;
}

function recalculate() {
  if (!levelTable) return;
  const fields = readCalculatorFields();
  const result = evaluateManualCalculator(fields, levelTable);

  els.resultNetEffect.textContent = result.netLinkSkillBuffEffectPct != null
    ? `${result.netLinkSkillBuffEffectPct}%`
    : DASH;
  els.resultMultiplier.textContent = multiplierText(result.linkEffectMultiplier);
  els.resultFlameLink.textContent = flameDamageRange(result);
  setError(els.flameError, result.flameLinkError);
  renderFlameLinkComparison(fields, result);

  els.preEnmityDisplay.textContent = `Pre-Enmity Fire Resistance: ${
    result.preEnmityFireResistance != null
      ? `${result.preEnmityFireResistance}%`
      : DASH
  }`;
  els.finalUncappedDisplay.textContent = `Final Uncapped Fire Resistance: ${
    result.finalUncappedFireResistance != null
      ? `${result.finalUncappedFireResistance}%`
      : DASH
  }`;
  els.overcappedDisplay.textContent = `Overcapped Fire Resistance: ${
    result.overcappedFireResistance != null
      ? `${result.overcappedFireResistance}%`
      : DASH
  }`;

  if (result.enmityPenetration != null) {
    els.resultEnmity.textContent = `${result.enmityPenetration.toString()}%`;
    setError(els.enmityError, null);
    setError(els.enmitySectionError, null);
  } else {
    els.resultEnmity.textContent = DASH;
    setError(els.enmityError, result.enmityError);
    setError(els.enmitySectionError, result.enmityError);
  }
}

function switchView(view) {
  const isCalc = view === "calculator";
  els.viewCalculator.hidden = !isCalc;
  els.viewBreakdown.hidden = isCalc;
  els.viewCalculator.classList.toggle("is-active", isCalc);
  els.viewBreakdown.classList.toggle("is-active", !isCalc);
  for (const tab of els.tabs) {
    const active = tab.dataset.view === view;
    tab.classList.toggle("is-active", active);
    tab.setAttribute("aria-selected", active ? "true" : "false");
  }
}

function parseBreakdownValue(text) {
  const trimmed = String(text ?? "").trim();
  if (!trimmed) return Dec.zero();
  try {
    return parseDecimalText(trimmed).value;
  } catch {
    return null;
  }
}

function syncBreakdownFromInputs() {
  for (let i = 0; i < FIXED_LIGHT_RADIUS_SLOTS.length; i++) {
    const name = FIXED_LIGHT_RADIUS_SLOTS[i];
    const parsed = parseBreakdownValue(slotInputs[i].value);
    breakdown.slots[name] = parsed ?? Dec.zero();
  }
  for (let i = 0; i < jewelControls.length; i++) {
    const parsed = parseBreakdownValue(jewelControls[i].input.value);
    breakdown.jewels[i] = parsed ?? Dec.zero();
  }
  const total = breakdown.total();
  els.breakdownTotal.textContent = `${total.formatNetPct()}%`;
}

function createSlotRow(name) {
  const row = document.createElement("div");
  row.className = "field-row has-icon";
  const iconName = SLOT_ICONS[name];
  const icon = document.createElement("img");
  icon.className = "slot-icon";
  icon.src = `${ASSET}/${iconName}`;
  icon.alt = "";
  icon.width = 18;
  icon.height = 18;
  const label = document.createElement("label");
  const id = `slot-${name.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}`;
  label.htmlFor = id;
  label.textContent = name;
  const input = document.createElement("input");
  input.id = id;
  input.type = "text";
  input.inputMode = "decimal";
  input.autocomplete = "off";
  input.spellcheck = false;
  input.value = "0";
  input.addEventListener("input", syncBreakdownFromInputs);
  const suffix = document.createElement("span");
  suffix.className = "suffix";
  suffix.textContent = "%";
  row.append(icon, label, input, suffix);
  return { row, input };
}

function createJewelRow(index, removable) {
  const wrap = document.createElement("div");
  wrap.className = "jewel-row-wrap";
  const row = document.createElement("div");
  row.className = "field-row has-icon";
  const icon = document.createElement("img");
  icon.className = "slot-icon";
  icon.src = `${ASSET}/jewel.png`;
  icon.alt = "";
  icon.width = 18;
  icon.height = 18;
  const label = document.createElement("label");
  const id = `jewel-${index + 1}`;
  label.htmlFor = id;
  label.textContent = `Jewel ${index + 1}`;
  const input = document.createElement("input");
  input.id = id;
  input.type = "text";
  input.inputMode = "decimal";
  input.autocomplete = "off";
  input.spellcheck = false;
  input.value = "0";
  input.addEventListener("input", syncBreakdownFromInputs);
  const suffix = document.createElement("span");
  suffix.className = "suffix";
  suffix.textContent = "%";
  row.append(icon, label, input, suffix);
  wrap.append(row);

  let removeBtn = null;
  if (removable) {
    removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "btn-remove-jewel";
    removeBtn.textContent = "Remove";
    removeBtn.addEventListener("click", () => removeJewelAt(index));
    wrap.append(removeBtn);
  }
  return { wrap, input, removeBtn };
}

function renderSlots() {
  els.slotRows.replaceChildren();
  slotInputs = [];
  for (const name of FIXED_LIGHT_RADIUS_SLOTS) {
    const { row, input } = createSlotRow(name);
    els.slotRows.append(row);
    slotInputs.push(input);
  }
}

function renderJewels() {
  els.jewelRows.replaceChildren();
  jewelControls = [];
  for (let i = 0; i < breakdown.jewels.length; i++) {
    const removable = i >= INITIAL_JEWEL_COUNT;
    const { wrap, input, removeBtn } = createJewelRow(i, removable);
    const lexeme = breakdown.jewels[i].formatNetPct();
    input.value = lexeme;
    els.jewelRows.append(wrap);
    jewelControls.push({ input, removeBtn });
  }
}

function removeJewelAt(index) {
  breakdown.removeJewel(index);
  renderJewels();
  syncBreakdownFromInputs();
}

function addJewel() {
  breakdown.addJewel();
  renderJewels();
  syncBreakdownFromInputs();
  jewelControls[jewelControls.length - 1]?.input.focus();
}

function applyBreakdownTotal() {
  syncBreakdownFromInputs();
  const total = breakdown.total();
  els.lightRadius.value = total.formatNetPct();
  switchView("calculator");
  recalculate();
  els.lightRadius.focus();
}

function resetCalculator() {
  writeCalculatorFields(defaultManualCalculatorInput());
  els.compareFlameLink.checked = false;
  recalculate();
}

function resetBreakdown() {
  breakdown.reset();
  for (let i = 0; i < slotInputs.length; i++) {
    slotInputs[i].value = "0";
  }
  renderJewels();
  syncBreakdownFromInputs();
}

function bindEvents() {
  for (const tab of els.tabs) {
    tab.addEventListener("click", () => switchView(tab.dataset.view));
  }

  const textInputs = [
    els.maximumLife,
    els.lightRadius,
    els.otherLink,
    els.flameLinkLevel,
    els.gearFireRes,
    els.auraFireRes,
    els.enmityReduced,
    els.maximumFireRes,
  ];
  for (const input of textInputs) {
    input.addEventListener("input", recalculate);
  }
  for (const box of [
    els.goldenGlory,
    els.powerfulBond,
    els.inspiringBond,
    els.enmityEquipped,
  ]) {
    box.addEventListener("change", recalculate);
  }
  els.compareFlameLink.addEventListener("change", toggleFlameLinkComparison);

  els.btnResetCalculator.addEventListener("click", resetCalculator);
  els.btnAddJewel.addEventListener("click", addJewel);
  els.btnApplyTotal.addEventListener("click", applyBreakdownTotal);
  els.btnResetBreakdown.addEventListener("click", resetBreakdown);
}

async function loadFlameLinkTable(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Failed to load Flame Link level table (${response.status})`);
  }
  return parseFlameLinkLevelTable(await response.json());
}

async function toggleFlameLinkComparison() {
  if (els.compareFlameLink.checked && !previousLevelTable && !loadingPreviousTable) {
    loadingPreviousTable = true;
    recalculate();
    try {
      previousLevelTable = await loadFlameLinkTable(
        "./data/flame-link-level-table-v1.json?v=3.30.0",
      );
    } catch (error) {
      console.error(error);
    } finally {
      loadingPreviousTable = false;
    }
  }
  recalculate();
}

async function main() {
  levelTable = await loadFlameLinkTable("./data/flame-link-level-table-v2.json");
  els.flameGameVersion.textContent = levelTable.gameVersion;
  els.flameMaximumLifePercent.textContent =
    `${levelTable.maximumLifePercent.toLexeme()}%`;
  els.goldenGloryLightRadiusPercent.textContent =
    `${levelTable.goldenGloryLightRadiusPercent.toLexeme()}%`;
  renderSlots();
  renderJewels();
  bindEvents();
  resetCalculator();
  syncBreakdownFromInputs();
  const params = new URLSearchParams(window.location.search);
  const initialView =
    params.get("view") === "breakdown" ? "breakdown" : "calculator";
  switchView(initialView);
}

main().catch((error) => {
  console.error(error);
  document.body.insertAdjacentHTML(
    "afterbegin",
    `<p style="padding:1rem;color:#9a3b2a;font-family:sans-serif">
      Calculator failed to load: ${String(error.message || error)}
    </p>`,
  );
});
