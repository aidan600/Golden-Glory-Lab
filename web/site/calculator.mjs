/**
 * Manual Golden Glory Calculator — browser calculation seam.
 * Ports ordinary product behavior from manual_calculator.py / flame_link.py / enmity.py.
 * Exact decimal arithmetic via BigInt (no binary float in calculator math).
 */

const DECIMAL_RE = /^-?[0-9]+(?:\.[0-9]+)?$/;
const DECIMAL_DIGIT_LIMIT = 128;
const BOND_VALUE_PCT = "20";
const LIFE_COMPONENT_FRACTION = "0.05";
const ENMITY_CAP = 200n;
const MINIMUM_FLAME_LINK_LEVEL = 1;
const MAXIMUM_FLAME_LINK_LEVEL = 40;
const INITIAL_JEWEL_COUNT = 3;

export const FIXED_LIGHT_RADIUS_SLOTS = Object.freeze([
  "Helmet",
  "Body Armour",
  "Boots",
  "Main Hand",
  "Off Hand",
  "Amulet",
  "Ring 1",
  "Ring 2",
  "Belt",
  "Passive Tree / Ascendancy",
  "Other / Misc",
]);

export {
  INITIAL_JEWEL_COUNT,
  MINIMUM_FLAME_LINK_LEVEL,
  MAXIMUM_FLAME_LINK_LEVEL,
  ENMITY_CAP,
};

/** Exact decimal: value = coeff / 10^scale (coeff signed BigInt). */
export class Dec {
  constructor(coeff, scale = 0) {
    this.coeff = BigInt(coeff);
    this.scale = Number(scale);
    if (!Number.isInteger(this.scale) || this.scale < 0) {
      throw new Error("scale must be a nonnegative integer");
    }
    this._trimTrailingZeros();
  }

  static zero() {
    return new Dec(0n, 0);
  }

  static fromString(text) {
    if (typeof text !== "string") {
      throw new DecimalInputError(
        "DECIMAL_TEXT_TYPE",
        "Manual decimal input must be text",
      );
    }
    if (!DECIMAL_RE.test(text)) {
      throw new DecimalInputError(
        "DECIMAL_TEXT_GRAMMAR",
        "Manual decimal input does not match the exact ASCII decimal grammar",
      );
    }
    let digitCount = 0;
    for (const ch of text) {
      if (ch >= "0" && ch <= "9") digitCount += 1;
    }
    if (digitCount > DECIMAL_DIGIT_LIMIT) {
      throw new DecimalInputError(
        "DECIMAL_TEXT_DIGIT_LIMIT",
        `Manual decimal input exceeds the ${DECIMAL_DIGIT_LIMIT}-digit limit`,
      );
    }
    const neg = text.startsWith("-");
    const body = neg ? text.slice(1) : text;
    const dot = body.indexOf(".");
    let intPart;
    let fracPart;
    if (dot < 0) {
      intPart = body;
      fracPart = "";
    } else {
      intPart = body.slice(0, dot);
      fracPart = body.slice(dot + 1);
    }
    const digits = intPart + fracPart;
    let coeff = BigInt(digits || "0");
    if (neg) coeff = -coeff;
    return new Dec(coeff, fracPart.length);
  }

  static fromInt(n) {
    return new Dec(BigInt(n), 0);
  }

  _trimTrailingZeros() {
    while (this.scale > 0 && this.coeff % 10n === 0n) {
      this.coeff /= 10n;
      this.scale -= 1;
    }
  }

  _aligned(other) {
    const scale = Math.max(this.scale, other.scale);
    const a = this.coeff * pow10(BigInt(scale - this.scale));
    const b = other.coeff * pow10(BigInt(scale - other.scale));
    return { a, b, scale };
  }

  add(other) {
    const { a, b, scale } = this._aligned(other);
    return new Dec(a + b, scale);
  }

  sub(other) {
    const { a, b, scale } = this._aligned(other);
    return new Dec(a - b, scale);
  }

  mul(other) {
    return new Dec(this.coeff * other.coeff, this.scale + other.scale);
  }

  /**
   * Exact division by 100 for percentage conversion.
   * value/100 = coeff / 10^(scale+2) — no truncation.
   */
  divBy100() {
    return new Dec(this.coeff, this.scale + 2);
  }

  neg() {
    return new Dec(-this.coeff, this.scale);
  }

  isNegative() {
    return this.coeff < 0n;
  }

  isZero() {
    return this.coeff === 0n;
  }

  cmp(other) {
    const { a, b } = this._aligned(other);
    if (a < b) return -1;
    if (a > b) return 1;
    return 0;
  }

  eq(other) {
    return this.cmp(other) === 0;
  }

  isIntegral() {
    return this.scale === 0;
  }

  /** Truncate fractional part toward zero (PoB-style ROUND_DOWN for resistance). */
  truncateTowardZero() {
    if (this.scale === 0) return new Dec(this.coeff, 0);
    const q = this.coeff / pow10(BigInt(this.scale));
    return new Dec(q, 0);
  }

  /**
   * Nearest-integer HALF-UP as BigInt (ties away from zero for nonnegative).
   * Matches flame_link.round_half_up for nonnegative modelled outputs.
   */
  roundHalfUpInt() {
    if (this.isNegative()) {
      throw new Error("roundHalfUpInt supports nonnegative modelled outputs only");
    }
    if (this.scale === 0) return this.coeff;
    const factor = pow10(BigInt(this.scale));
    const whole = this.coeff / factor;
    const frac = this.coeff % factor;
    const roundUp = frac * 2n >= factor;
    return roundUp ? whole + 1n : whole;
  }

  /**
   * Quantize to hundredths with ROUND_HALF_EVEN (Python Decimal default),
   * matching manual_calculator._format_multiplier display only.
   */
  quantize2() {
    const cents = this._roundHalfEvenCents();
    return new Dec(cents, 2);
  }

  /**
   * Banker's rounding of value×100 to an integer BigInt (signed).
   * Ties (.5 exactly) round to the even hundredths digit.
   * Rounding direction uses the scaled coefficient's sign so values in
   * (-0.01, 0) are not mis-rounded after truncation to whole=0.
   * Used only for Link Effect Multiplier display — not Flame Link damage.
   */
  _roundHalfEvenCents() {
    const scaled = this.mul(Dec.fromString("100"));
    if (scaled.scale === 0) {
      return scaled.coeff;
    }
    const factor = pow10(BigInt(scaled.scale));
    const whole = scaled.coeff / factor; // truncates toward zero
    const rem = scaled.coeff % factor;
    const absRem = rem < 0n ? -rem : rem;
    const twice = absRem * 2n;
    const negative = scaled.coeff < 0n;
    if (twice < factor) {
      return whole;
    }
    if (twice > factor) {
      return negative ? whole - 1n : whole + 1n;
    }
    // Exact tie: round to even.
    if (whole % 2n === 0n) {
      return whole;
    }
    return negative ? whole - 1n : whole + 1n;
  }

  toLexeme() {
    const neg = this.coeff < 0n;
    let digits = (neg ? -this.coeff : this.coeff).toString();
    if (this.scale === 0) {
      return (neg ? "-" : "") + digits;
    }
    while (digits.length <= this.scale) {
      digits = "0" + digits;
    }
    const split = digits.length - this.scale;
    let frac = digits.slice(split);
    let intPart = digits.slice(0, split);
    frac = frac.replace(/0+$/, "");
    const body = frac.length ? `${intPart}.${frac}` : intPart;
    return (neg ? "-" : "") + body;
  }

  formatNetPct() {
    return this.toLexeme();
  }

  /** Always two decimal places with HALF_EVEN (desktop Decimal.quantize("0.01")). */
  formatMultiplier() {
    const cents = this._roundHalfEvenCents();
    // Preserve Python signed-zero display for negative values that quantize to 0.
    const neg = cents < 0n || (cents === 0n && this.isNegative());
    let digits = (cents < 0n ? -cents : cents).toString();
    while (digits.length < 3) digits = "0" + digits;
    const split = digits.length - 2;
    const body = `${digits.slice(0, split)}.${digits.slice(split)}`;
    return (neg ? "-" : "") + body;
  }
}

function pow10(n) {
  let r = 1n;
  for (let i = 0n; i < n; i++) r *= 10n;
  return r;
}

export class DecimalInputError extends Error {
  constructor(code, message) {
    super(message);
    this.code = code;
    this.message = message;
    this.name = "DecimalInputError";
  }
}

export function parseDecimalText(text) {
  const value = Dec.fromString(text);
  return { lexeme: text, value, integral: value.isIntegral() };
}

function blank(text) {
  return !String(text ?? "").trim();
}

function parseOptionalDecimal(text) {
  if (blank(text)) return { value: null, error: null };
  try {
    return { value: Dec.fromString(String(text).trim()), error: null };
  } catch (err) {
    if (err instanceof DecimalInputError) {
      return { value: null, error: "Enter a valid number" };
    }
    throw err;
  }
}

/**
 * Exact overcap/contribution from integral BigInt uncapped and maximum.
 * overcap = max(0, U - M); contribution = min(200, overcap).
 */
export function enmityOvercapContribution(uncapped, maximum) {
  const u = typeof uncapped === "bigint" ? uncapped : BigInt(uncapped);
  const m = typeof maximum === "bigint" ? maximum : BigInt(maximum);
  const overcap = u > m ? u - m : 0n;
  const contribution = overcap < ENMITY_CAP ? overcap : ENMITY_CAP;
  return { overcap, contribution };
}

function formatResistancePct(value) {
  return value.toLexeme();
}

/**
 * @param {object} tableJson
 * @returns {{ rows: Map<number,{flatMin:Dec, flatMax:Dec}>, minimumLevel:number, maximumLevel:number }}
 */
export function parseFlameLinkLevelTable(tableJson) {
  const rows = new Map();
  for (const raw of tableJson.rows) {
    rows.set(raw.level, {
      flatMin: Dec.fromInt(raw.flatMin),
      flatMax: Dec.fromInt(raw.flatMax),
    });
  }
  return {
    rows,
    minimumLevel: tableJson.tableBounds.minimumLevel,
    maximumLevel: tableJson.tableBounds.maximumLevel,
  };
}

export function defaultManualCalculatorInput() {
  return {
    maximumLife: "",
    increasedLightRadiusPct: "",
    otherLinkSkillBuffEffectPct: "",
    flameLinkLevel: "",
    goldenGloryAllocated: false,
    powerfulBondActive: false,
    inspiringBondActive: false,
    totalFireResistanceOnGear: "",
    luminaryAuraFireResistance: "",
    enmityReducedFireResistance: "",
    maximumFireResistance: "",
    enmityEquipped: false,
  };
}

function evaluateFlameLinkSection(fields, levelTable) {
  if (blank(fields.maximumLife)) {
    return emptyFlame("Enter Maximum Life");
  }
  const lifeP = parseOptionalDecimal(fields.maximumLife);
  if (lifeP.error) return emptyFlame(lifeP.error);
  if (lifeP.value.isNegative()) {
    return emptyFlame("Maximum Life must be nonnegative");
  }

  if (blank(fields.increasedLightRadiusPct)) {
    return emptyFlame("Enter Increased Light Radius Modifier");
  }
  const lightP = parseOptionalDecimal(fields.increasedLightRadiusPct);
  if (lightP.error) return emptyFlame(lightP.error);

  let other;
  if (blank(fields.otherLinkSkillBuffEffectPct)) {
    other = Dec.zero();
  } else {
    const otherP = parseOptionalDecimal(fields.otherLinkSkillBuffEffectPct);
    if (otherP.error) return emptyFlame(otherP.error);
    other = otherP.value;
  }

  if (blank(fields.flameLinkLevel)) {
    return emptyFlame("Enter a Flame Link level from 1 to 40");
  }
  const levelP = parseOptionalDecimal(fields.flameLinkLevel);
  if (levelP.error) return emptyFlame(levelP.error);
  if (!levelP.value.isIntegral()) {
    return emptyFlame("Enter a Flame Link level from 1 to 40");
  }
  const level = Number(levelP.value.coeff);
  if (level < MINIMUM_FLAME_LINK_LEVEL || level > MAXIMUM_FLAME_LINK_LEVEL) {
    return emptyFlame("Enter a Flame Link level from 1 to 40");
  }

  const gg = fields.goldenGloryAllocated ? lightP.value : Dec.zero();
  const direct = other;
  let conditional = Dec.zero();
  if (fields.powerfulBondActive) {
    conditional = conditional.add(Dec.fromString(BOND_VALUE_PCT));
  }
  if (fields.inspiringBondActive) {
    conditional = conditional.add(Dec.fromString(BOND_VALUE_PCT));
  }

  const net = gg.add(direct).add(conditional);
  const one = Dec.fromInt(1);
  const multiplier = one.add(net.divBy100());

  if (multiplier.isNegative()) {
    return {
      netLinkSkillBuffEffectPct: net.formatNetPct(),
      linkEffectMultiplier: multiplier.formatMultiplier(),
      flameLinkMin: null,
      flameLinkMax: null,
      flameLinkError: "Link Effect Multiplier below zero is unsupported",
    };
  }

  const effectiveLevel = level;
  if (
    effectiveLevel < levelTable.minimumLevel ||
    effectiveLevel > levelTable.maximumLevel
  ) {
    return emptyFlame(
      "Effective Flame Link level is outside the supported 1-40 table",
    );
  }
  const row = levelTable.rows.get(effectiveLevel);
  if (!row) {
    return emptyFlame("Unable to calculate Flame Link result");
  }

  const lifeComponent = lifeP.value.mul(Dec.fromString(LIFE_COMPONENT_FRACTION));
  const unscaledMin = row.flatMin.add(lifeComponent);
  const unscaledMax = row.flatMax.add(lifeComponent);
  const exactMin = unscaledMin.mul(multiplier);
  const exactMax = unscaledMax.mul(multiplier);

  let modelledMin;
  let modelledMax;
  if (multiplier.isZero()) {
    modelledMin = 0n;
    modelledMax = 0n;
  } else {
    modelledMin = exactMin.roundHalfUpInt();
    modelledMax = exactMax.roundHalfUpInt();
  }

  return {
    netLinkSkillBuffEffectPct: net.formatNetPct(),
    linkEffectMultiplier: multiplier.formatMultiplier(),
    flameLinkMin: modelledMin,
    flameLinkMax: modelledMax,
    flameLinkError: null,
  };
}

function emptyFlame(error) {
  return {
    netLinkSkillBuffEffectPct: null,
    linkEffectMultiplier: null,
    flameLinkMin: null,
    flameLinkMax: null,
    flameLinkError: error,
  };
}

function evaluateEnmitySection(fields) {
  const gearBlank = blank(fields.totalFireResistanceOnGear);
  if (gearBlank) {
    if (fields.enmityEquipped) {
      return emptyEnmity("Enter Total Fire Resistance on Gear");
    }
    return emptyEnmity(null);
  }

  const gearP = parseOptionalDecimal(fields.totalFireResistanceOnGear);
  if (gearP.error) return emptyEnmity(gearP.error);

  let aura;
  if (blank(fields.luminaryAuraFireResistance)) {
    aura = Dec.zero();
  } else {
    const auraP = parseOptionalDecimal(fields.luminaryAuraFireResistance);
    if (auraP.error) return emptyEnmity(auraP.error);
    aura = auraP.value;
  }

  const preEnmity = gearP.value.add(aura);
  const preText = formatResistancePct(preEnmity);

  if (!fields.enmityEquipped) {
    return {
      preEnmityFireResistance: preText,
      finalUncappedFireResistance: preText,
      overcappedFireResistance: null,
      enmityPenetration: null,
      enmityError: null,
    };
  }

  if (blank(fields.enmityReducedFireResistance)) {
    return {
      preEnmityFireResistance: preText,
      finalUncappedFireResistance: null,
      overcappedFireResistance: null,
      enmityPenetration: null,
      enmityError: "Enter Enmity Reduced Fire Resistance",
    };
  }
  const redP = parseOptionalDecimal(fields.enmityReducedFireResistance);
  if (redP.error) {
    return {
      preEnmityFireResistance: preText,
      finalUncappedFireResistance: null,
      overcappedFireResistance: null,
      enmityPenetration: null,
      enmityError: redP.error,
    };
  }

  if (blank(fields.maximumFireResistance)) {
    return {
      preEnmityFireResistance: preText,
      finalUncappedFireResistance: null,
      overcappedFireResistance: null,
      enmityPenetration: null,
      enmityError: "Enter Maximum Fire Resistance",
    };
  }
  const maxP = parseOptionalDecimal(fields.maximumFireResistance);
  if (maxP.error) {
    return {
      preEnmityFireResistance: preText,
      finalUncappedFireResistance: null,
      overcappedFireResistance: null,
      enmityPenetration: null,
      enmityError: maxP.error,
    };
  }

  // raw = pre * (1 - reduction/100) — exact /100 via scale shift
  const one = Dec.fromInt(1);
  const factor = one.sub(redP.value.divBy100());
  const rawFinal = preEnmity.mul(factor);
  const finalUncapped = rawFinal.truncateTowardZero();
  const maximumTrunc = maxP.value.truncateTowardZero();
  const { overcap, contribution } = enmityOvercapContribution(
    finalUncapped.coeff,
    maximumTrunc.coeff,
  );

  return {
    preEnmityFireResistance: preText,
    finalUncappedFireResistance: formatResistancePct(finalUncapped),
    overcappedFireResistance: formatResistancePct(Dec.fromInt(overcap)),
    enmityPenetration: contribution,
    enmityError: null,
  };
}

function emptyEnmity(error) {
  return {
    preEnmityFireResistance: null,
    finalUncappedFireResistance: null,
    overcappedFireResistance: null,
    enmityPenetration: null,
    enmityError: error,
  };
}

export function evaluateManualCalculator(fields, levelTable) {
  const flame = evaluateFlameLinkSection(fields, levelTable);
  const enmity = evaluateEnmitySection(fields);
  return {
    ...flame,
    ...enmity,
  };
}

export class LightRadiusBreakdown {
  constructor() {
    this.slots = {};
    for (const name of FIXED_LIGHT_RADIUS_SLOTS) {
      this.slots[name] = Dec.zero();
    }
    this.jewels = Array.from({ length: INITIAL_JEWEL_COUNT }, () => Dec.zero());
  }

  total() {
    let sum = Dec.zero();
    for (const name of FIXED_LIGHT_RADIUS_SLOTS) {
      sum = sum.add(this.slots[name] ?? Dec.zero());
    }
    for (const j of this.jewels) {
      sum = sum.add(j);
    }
    return sum;
  }

  addJewel() {
    this.jewels.push(Dec.zero());
  }

  canRemoveJewel(index) {
    return index >= INITIAL_JEWEL_COUNT && index >= 0 && index < this.jewels.length;
  }

  removeJewel(index) {
    if (!this.canRemoveJewel(index)) {
      throw new Error("Only dynamically added jewel rows can be removed");
    }
    this.jewels.splice(index, 1);
  }

  reset() {
    for (const name of FIXED_LIGHT_RADIUS_SLOTS) {
      this.slots[name] = Dec.zero();
    }
    this.jewels = Array.from({ length: INITIAL_JEWEL_COUNT }, () => Dec.zero());
  }
}
