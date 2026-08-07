/**
 * Approved synthetic sample used only by capture/viewport tooling.
 * Not loaded by production app.mjs startup.
 */

export const SAMPLE_CALCULATOR = {
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

export const SAMPLE_BREAKDOWN_SLOTS = {
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

export const SAMPLE_JEWELS = ["0", "0", "0"];

/** CDP Runtime.evaluate expression that fills the approved sample into the live page. */
export const POPULATE_SAMPLE_EXPRESSION = `(() => {
  const set = (id, value) => {
    const el = document.getElementById(id);
    el.value = value;
    el.dispatchEvent(new Event("input", { bubbles: true }));
  };
  const check = (id, on) => {
    const el = document.getElementById(id);
    el.checked = on;
    el.dispatchEvent(new Event("change", { bubbles: true }));
  };
  set("maximum-life", "15751");
  set("light-radius", "254");
  set("other-link", "0");
  set("flame-link-level", "26");
  check("golden-glory", true);
  check("powerful-bond", false);
  check("inspiring-bond", false);
  set("gear-fire-res", "687");
  set("aura-fire-res", "");
  set("enmity-reduced", "60");
  set("maximum-fire-res", "78");
  check("enmity-equipped", true);
  const slots = {
    "slot-helmet": "76",
    "slot-body-armour": "0",
    "slot-boots": "0",
    "slot-main-hand": "50",
    "slot-off-hand": "0",
    "slot-amulet": "68",
    "slot-ring-1": "15",
    "slot-ring-2": "15",
    "slot-belt": "0",
    "slot-passive-tree-ascendancy": "30",
    "slot-other-misc": "0",
  };
  for (const [id, value] of Object.entries(slots)) {
    set(id, value);
  }
  for (let i = 1; i <= 3; i++) {
    set("jewel-" + i, "0");
  }
  return {
    flame: document.getElementById("result-flame-link").textContent,
    total: document.getElementById("breakdown-total").textContent,
  };
})()`;
