#!/usr/bin/env node

/*
 * Validates the first-release evidence pack and its recorded safety gates.
 * It never calculates a live mechanic or accesses the network at runtime.
 */

import { existsSync, readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const auditIds = ["AUD-002", "AUD-003", "AUD-004", "AUD-005"];
const statuses = new Set(["confirmed", "supported", "provisional", "unknown", "superseded"]);
const ordinals = new Set(["supported", "confirmed"]);
const rank = new Map([["supported", 1], ["confirmed", 2]]);
const polarities = new Set(["positive-capability", "non-gating-fact", "product-policy", "limitation-or-gap"]);
const manifest = [
  ["data/curated/aud-002-mercenary-input-contract-v1.json", "aud-002-mercenary-input-contract-v1", "manual-input-contract", "AUD-002"],
  ["data/curated/aud-003-light-radius-passive-sources-v1.json", "aud-003-light-radius-passive-sources-v1", "source-catalog", "AUD-003"],
  ["data/curated/aud-003-light-radius-observed-stat-terms-v1.json", "aud-003-light-radius-observed-stat-terms-v1", "source-catalog", "AUD-003"],
  ["data/curated/aud-003-link-effect-passive-sources-v1.json", "aud-003-link-effect-passive-sources-v1", "source-catalog", "AUD-003"],
  ["data/curated/aud-003-link-effect-observed-stat-terms-v1.json", "aud-003-link-effect-observed-stat-terms-v1", "source-catalog", "AUD-003"],
  ["data/curated/aud-003-golden-glory-mechanic-v1.json", "aud-003-golden-glory-mechanic-v1", "mechanic-reference", "AUD-003"],
  ["data/curated/aud-004-flame-link-reference-v1.json", "aud-004-flame-link-reference-v1", "mechanic-reference", "AUD-004"],
  ["fixtures/mechanics/aud-004-flame-link-gates-v1.json", "aud-004-flame-link-gates-v1", "calculation-gate-fixture", "AUD-004"],
  ["data/curated/aud-005-enmitys-embrace-reference-v1.json", "aud-005-enmitys-embrace-reference-v1", "mechanic-reference", "AUD-005"],
  ["fixtures/mechanics/aud-005-enmitys-embrace-gates-v1.json", "aud-005-enmitys-embrace-gates-v1", "calculation-gate-fixture", "AUD-005"]
].map(([path, artifactId, artifactType, auditId]) => ({ path, artifactId, artifactType, auditId }));
const expectedRecordIds = new Map([
  [manifest[0].path, ["mercenary-final-uncapped-fire-resistance", "mercenary-maximum-fire-resistance", "mercenary-equipment-inclusion-state", "mercenary-measurement-context"]],
  [manifest[1].path, ["poe1-passive-node-27123", "poe1-passive-node-30675", "poe1-passive-node-35877", "poe1-passive-node-61133", "poe1-passive-node-63954", "poe1-passive-node-54694", "poe1-mastery-effect-51424"]],
  [manifest[2].path, ["poe1-trade-light-radius-explicit-1263695895", "poe1-trade-light-radius-implicit-1263695895", "poe1-trade-light-radius-fractured-1263695895", "poe1-trade-light-radius-enchant-1263695895", "poe1-trade-light-radius-scourge-1263695895", "poe1-trade-light-radius-during-effect-2745936267", "poe1-trade-light-radius-basis-explicit-3836017971", "poe1-trade-light-radius-basis-fractured-3836017971", "poe1-trade-light-radius-basis-crafted-3836017971", "poe1-helmet-corruption-light-radius-range"]],
  [manifest[3].path, ["poe1-passive-node-3089", "poe1-passive-node-57404", "poe1-passive-node-60145", "poe1-passive-node-60781", "poe1-passive-node-46471", "poe1-passive-node-15900"]],
  [manifest[4].path, ["poe1-trade-crucible-link-effect-15845", "poe1-trade-crucible-link-effect-47594", "poe1-trade-crucible-link-effect-41316", "poe1-trade-crucible-link-effect-48159", "poe1-trade-crucible-link-effect-41817", "poe1-trade-crucible-link-effect-45"]],
  [manifest[5].path, ["poe1-passive-node-31517"]],
  [manifest[6].path, ["poe1-flame-link-standard-reference", "poe1-flame-link-target-and-scaling-gate"]],
  [manifest[7].path, ["flame-link-level-one-recognition", "flame-link-level-twenty-recognition", "flame-link-exceptional-level-review", "flame-link-outside-source-level-range", "flame-link-quality-duration-separation", "flame-link-quality-variant-review", "flame-link-inactive-reporting-state", "flame-link-unknown-reporting-state", "flame-link-target-review-gate", "flame-link-missing-source-life-gate", "flame-link-fractional-life-rounding-gate", "flame-link-independent-source-states", "flame-link-powerful-bond-condition-gate", "flame-link-source-version-mismatch", "flame-link-scaling-dependency-gate"]],
  [manifest[8].path, ["poe1-enmitys-embrace-reference", "poe1-enmitys-embrace-manual-isolated-formula", "poe1-enmitys-embrace-input-and-aggregation-gates"]],
  [manifest[9].path, ["enmity-manual-no-overcap", "enmity-manual-one-point-overcap", "enmity-manual-item-cap", "enmity-manual-input-beyond-item-cap", "enmity-manual-nonpositive-overcap", "enmity-manual-missing-final-inputs", "enmity-target-reporting", "enmity-sheet-derived-inclusion-gate", "enmity-equipped-attestation-gate", "enmity-fractional-manual-gate", "enmity-observed-outside-reviewed-range"]]
]);

const isObject = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
const clone = (value) => JSON.parse(JSON.stringify(value));
const sameArray = (left, right) => Array.isArray(left) && Array.isArray(right) && left.length === right.length && left.every((value, index) => value === right[index]);
const sameValue = (left, right) => {
  if (left === right) return true;
  if (Array.isArray(left) || Array.isArray(right)) return Array.isArray(left) && Array.isArray(right) && left.length === right.length && left.every((value, index) => sameValue(value, right[index]));
  if (isObject(left) && isObject(right)) {
    const leftKeys = Object.keys(left).sort();
    const rightKeys = Object.keys(right).sort();
    return leftKeys.length === rightKeys.length && leftKeys.every((key, index) => key === rightKeys[index] && sameValue(left[key], right[key]));
  }
  return false;
};
const record = (artifact, id) => artifact?.records?.find((entry) => entry.id === id);
const fail = (errors, message) => errors.push(message);
const claim = (inventories, claimId) => inventories.get(claimId?.split("-C")[0])?.get(claimId);

function createContext(overrides = {}) {
  const artifacts = new Map(Object.entries(overrides.artifacts || {}));
  const texts = new Map(Object.entries(overrides.texts || {}));
  const missing = new Set(overrides.missing || []);
  return {
    exists(path) {
      return !missing.has(path) && (artifacts.has(path) || texts.has(path) || existsSync(resolve(root, path)));
    },
    text(path) {
      if (missing.has(path)) throw new Error("missing " + path);
      if (texts.has(path)) return texts.get(path);
      if (artifacts.has(path)) return JSON.stringify(artifacts.get(path));
      return readFileSync(resolve(root, path), "utf8");
    },
    json(path) {
      return artifacts.has(path) ? clone(artifacts.get(path)) : JSON.parse(this.text(path));
    }
  };
}

function parseClaimInventories(context, errors) {
  const inventories = new Map();
  for (const auditId of auditIds) {
    const path = "docs/audits/" + auditId + ".md";
    let text;
    try {
      text = context.text(path);
    } catch {
      fail(errors, path + ": missing Claim inventory");
      continue;
    }
    const section = text.match(/^## Claim inventory\r?\n([\s\S]*?)(?=^## |\Z)/m);
    if (!section) {
      fail(errors, path + ": missing Claim inventory section");
      continue;
    }
    const inventory = new Map();
    for (const line of section[1].split(/\r?\n/)) {
      if (!line.startsWith("| \`AUD-")) continue;
      const fields = line.split("|").slice(1, -1).map((field) => field.trim());
      const id = fields[0]?.match(/^\`(AUD-00[2-5]-C\d{2})\`$/)?.[1];
      if (!id || fields.length < 4) {
        fail(errors, path + ": malformed Claim inventory row");
        continue;
      }
      const status = fields[2];
      const polarity = fields[3];
      if (inventory.has(id)) fail(errors, path + ": duplicate claim " + id);
      if (!statuses.has(status)) fail(errors, path + ": invalid status for " + id);
      if (!polarities.has(polarity)) fail(errors, path + ": invalid gate polarity for " + id);
      inventory.set(id, { status, polarity });
    }
    if (!inventory.size) fail(errors, path + ": Claim inventory contains no parseable claims");
    inventories.set(auditId, inventory);
  }
  return inventories;
}

function validateArtifactManifest(context, selectedAudit, sources, inventories, errors) {
  const artifacts = new Map();
  for (const entry of manifest.filter((candidate) => selectedAudit === undefined || candidate.auditId === selectedAudit)) {
    if (!context.exists(entry.path)) {
      fail(errors, entry.path + ": missing expected artifact for " + entry.auditId);
      continue;
    }
    let artifact;
    try {
      artifact = context.json(entry.path);
    } catch (error) {
      fail(errors, entry.path + ": invalid JSON: " + error.message);
      continue;
    }
    artifacts.set(entry.path, artifact);
    for (const [key, expected] of [["artifactId", entry.artifactId], ["artifactType", entry.artifactType], ["auditId", entry.auditId], ["contractVersion", "1.0.0"], ["targetGameVersion", "Path of Exile 1 3.29.1"]]) {
      if (artifact[key] !== expected) fail(errors, entry.path + ": " + key + " must be " + expected);
    }
    if (!statuses.has(artifact.verificationStatus)) fail(errors, entry.path + ": invalid verificationStatus");
    if (!Array.isArray(artifact.sourceIds) || !artifact.sourceIds.length || new Set(artifact.sourceIds).size !== artifact.sourceIds.length) fail(errors, entry.path + ": sourceIds must be a nonempty unique manifest");
    for (const sourceId of artifact.sourceIds || []) if (!sources.has(sourceId)) fail(errors, entry.path + ": source ID is not registered: " + sourceId);
    if (!sameArray((artifact.records || []).map((entry) => entry.id), expectedRecordIds.get(entry.path))) fail(errors, entry.path + ": record IDs/count do not match the approved artifact contract");
    for (const item of artifact.records || []) {
      if (!statuses.has(item.verificationStatus)) fail(errors, entry.path + "#" + item.id + ": invalid record verificationStatus");
      for (const sourceId of item.sourceIds || []) {
        if (!sources.has(sourceId)) fail(errors, entry.path + "#" + item.id + ": record source is unregistered: " + sourceId);
        if (!artifact.sourceIds.includes(sourceId)) fail(errors, entry.path + "#" + item.id + ": record source is not declared by artifact sourceIds: " + sourceId);
      }
      for (const claimId of item.claimIds || []) if (!claim(inventories, claimId)) fail(errors, entry.path + "#" + item.id + ": claim is absent from its Claim inventory: " + claimId);
    }
  }
  return artifacts;
}

function validateCapability(dependency, location, inventories, errors) {
  if (!isObject(dependency)) {
    fail(errors, location + ": capability dependency is not an object");
    return { qualified: false };
  }
  for (const field of ["claimId", "contractVersion", "gateMode", "minimumStatus", "appliesWhen", "unmetBehavior"]) if (!Object.hasOwn(dependency, field)) fail(errors, location + ": missing capability dependency field " + field);
  if (dependency.gateMode !== "requires-positive-capability") fail(errors, location + ": capability dependency must use requires-positive-capability");
  if (!ordinals.has(dependency.minimumStatus)) fail(errors, location + ": minimumStatus must be supported or confirmed");
  if (dependency.contractVersion !== "1.0.0") fail(errors, location + ": dependency contractVersion must be 1.0.0");
  const target = claim(inventories, dependency.claimId);
  if (!target) fail(errors, location + ": dependency claim is absent from a Claim inventory: " + dependency.claimId);
  else if (target.polarity !== "positive-capability") fail(errors, location + ": ordinal dependency targets non-positive-capability claim " + dependency.claimId);
  return { claimId: dependency.claimId, qualified: Boolean(target && ordinals.has(dependency.minimumStatus) && rank.get(target.status) >= rank.get(dependency.minimumStatus)) };
}
function validatePolicy(policy, location, inventories, errors) {
  if (!isObject(policy)) {
    fail(errors, location + ": policy prerequisite is not an object");
    return { adopted: false };
  }
  for (const field of ["claimId", "contractVersion", "policyMode", "appliesWhen", "unmetBehavior"]) if (!Object.hasOwn(policy, field)) fail(errors, location + ": missing policy prerequisite field " + field);
  if (Object.hasOwn(policy, "minimumStatus")) fail(errors, location + ": policy prerequisite must not use ordinal minimumStatus");
  if (policy.policyMode !== "requires-adopted-policy") fail(errors, location + ": policy prerequisite must use requires-adopted-policy");
  const target = claim(inventories, policy.claimId);
  if (!target) fail(errors, location + ": policy claim is absent from a Claim inventory: " + policy.claimId);
  else if (target.polarity !== "product-policy") fail(errors, location + ": policy prerequisite must target a product-policy claim");
  return { claimId: policy.claimId, adopted: Boolean(target && ["supported", "confirmed"].includes(target.status)) };
}
function validateDependencies(value, location, inventories, errors) {
  if (Array.isArray(value)) {
    return value.flatMap((item, index) => validateDependencies(item, location + "[" + index + "]", inventories, errors));
  }
  if (!isObject(value)) return [];
  const states = [];
  for (const [key, child] of Object.entries(value)) {
    const childLocation = location + "." + key;
    if (key === "requiredPolicyClaims") {
      if (!Array.isArray(child) || !child.length) fail(errors, childLocation + ": requiredPolicyClaims must be a nonempty array");
      else states.push(...child.map((entry, index) => ({ type: "policy", ...validatePolicy(entry, childLocation + "[" + index + "]", inventories, errors) })));
    } else if (key.endsWith("Dependencies") || key === "blockingDependencies") {
      if (!Array.isArray(child) || !child.length) fail(errors, childLocation + ": capability dependency collection must be nonempty");
      else states.push(...child.map((entry, index) => ({ type: "capability", ...validateCapability(entry, childLocation + "[" + index + "]", inventories, errors) })));
    } else states.push(...validateDependencies(child, childLocation, inventories, errors));
  }
  return states;
}

function validateAud003(artifacts, errors) {
  const passive = artifacts.get(manifest[1].path);
  const passiveTuples = new Map([
    ["poe1-passive-node-27123", { nodeId: 27123, skillId: 27123, name: "Mercenary Life, Light Radius", ascendancyName: "Luminary", sourceType: "passive-node", statFamily: "light-radius", valuePercent: 5, sign: "increase", availability: "Default-tree" }],
    ["poe1-passive-node-30675", { nodeId: 30675, skillId: 30675, name: "Link Cast Speed, Light Radius", ascendancyName: "Luminary", sourceType: "passive-node", statFamily: "light-radius", valuePercent: 5, sign: "increase", availability: "Default-tree" }],
    ["poe1-passive-node-35877", { nodeId: 35877, skillId: 35877, name: "Mercenary Damage, Light Radius", ascendancyName: "Luminary", sourceType: "passive-node", statFamily: "light-radius", valuePercent: 5, sign: "increase", availability: "Default-tree" }],
    ["poe1-passive-node-61133", { nodeId: 61133, skillId: 61133, name: "Mercenary Life, Light Radius", ascendancyName: "Luminary", sourceType: "passive-node", statFamily: "light-radius", valuePercent: 5, sign: "increase", availability: "Default-tree" }],
    ["poe1-passive-node-63954", { nodeId: 63954, skillId: 63954, name: "Link Cast Speed, Light Radius", ascendancyName: "Luminary", sourceType: "passive-node", statFamily: "light-radius", valuePercent: 5, sign: "increase", availability: "Default-tree" }],
    ["poe1-passive-node-54694", { nodeId: 54694, skillId: 54694, name: "Light of Divinity", sourceType: "passive-node", statFamily: "light-radius", valuePercent: 10, sign: "increase", availability: "Default-tree" }],
    ["poe1-mastery-effect-51424", { masteryEffectId: 51424, masteryName: "Energy Shield Mastery", selectionNodeIds: [857, 3471, 6338, 10729, 18240, 27307], sourceType: "mastery-effect", statFamily: "light-radius", valuePercent: 30, sign: "increase", basisOverride: "energy-shield-instead-of-life", availability: "Default-tree" }]
  ]);
  for (const item of passive?.records || []) {
    const mastery = item.id === "poe1-mastery-effect-51424";
    const expectedClaims = mastery ? ["AUD-003-C03", "AUD-003-C05"] : ["AUD-003-C03"];
    if (!sameArray(item.claimIds, expectedClaims) || !sameArray(item.sourceIds, ["ggg-poe1-skilltree-export-3-29-1"]) || !sameValue(item.data, passiveTuples.get(item.id))) fail(errors, "AUD-003 Light Radius passive tuple is not canonical at " + item.id);
  }
  const observed = artifacts.get(manifest[2].path);
  for (const item of observed?.records || []) if (item.data?.offerAsImprovement !== false || item.data?.acceptedForObservedInstance !== true) fail(errors, "AUD-003 observed Light Radius boundary is not canonical at " + item.id);
  const direct = artifacts.get(manifest[3].path);
  const directTuples = new Map([
    ["poe1-passive-node-3089", { nodeId: 3089, skillId: 3089, name: "Link Effect", sourceType: "passive-node", statFamily: "direct-link-buff-effect", valuePercent: 5, sign: "increase", condition: "always-on-if-allocated", availability: "Default-tree" }],
    ["poe1-passive-node-57404", { nodeId: 57404, skillId: 57404, name: "Link Effect", sourceType: "passive-node", statFamily: "direct-link-buff-effect", valuePercent: 5, sign: "increase", condition: "always-on-if-allocated", availability: "Default-tree" }],
    ["poe1-passive-node-60145", { nodeId: 60145, skillId: 60145, name: "Link Effect", sourceType: "passive-node", statFamily: "direct-link-buff-effect", valuePercent: 5, sign: "increase", condition: "always-on-if-allocated", availability: "Default-tree" }],
    ["poe1-passive-node-60781", { nodeId: 60781, skillId: 60781, name: "Inspiring Bond", sourceType: "passive-node", statFamily: "direct-link-buff-effect", valuePercent: 20, sign: "increase", condition: { kind: "linked-recently", windowSeconds: 4, defaultState: "unknown" }, availability: "Default-tree" }],
    ["poe1-passive-node-46471", { nodeId: 46471, skillId: 46471, name: "Powerful Bond", sourceType: "passive-node", statFamily: "direct-link-buff-effect", valuePercent: 20, sign: "increase", condition: { kind: "half-link-duration-expired", thresholdPercent: 50, defaultState: "unknown" }, availability: "Default-tree" }],
    ["poe1-passive-node-15900", { nodeId: 15900, skillId: 15900, name: "Oath of Fealty", sourceType: "related-condition-node", attachmentDuration: "infinite", directLinkBuffEffectPercent: null, availability: "Default-tree" }]
  ]);
  const directClaims = new Map([["poe1-passive-node-3089", ["AUD-003-C04"]], ["poe1-passive-node-57404", ["AUD-003-C04"]], ["poe1-passive-node-60145", ["AUD-003-C04"]], ["poe1-passive-node-60781", ["AUD-003-C04", "AUD-003-C09", "AUD-003-C12"]], ["poe1-passive-node-46471", ["AUD-003-C04", "AUD-003-C08"]], ["poe1-passive-node-15900", ["AUD-003-C08"]]]);
  for (const item of direct?.records || []) if (!sameArray(item.claimIds, directClaims.get(item.id)) || !sameArray(item.sourceIds, ["ggg-poe1-skilltree-export-3-29-1"]) || !sameValue(item.data, directTuples.get(item.id))) fail(errors, "AUD-003 direct Link tuple is not canonical at " + item.id);
  const golden = record(artifacts.get(manifest[5].path), "poe1-passive-node-31517");
  const data = golden?.data || {};
  if (!sameArray(golden?.claimIds, ["AUD-003-C02", "AUD-003-C12"]) || !sameArray(golden?.sourceIds, ["ggg-poe1-skilltree-export-3-29-1"]) || data.nodeId !== 31517 || data.skillId !== 31517 || data.name !== "Golden Glory" || data.targetKind !== "Mercenary" || data.literalEffect !== "Increases and Reductions to Light Radius also apply to Effect of your Link Skill Buffs on your Mercenary" || !["arithmetic", "stacking", "rounding", "cap"].every((key) => data[key] === "unknown")) fail(errors, "AUD-003 Golden Glory canonical facts are not exact");
}
function validateFlame(artifacts, inventories, errors) {
  const reference = artifacts.get(manifest[6].path);
  const fixture = artifacts.get(manifest[7].path);
  const standard = record(reference, "poe1-flame-link-standard-reference")?.data;
  const gate = record(reference, "poe1-flame-link-target-and-scaling-gate")?.data;
  if (standard?.gemMetadataId !== "Metadata/Items/Gems/SkillGemFlameLink" || standard?.grantedEffectId !== "FlameLink" || standard?.sourceDataVersion !== "Path of Exile 1 3.29.0" || standard?.versionState !== "supporting-source-version-mismatch" || standard?.ordinaryLevelRange?.minimum !== 1 || standard?.ordinaryLevelRange?.maximum !== 20 || standard?.components?.levelDerivedFlatFire?.minimumStatId !== "flame_link_minimum_fire_damage" || standard?.components?.levelDerivedFlatFire?.maximumStatId !== "flame_link_maximum_fire_damage" || standard?.components?.sourceMaximumLife?.statId !== "flame_link_added_fire_damage_from_life_%" || standard?.components?.sourceMaximumLife?.percent !== 5 || standard?.standardQuality?.millisecondsPerQuality !== 75 || standard?.standardQuality?.quality20AdditionalBaseDurationMilliseconds !== 1500) fail(errors, "AUD-004 Flame Link canonical reference facts are not exact");
  const compactAnchors = [{ level: 1, requirementLevel: 34, addedFireMinimum: 23, addedFireMaximum: 35 }, { level: 20, requirementLevel: 70, addedFireMinimum: 169, addedFireMaximum: 254 }];
  if (!sameValue(standard?.reproduction?.compactAnchors, compactAnchors)) fail(errors, "AUD-004 Flame Link compact anchors are not exact");
  const blockers = gate?.unconditionalBlockingDependencies || [];
  if (gate?.finalScaledResult !== "withheld" || gate?.unknownIsNotZero !== true || !sameArray(blockers.map((entry) => entry.claimId), ["AUD-003-C12", "AUD-004-C09", "AUD-004-C10"])) fail(errors, "AUD-004 definitive scaled Flame Link result must remain explicitly withheld");
  for (const [index, blocker] of blockers.entries()) if (validateCapability(blocker, "AUD-004 unconditional blocker[" + index + "]", inventories, errors).qualified) fail(errors, "AUD-004 lists a satisfied capability as an unresolved blocker: " + blocker.claimId);
  const fixtures = new Map((fixture?.records || []).map((entry) => [entry.id, entry.data]));
  const expected = [
    ["flame-link-level-one-recognition", (data) => data?.input?.level === 1 && data.expectedState === "recognized-ordinary" && data.expectedScaledGrant === "withheld-pending-scaling-evidence"],
    ["flame-link-level-twenty-recognition", (data) => data?.input?.level === 20 && data.expectedState === "recognized-ordinary"],
    ["flame-link-exceptional-level-review", (data) => data?.input?.level === 21 && data.expectedState === "needs-review"],
    ["flame-link-outside-source-level-range", (data) => sameArray(data?.inputCases?.map((entry) => entry.level), [0, 41]) && data.expectedState === "unsupported"],
    ["flame-link-quality-duration-separation", (data) => data?.input?.quality === 20 && data.expectedAdditionalBaseDurationMilliseconds === 1500 && data.expectedGrantedDamageConclusion === "not-established"],
    ["flame-link-inactive-reporting-state", (data) => data?.input?.linkState === "inactive" && data.expectedState === "inactive" && data.expectedNumericZero === false],
    ["flame-link-unknown-reporting-state", (data) => data?.input?.linkState === "unknown" && data.expectedState === "unavailable" && data.expectedNumericZero === false],
    ["flame-link-source-version-mismatch", (data) => data?.input?.targetVersion === "3.29.1" && data?.input?.sourceDataVersion === "3.29.0" && data.expectedState === "supporting-source-version-mismatch"],
    ["flame-link-scaling-dependency-gate", (data) => data?.expectedState === "scaled-result-withheld" && Array.isArray(data.unconditionalBlockingDependencies)]
  ];
  for (const [id, predicate] of expected) if (!predicate(fixtures.get(id))) fail(errors, "AUD-004 Flame Link fixture is not canonical at " + id);
}

function validateEnmity(artifacts, inventories, context, errors) {
  const reference = artifacts.get(manifest[8].path);
  const fixture = artifacts.get(manifest[9].path);
  const item = record(reference, "poe1-enmitys-embrace-reference")?.data;
  const formula = record(reference, "poe1-enmitys-embrace-manual-isolated-formula")?.data;
  const gate = record(reference, "poe1-enmitys-embrace-input-and-aggregation-gates")?.data;
  if (item?.sourceLocators?.developmentSnapshot?.commitSha !== "50d22365b919c7435b5d12d892875e9f61d11133" || item?.sourceLocators?.developmentSnapshot?.dynamicStatDescription !== "generated stat-description record 3043" || item?.sourceLocators?.pinnedExport?.commitSha !== "3a73a54bd3a9c92c4d3264c5d697a51b6c9063bc" || item?.sourceLocators?.pinnedExport?.dynamicStatDescription !== "generated stat-description record 3040") fail(errors, "AUD-005 Enmity source locators must be the verified development 3043 and export 3040 pair");
  if (formula?.formula?.overcap !== "max(0,U-M)" || formula?.formula?.enmityOwnFirePenetration !== "min(200,overcap)") fail(errors, "AUD-005 Enmity formula is not canonical");
  const capabilities = gate?.manualOutputCapabilityDependencies || [];
  const policies = gate?.requiredPolicyClaims || [];
  if (!sameArray(capabilities.map((entry) => entry.claimId), ["AUD-005-C03", "AUD-005-C04"])) fail(errors, "AUD-005 manual path must require only C03/C04 mechanics capabilities");
  if (!sameArray(policies.map((entry) => entry.claimId), ["AUD-002-C06"])) fail(errors, "AUD-005 manual path must name AUD-002-C06 as a separate policy prerequisite");
  const capabilityStates = capabilities.map((entry, index) => validateCapability(entry, "AUD-005 manual capability[" + index + "]", inventories, errors));
  const policyStates = policies.map((entry, index) => validatePolicy(entry, "AUD-005 manual policy[" + index + "]", inventories, errors));
  const attestation = record(fixture, "enmity-equipped-attestation-gate")?.data;
  if (!sameArray(attestation?.manualOutputCapabilityDependencies?.map((entry) => entry.claimId), ["AUD-005-C03", "AUD-005-C04"]) || !sameArray(attestation?.requiredPolicyClaims?.map((entry) => entry.claimId), ["AUD-002-C06"])) fail(errors, "AUD-005 fixture must mirror manual capability and policy prerequisites");
  if ((capabilityStates.some((entry) => !entry.qualified) || policyStates.some((entry) => !entry.adopted)) && fixture?.records?.some((entry) => entry.id.startsWith("enmity-manual-") && isObject(entry.data?.expected))) fail(errors, "AUD-005 presents manual numeric output despite an unsatisfied manual capability or policy prerequisite");
  for (const entry of fixture?.records || []) {
    const cases = entry.id === "enmity-manual-nonpositive-overcap" ? entry.data?.inputCases : entry.data?.input ? [entry.data.input] : [];
    if (!entry.id.startsWith("enmity-manual-") || !entry.data?.expected) continue;
    for (const input of cases) {
      if (!Number.isFinite(input?.U) || !Number.isFinite(input?.M)) continue;
      const overcap = Math.max(0, input.U - input.M);
      if (entry.data.expected.overcap !== overcap || entry.data.expected.enmityOwnFirePenetration !== Math.min(200, overcap)) fail(errors, entry.id + ": expected Enmity formula values are incorrect");
      if (Object.hasOwn(entry.data.expected, "inputBeyondCap") && entry.data.expected.inputBeyondCap !== Math.max(0, overcap - 200)) fail(errors, entry.id + ": expected Enmity cap excess is incorrect");
    }
  }
  for (const input of record(fixture, "enmity-target-reporting")?.data?.inputCases || []) if (input.expected && JSON.stringify(input.expected) !== JSON.stringify({ gap: Math.max(0, input.target - input.P_enmity), surplus: Math.max(0, input.P_enmity - input.target), capHeadroom: 200 - input.P_enmity })) fail(errors, "enmity-target-reporting: target metrics are not canonical");
  const observed = record(fixture, "enmity-observed-outside-reviewed-range")?.data?.input;
  if (observed?.rawItemText !== "123% reduced Fire Resistance; 777 Fire Damage when you use a Skill" || observed?.origin !== "synthetic-contract-fixture") fail(errors, "AUD-005 synthetic observed-value fixture is not canonical");
  for (const path of ["data/sources/registry.json", manifest[8].path, "docs/audits/AUD-005.md"]) if (context.exists(path) && context.text(path).includes("2919")) fail(errors, "AUD-005 stale Enmity locator 2919 remains in " + path);
}

function validateEvidencePack(context, selectedAudit) {
  const errors = [];
  const inventories = parseClaimInventories(context, errors);
  let registry;
  try {
    registry = context.json("data/sources/registry.json");
  } catch (error) {
    fail(errors, "data/sources/registry.json: invalid JSON: " + error.message);
    return { errors };
  }
  const artifacts = validateArtifactManifest(context, selectedAudit, new Set((registry.sources || []).map((entry) => entry.id)), inventories, errors);
  for (const [path, artifact] of artifacts) validateDependencies(artifact, path, inventories, errors);
  if (selectedAudit === undefined || selectedAudit === "AUD-003") validateAud003(artifacts, errors);
  if (selectedAudit === undefined || selectedAudit === "AUD-004") validateFlame(artifacts, inventories, errors);
  if (selectedAudit === undefined || selectedAudit === "AUD-005") validateEnmity(artifacts, inventories, context, errors);
  return { errors };
}

function changedArtifact(path, mutate) {
  const baseline = createContext();
  const artifact = baseline.json(path);
  mutate(artifact);
  return createContext({ artifacts: { [path]: artifact } });
}
function runSemanticMutationTests() {
  const failures = [];
  const reject = (name, context, fragment, audit) => {
    if (!validateEvidencePack(context, audit).errors.some((error) => error.includes(fragment))) failures.push(name + " was not rejected by validateEvidencePack: " + fragment);
  };
  reject("wrong artifact ID", changedArtifact(manifest[0].path, (item) => { item.artifactId = "wrong"; }), "artifactId must be");
  reject("wrong artifact type", changedArtifact(manifest[0].path, (item) => { item.artifactType = "source-catalog"; }), "artifactType must be");
  reject("missing selected artifact", createContext({ missing: [manifest[8].path] }), "missing expected artifact", "AUD-005");
  reject("claim outside Claim inventory", changedArtifact(manifest[0].path, (item) => { item.records[0].claimIds = ["AUD-002-C99"]; }), "claim is absent from its Claim inventory");
  reject("unregistered source", changedArtifact(manifest[0].path, (item) => { item.records[0].sourceIds = ["not-registered"]; }), "record source is unregistered");
  reject("record source absent from outer manifest", changedArtifact(manifest[0].path, (item) => { item.records[0].sourceIds = ["ggg-poe1-skilltree-export-3-29-1"]; }), "record source is not declared by artifact sourceIds");
  reject("non-capability ordinal gate", changedArtifact(manifest[6].path, (item) => { item.records[1].data.upstreamDependencies[0].claimId = "AUD-003-C06"; }), "ordinal dependency targets non-positive-capability");
  reject("invalid ordinal status", changedArtifact(manifest[6].path, (item) => { item.records[1].data.upstreamDependencies[0].minimumStatus = "unknown"; }), "minimumStatus must be supported or confirmed");
  reject("missing gate mode", changedArtifact(manifest[6].path, (item) => { delete item.records[1].data.upstreamDependencies[0].gateMode; }), "missing capability dependency field gateMode");
  reject("ordinal policy field", changedArtifact(manifest[8].path, (item) => { item.records[2].data.requiredPolicyClaims[0].minimumStatus = "supported"; }), "policy prerequisite must not use ordinal minimumStatus");
  reject("non-policy prerequisite", changedArtifact(manifest[8].path, (item) => { item.records[2].data.requiredPolicyClaims[0].claimId = "AUD-002-C03"; }), "policy prerequisite must target a product-policy claim");
  reject("supported capability promoted to confirmed", changedArtifact(manifest[8].path, (item) => { item.records[2].data.manualOutputCapabilityDependencies[0].minimumStatus = "confirmed"; }), "presents manual numeric output despite an unsatisfied");
  reject("stale Enmity locator", changedArtifact(manifest[8].path, (item) => { item.records[0].data.sourceLocators.developmentSnapshot.dynamicStatDescription = "generated stat-description record 2919"; }), "source locators must be");
  reject("arbitrary Enmity formula", changedArtifact(manifest[8].path, (item) => { item.records[1].data.formula.overcap = "U-M"; }), "formula is not canonical");
  reject("wrong Enmity expected value", changedArtifact(manifest[9].path, (item) => { item.records[1].data.expected.enmityOwnFirePenetration = 7; }), "expected Enmity formula values are incorrect");
  reject("wrong target metrics", changedArtifact(manifest[9].path, (item) => { item.records[6].data.inputCases[0].expected.gap = 1; }), "target metrics are not canonical");
  reject("synthetic observed fixture replacement", changedArtifact(manifest[9].path, (item) => { item.records[10].data.input.rawItemText = "real user item"; }), "synthetic observed-value fixture is not canonical");
  reject("released Flame Link scaling", changedArtifact(manifest[6].path, (item) => { item.records[1].data.finalScaledResult = "calculated"; }), "definitive scaled Flame Link result must remain explicitly withheld");
  reject("invalid Flame Link state", changedArtifact(manifest[7].path, (item) => { item.records[0].data.expectedState = "calculated-anyway"; }), "Flame Link fixture is not canonical");
  reject("wrong Golden Glory node", changedArtifact(manifest[5].path, (item) => { item.records[0].data.nodeId = 999; }), "Golden Glory canonical facts are not exact");
  reject("Light Radius five percent inflated", changedArtifact(manifest[1].path, (item) => { item.records[0].data.valuePercent = 500; }), "Light Radius passive tuple is not canonical");
  reject("Flame Link level-twenty compact anchor replaced", changedArtifact(manifest[6].path, (item) => { item.records[0].data.reproduction.compactAnchors[1].addedFireMinimum = 999; item.records[0].data.reproduction.compactAnchors[1].addedFireMaximum = 1000; }), "Flame Link compact anchors are not exact");
  return { count: 22, failures };
}

function discoverPython() {
  const candidates = process.env.PYTHON ? [process.env.PYTHON] : process.platform === "win32" ? ["py", "python", "python3"] : ["python3", "python"];
  const tried = [];
  for (const candidate of candidates) {
    const probe = spawnSync(candidate, ["--version"], { encoding: "utf8" });
    if (!probe.error && probe.status === 0) return { command: candidate, tried };
    tried.push(candidate + ": " + (probe.error?.message || "exit " + probe.status));
  }
  return { tried };
}
function runDraftSchemaValidation() {
  const python = discoverPython();
  if (!python.command) return { error: "could not find usable Python. Tried " + python.tried.join("; ") + ". Set PYTHON to an executable path." };
  const process = spawnSync(python.command, [resolve(root, "scripts/validate/run_evidence_pack_schema_validation.py"), "--root", root], { encoding: "utf8" });
  if (process.error) return { error: "Draft 2020-12 validator could not start: " + process.error.message };
  if (process.status !== 0) return { error: "Draft 2020-12 validation failed: " + (process.stderr || process.stdout || "unknown error").trim() };
  const output = process.stdout.trim();
  const line = output.split(/\r?\n/).find((entry) => entry.startsWith("EVIDENCE_SCHEMA_SUMMARY="));
  if (!line) return { error: "Draft 2020-12 validator did not emit an evidence schema summary" };
  try {
    return { output, python: python.command, schemaMutations: JSON.parse(line.slice("EVIDENCE_SCHEMA_SUMMARY=".length)).schemaMutations };
  } catch {
    return { error: "Draft 2020-12 validator emitted an unreadable evidence schema summary" };
  }
}

const args = process.argv.slice(2);
const selectedAudit = args[0] === "--audit" ? args[1] : undefined;
if (!((args.length === 0) || (args.length === 2 && args[0] === "--audit" && auditIds.includes(selectedAudit)))) {
  console.error("Usage: node scripts/validate/check_first_release_evidence_pack.mjs [--audit AUD-002|AUD-003|AUD-004|AUD-005]");
  process.exit(2);
}
const result = validateEvidencePack(createContext(), selectedAudit);
const mutations = selectedAudit === undefined ? runSemanticMutationTests() : { count: 0, failures: [] };
const schema = runDraftSchemaValidation();
if (schema.error) result.errors.push(schema.error);
result.errors.push(...mutations.failures.map((entry) => "semantic mutation failure: " + entry));
if (schema.output) console.log(schema.output);
if (result.errors.length) {
  console.error("First-release evidence-pack validation failed:");
  for (const error of result.errors) console.error("- " + error);
  process.exitCode = 1;
} else {
  console.log("EVIDENCE_PACK_SUMMARY=" + JSON.stringify({ artifacts: selectedAudit ? manifest.filter((entry) => entry.auditId === selectedAudit).length : manifest.length, semanticMutations: mutations.count, schemaMutations: schema.schemaMutations, python: schema.python }));
  console.log("Validated first-release evidence artifacts, claim inventories, source manifests, separate policy prerequisites, ordinal capability gates, semantic fixtures, and real negative mutations" + (selectedAudit ? " for " + selectedAudit : "") + ".");
}
