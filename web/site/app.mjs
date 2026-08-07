/**
 * Golden Glory Calculator — browser UI shell.
 * Relative module/asset paths for GitHub Pages project hosting.
 */

import {
  Dec,
  FIXED_LIGHT_RADIUS_SLOTS,
  INITIAL_JEWEL_COUNT,
  LightRadiusBreakdown,
  MAXIMUM_JEWEL_ROWS,
  defaultManualCalculatorInput,
  evaluateManualCalculator,
  parseDecimalText,
  parseFlameLinkLevelTable,
} from "./calculator.mjs";

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

/** Populated sample matching the owner's accepted desktop screenshots. */
const SAMPLE_CALCULATOR = {
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
};

const SAMPLE_BREAKDOWN_SLOTS = {
  Helmet: "76",
  "Body Armour": "0",
  Boots: "0",
  "Main Hand": "50",
  "Off Hand": "0",
  Amulet: "68",
  "Ring 1": "15",
  "Ring 2": "15",
  Belt: "0",
  "Passive Tree / Ascendancy": "30",
  "Other / Misc": "0",
};

const SAMPLE_JEWELS = ["0", "0", "0"];

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
  enmityError: document.getElementById("enmity-error"),
  btnResetCalculator: document.getElementById("btn-reset-calculator"),
  slotRows: document.getElementById("slot-rows"),
  jewelRows: document.getElementById("jewel-rows"),
  btnAddJewel: document.getElementById("btn-add-jewel"),
  breakdownTotal: document.getElementById("breakdown-total"),
  btnApplyTotal: document.getElementById("btn-apply-total"),
  btnResetBreakdown: document.getElementById("btn-reset-breakdown"),
};

/** @type {{ rows: Map, minimumLevel: number, maximumLevel: number } | null} */
let levelTable = null;
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

function recalculate() {
  if (!levelTable) return;
  const result = evaluateManualCalculator(readCalculatorFields(), levelTable);

  if (result.flameLinkError && result.netLinkSkillBuffEffectPct == null) {
    els.resultNetEffect.textContent = DASH;
    els.resultMultiplier.textContent = DASH;
    els.resultFlameLink.textContent = DASH;
    setError(els.flameError, result.flameLinkError);
  } else {
    els.resultNetEffect.textContent =
      result.netLinkSkillBuffEffectPct != null
        ? `${result.netLinkSkillBuffEffectPct}%`
        : DASH;
    els.resultMultiplier.textContent =
      result.linkEffectMultiplier != null
        ? `${result.linkEffectMultiplier}x`
        : DASH;
    if (result.flameLinkMin != null && result.flameLinkMax != null) {
      els.resultFlameLink.textContent = `${result.flameLinkMin}-${result.flameLinkMax}`;
      setError(els.flameError, null);
    } else {
      els.resultFlameLink.textContent = DASH;
      setError(els.flameError, result.flameLinkError);
    }
  }

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
    els.resultEnmity.textContent = `${result.enmityPenetration}%`;
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
  els.btnAddJewel.disabled = breakdown.jewels.length >= MAXIMUM_JEWEL_ROWS;
}

function removeJewelAt(index) {
  breakdown.removeJewel(index);
  renderJewels();
  syncBreakdownFromInputs();
}

function addJewel() {
  if (!breakdown.addJewel()) return;
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

function loadSampleData() {
  writeCalculatorFields(SAMPLE_CALCULATOR);
  for (let i = 0; i < FIXED_LIGHT_RADIUS_SLOTS.length; i++) {
    const name = FIXED_LIGHT_RADIUS_SLOTS[i];
    slotInputs[i].value = SAMPLE_BREAKDOWN_SLOTS[name] ?? "0";
  }
  breakdown.reset();
  for (let i = 0; i < SAMPLE_JEWELS.length; i++) {
    breakdown.jewels[i] = Dec.fromString(SAMPLE_JEWELS[i]);
  }
  renderJewels();
  syncBreakdownFromInputs();
  recalculate();
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

  els.btnResetCalculator.addEventListener("click", resetCalculator);
  els.btnAddJewel.addEventListener("click", addJewel);
  els.btnApplyTotal.addEventListener("click", applyBreakdownTotal);
  els.btnResetBreakdown.addEventListener("click", resetBreakdown);
}

async function main() {
  const response = await fetch("./data/flame-link-level-table-v1.json");
  if (!response.ok) {
    throw new Error(`Failed to load Flame Link level table (${response.status})`);
  }
  levelTable = parseFlameLinkLevelTable(await response.json());
  renderSlots();
  renderJewels();
  bindEvents();
  loadSampleData();
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
