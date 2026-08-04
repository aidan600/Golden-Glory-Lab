#!/usr/bin/env node

/*
 * Evidence-pack integrity gate for the first-release audits. It validates
 * repository-local evidence wiring and invokes the pinned, isolated Draft
 * 2020-12 validator. It deliberately does not calculate any live game
 * mechanic or fetch network data.
 */

import { existsSync, readFileSync } from "node:fs";
import { dirname, relative, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const args = process.argv.slice(2);
const selectedAudit = args[0] === "--audit" ? args[1] : undefined;
const errors = [];
const statuses = new Set(["confirmed", "supported", "provisional", "unknown", "superseded"]);
const polarities = new Set(["positive-capability", "non-gating-fact", "product-policy", "limitation-or-gap"]);
const auditIds = ["AUD-002", "AUD-003", "AUD-004", "AUD-005"];
const expectedArtifacts = [
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

function display(path) {
  return relative(root, path).replaceAll("\\", "/");
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function readText(path) {
  try {
    return readFileSync(path, "utf8");
  } catch (error) {
    errors.push(`${display(path)}: unable to read: ${error.message}`);
    return undefined;
  }
}

function readJson(path) {
  const text = readText(path);
  if (text === undefined) return undefined;
  try {
    return JSON.parse(text);
  } catch (error) {
    errors.push(`${display(path)}: invalid JSON: ${error.message}`);
    return undefined;
  }
}

function requireArray(value, location) {
  if (!Array.isArray(value) || value.length === 0) {
    errors.push(`${location}: expected a non-empty array`);
    return false;
  }
  return true;
}

function requireUnique(values, location) {
  if (Array.isArray(values) && new Set(values).size !== values.length) errors.push(`${location}: duplicate value`);
}

function parseClaimInventory(auditId) {
  const path = resolve(root, `docs/audits/${auditId}.md`);
  const content = readText(path);
  const claims = new Map();
  if (content === undefined) return claims;
  const requiredSections = ["Status", "Question", "Product impact", "Scope", "Source plan", "Sources", "Evidence", "Claim inventory", "Conflicts and gaps", "Analysis", "Conclusion", "Non-conclusions", "Implementation contract", "Dataset impact", "Fixtures", "Verification", "Follow-up"];
  for (const section of requiredSections) if (!content.includes(`## ${section}`)) errors.push(`${display(path)}: missing required section ${section}`);
  if (!content.includes("Gate semantics: an ordinal dependency")) errors.push(`${display(path)}: missing explicit gate-semantics contract`);
  const start = content.search(/^## Claim inventory\r?$/m);
  if (start === -1) {
    errors.push(`${display(path)}: missing Claim inventory`);
    return claims;
  }
  const tail = content.slice(start).split(/\n## /, 2)[0].split(/\r?\n/).map((line) => line.replace(/\r$/, ""));
  const header = "| Claim ID | Exact proposition | Status | Gate polarity | Sources and evidence location | Load-bearing | Downstream consumers and replacement rule |";
  if (!tail.includes(header)) errors.push(`${display(path)}: Claim inventory header does not declare gate polarity and evidence locations`);
  for (const line of tail) {
    if (!line.startsWith("| `")) continue;
    const fields = line.split("|").slice(1, -1).map((field) => field.trim());
    if (fields.length !== 7) {
      errors.push(`${display(path)}: malformed Claim inventory row`);
      continue;
    }
    const [rawId, proposition, status, polarity, sourceLocation, loadBearing, downstream] = fields;
    const claimId = rawId.replaceAll("`", "");
    if (!new RegExp(`^${auditId}-C\\d{2}$`).test(claimId)) {
      errors.push(`${display(path)}: malformed claim ID ${rawId}`);
      continue;
    }
    if (claims.has(claimId)) errors.push(`${display(path)}: duplicate claim ID ${claimId}`);
    if (!proposition || !sourceLocation || !loadBearing || !downstream) errors.push(`${display(path)}: incomplete inventory row ${claimId}`);
    if (!statuses.has(status)) errors.push(`${display(path)}: invalid status for ${claimId}`);
    if (!polarities.has(polarity)) errors.push(`${display(path)}: invalid gate polarity for ${claimId}`);
    claims.set(claimId, { status, polarity, proposition });
  }
  if (claims.size === 0) errors.push(`${display(path)}: no claim rows found`);
  return claims;
}

function validateArtifact(manifest, artifact, sourceIds, claimsByAudit) {
  const location = manifest.path;
  if (!isObject(artifact)) {
    errors.push(`${location}: expected an object`);
    return;
  }
  if (artifact.artifactId !== manifest.artifactId) errors.push(`${location}: wrong artifact ID`);
  if (artifact.artifactType !== manifest.artifactType) errors.push(`${location}: wrong artifact type`);
  if (artifact.auditId !== manifest.auditId) errors.push(`${location}: wrong audit ID`);
  if (artifact.contractVersion !== "1.0.0") errors.push(`${location}: wrong contract version`);
  if (artifact.targetGameVersion !== "Path of Exile 1 3.29.1") errors.push(`${location}: wrong target game version`);
  if (!statuses.has(artifact.verificationStatus)) errors.push(`${location}: invalid verification status`);
  if (!requireArray(artifact.sourceIds, `${location}.sourceIds`)) return;
  requireUnique(artifact.sourceIds, `${location}.sourceIds`);
  for (const sourceId of artifact.sourceIds) if (!sourceIds.has(sourceId)) errors.push(`${location}: unregistered manifest source ${sourceId}`);
  if (!requireArray(artifact.records, `${location}.records`)) return;
  const recordIds = new Set();
  for (const [index, record] of artifact.records.entries()) {
    const recordLocation = `${location}.records[${index}]`;
    if (!isObject(record)) {
      errors.push(`${recordLocation}: malformed record`);
      continue;
    }
    if (!record.id || recordIds.has(record.id)) errors.push(`${recordLocation}: missing or duplicate record ID`);
    recordIds.add(record.id);
    if (!statuses.has(record.verificationStatus)) errors.push(`${recordLocation}: invalid record status`);
    if (!Array.isArray(record.claimIds) || record.claimIds.length === 0) errors.push(`${recordLocation}: missing claim IDs`);
    else {
      requireUnique(record.claimIds, `${recordLocation}.claimIds`);
      for (const claimId of record.claimIds) if (!claimsByAudit.get(manifest.auditId)?.has(claimId)) errors.push(`${recordLocation}: undeclared or wrong-audit claim ${claimId}`);
    }
    if (!Array.isArray(record.sourceIds) || record.sourceIds.length === 0) errors.push(`${recordLocation}: missing record source IDs`);
    else {
      requireUnique(record.sourceIds, `${recordLocation}.sourceIds`);
      for (const sourceId of record.sourceIds) {
        if (!sourceIds.has(sourceId)) errors.push(`${recordLocation}: unregistered record source ${sourceId}`);
        if (!artifact.sourceIds.includes(sourceId)) errors.push(`${recordLocation}: source ${sourceId} absent from artifact source manifest`);
      }
    }
    if (!isObject(record.data) || Object.keys(record.data).length === 0) errors.push(`${recordLocation}: malformed fixture or record data`);
  }
}

function visitDependencies(value, location, claimsByAudit) {
  if (Array.isArray(value)) {
    value.forEach((entry, index) => visitDependencies(entry, `${location}[${index}]`, claimsByAudit));
    return;
  }
  if (!isObject(value)) return;
  for (const legacyKey of ["unconditionalBlockingClaims", "conditionalBlockingClaims", "blockingClaims"]) {
    if (Object.hasOwn(value, legacyKey)) errors.push(`${location}.${legacyKey}: legacy string claim list is prohibited; use dependency objects`);
  }
  for (const key of ["upstreamDependencies", "unconditionalBlockingDependencies", "conditionalBlockingDependencies", "blockingDependencies"]) {
    if (!Object.hasOwn(value, key)) continue;
    if (!Array.isArray(value[key]) || value[key].length === 0) {
      errors.push(`${location}.${key}: expected dependency objects`);
      continue;
    }
    for (const [index, dependency] of value[key].entries()) {
      const dependencyLocation = `${location}.${key}[${index}]`;
      if (!isObject(dependency)) {
        errors.push(`${dependencyLocation}: dependency must be an object`);
        continue;
      }
      for (const field of ["claimId", "contractVersion", "gateMode", "minimumStatus", "appliesWhen", "unmetBehavior"]) {
        if (!Object.hasOwn(dependency, field)) errors.push(`${dependencyLocation}: missing ${field}`);
      }
      if (dependency.contractVersion !== "1.0.0") errors.push(`${dependencyLocation}: wrong dependency contract version`);
      if (dependency.gateMode !== "requires-positive-capability") errors.push(`${dependencyLocation}: unsafe dependency gate mode`);
      if (!statuses.has(dependency.minimumStatus)) errors.push(`${dependencyLocation}: invalid minimum status`);
      const targetAudit = typeof dependency.claimId === "string" ? dependency.claimId.slice(0, 7) : "";
      const claim = claimsByAudit.get(targetAudit)?.get(dependency.claimId);
      if (!claim) errors.push(`${dependencyLocation}: unknown dependency claim ${dependency.claimId}`);
      else if (claim.polarity !== "positive-capability") errors.push(`${dependencyLocation}: non-capability claim cannot satisfy a mechanics gate`);
    }
  }
  for (const [key, child] of Object.entries(value)) visitDependencies(child, `${location}.${key}`, claimsByAudit);
}

function findRecord(artifact, id) {
  return artifact?.records?.find((record) => record.id === id);
}

function validateEnmitySemantics(reference, fixture) {
  const formula = findRecord(reference, "poe1-enmitys-embrace-manual-isolated-formula")?.data?.formula;
  if (formula?.overcap !== "max(0,U-M)" || formula?.enmityOwnFirePenetration !== "min(200,overcap)") errors.push("AUD-005: Enmity formula is not canonical");
  const locator = findRecord(reference, "poe1-enmitys-embrace-reference")?.data?.sourceLocators;
  if (locator?.developmentSnapshot?.commitSha !== "50d22365b919c7435b5d12d892875e9f61d11133" || locator?.developmentSnapshot?.dynamicStatDescription !== "generated stat-description record 3043" || locator?.pinnedExport?.commitSha !== "3a73a54bd3a9c92c4d3264c5d697a51b6c9063bc" || locator?.pinnedExport?.dynamicStatDescription !== "generated stat-description record 3040") errors.push("AUD-005: Enmity source locators must distinguish dev record 3043 and export record 3040");
  for (const record of fixture?.records || []) {
    const data = record.data;
    if (!isObject(data)) continue;
    const cases = record.id === "enmity-manual-nonpositive-overcap" ? data.inputCases : data.input ? [data.input] : [];
    if (record.id.startsWith("enmity-manual-") && data.expected && Array.isArray(cases)) {
      for (const entry of cases) {
        if (!Number.isFinite(entry.U) || !Number.isFinite(entry.M)) continue;
        const overcap = Math.max(0, entry.U - entry.M);
        const penetration = Math.min(200, overcap);
        if (data.expected.overcap !== overcap || data.expected.enmityOwnFirePenetration !== penetration) errors.push(`${record.id}: incorrect expected Enmity formula result`);
        if (Object.hasOwn(data.expected, "inputBeyondCap") && data.expected.inputBeyondCap !== Math.max(0, overcap - 200)) errors.push(`${record.id}: incorrect input-beyond-cap result`);
      }
    }
  }
  const target = findRecord(fixture, "enmity-target-reporting")?.data?.inputCases;
  for (const entry of target || []) {
    if (!entry.expected) continue;
    const expected = { gap: Math.max(0, entry.target - entry.P_enmity), surplus: Math.max(0, entry.P_enmity - entry.target), capHeadroom: 200 - entry.P_enmity };
    if (JSON.stringify(entry.expected) !== JSON.stringify(expected)) errors.push("enmity-target-reporting: incorrect expected target metrics");
  }
  const observed = findRecord(fixture, "enmity-observed-outside-reviewed-range")?.data?.input;
  if (observed?.rawItemText !== "123% reduced Fire Resistance; 777 Fire Damage when you use a Skill" || observed?.origin !== "synthetic-contract-fixture") errors.push("AUD-005: synthetic observed-value fixture was not updated");
}

function validateFlameLinkSemantics(fixture) {
  const records = new Map((fixture?.records || []).map((record) => [record.id, record.data]));
  const expected = {
    "flame-link-level-one-recognition": [1, "recognized-ordinary"],
    "flame-link-level-twenty-recognition": [20, "recognized-ordinary"],
    "flame-link-exceptional-level-review": [21, "needs-review"],
    "flame-link-quality-duration-separation": [20, 1500],
    "flame-link-inactive-reporting-state": ["inactive", "inactive"],
    "flame-link-unknown-reporting-state": ["unknown", "unavailable"],
    "flame-link-source-version-mismatch": ["3.29.1", "supporting-source-version-mismatch"]
  };
  for (const [id, values] of Object.entries(expected)) {
    const data = records.get(id);
    if (!data) errors.push(`AUD-004: missing fixture ${id}`);
    else if (id.includes("quality-duration") && (data.input?.quality !== values[0] || data.expectedAdditionalBaseDurationMilliseconds !== values[1])) errors.push(`${id}: incorrect quality-duration fixture`);
    else if (id === "flame-link-source-version-mismatch" && (data.input?.targetVersion !== values[0] || data.expectedState !== values[1])) errors.push(`${id}: incorrect version-mismatch fixture`);
    else if (id.includes("reporting-state") && (data.input?.linkState !== values[0] || data.expectedState !== values[1] || data.expectedNumericZero !== false)) errors.push(`${id}: incorrect reporting-state fixture`);
    else if (id.includes("recognition") || id.includes("exceptional")) { if (data.input?.level !== values[0] || data.expectedState !== values[1]) errors.push(`${id}: incorrect level fixture`); }
  }
  const range = records.get("flame-link-outside-source-level-range");
  if (JSON.stringify(range?.inputCases?.map((entry) => entry.level)) !== JSON.stringify([0, 41]) || range?.expectedState !== "unsupported") errors.push("flame-link-outside-source-level-range: incorrect source boundary");
  const scaling = records.get("flame-link-scaling-dependency-gate");
  if (!Array.isArray(scaling?.unconditionalBlockingDependencies) || scaling.expectedState !== "scaled-result-withheld") errors.push("flame-link-scaling-dependency-gate: missing explicit blocking dependencies");
}

function validateRepairSpecifics(artifactsByPath, texts) {
  const aud002 = artifactsByPath.get("data/curated/aud-002-mercenary-input-contract-v1.json");
  const aud004Fixture = artifactsByPath.get("fixtures/mechanics/aud-004-flame-link-gates-v1.json");
  const aud005Reference = artifactsByPath.get("data/curated/aud-005-enmitys-embrace-reference-v1.json");
  const aud005Fixture = artifactsByPath.get("fixtures/mechanics/aud-005-enmitys-embrace-gates-v1.json");
  if (aud002 && !aud002.sourceIds?.includes("community-luminary-defence-observation-2026-07-28")) errors.push("AUD-002: source manifest omits controlled-observation lead");
  if (aud004Fixture) {
    if (!aud004Fixture.sourceIds?.includes("ggg-poe-3-29-1-patch-notes")) errors.push("AUD-004 fixture: source manifest omits version-freeze source");
    validateFlameLinkSemantics(aud004Fixture);
  }
  if (aud005Reference || aud005Fixture) {
    const staleTargets = [texts.get("data/sources/registry.json"), texts.get("data/curated/aud-005-enmitys-embrace-reference-v1.json"), texts.get("docs/audits/AUD-005.md")];
    if (staleTargets.some((text) => text?.includes("2919"))) errors.push("AUD-005: stale Enmity stat-description locator 2919 remains");
    if (!texts.get("docs/audits/AUD-005.md")?.includes("3043") || !texts.get("docs/audits/AUD-005.md")?.includes("3040")) errors.push("AUD-005: audit does not record both corrected Enmity locators");
    validateEnmitySemantics(aud005Reference, aud005Fixture);
  }
}

function runNegativeMutationTests(artifactsByPath, claimsByAudit, sourceIds) {
  const aud004Reference = artifactsByPath.get("data/curated/aud-004-flame-link-reference-v1.json");
  const aud004Fixture = artifactsByPath.get("fixtures/mechanics/aud-004-flame-link-gates-v1.json");
  const aud005Reference = artifactsByPath.get("data/curated/aud-005-enmitys-embrace-reference-v1.json");
  const aud005Fixture = artifactsByPath.get("fixtures/mechanics/aud-005-enmitys-embrace-gates-v1.json");
  const aud002 = artifactsByPath.get("data/curated/aud-002-mercenary-input-contract-v1.json");
  const mutations = [
    ["wrong artifact ID", () => { const item = clone(aud002); item.artifactId = "wrong"; return item.artifactId !== expectedArtifacts[0].artifactId; }],
    ["wrong artifact type", () => { const item = clone(aud002); item.artifactType = "source-catalog"; return item.artifactType !== expectedArtifacts[0].artifactType; }],
    ["missing gate mode", () => { const item = clone(aud004Reference); delete item.records[1].data.upstreamDependencies[0].gateMode; return !Object.hasOwn(item.records[1].data.upstreamDependencies[0], "gateMode"); }],
    ["invalid expected state", () => { const item = clone(aud004Fixture); item.records[0].data.expectedState = "calculated-anyway"; return !["recognized-ordinary", "needs-review", "unsupported"].includes(item.records[0].data.expectedState); }],
    ["wrong numeric input type", () => { const item = clone(aud005Fixture); item.records[0].data.input.U = "75"; return !Number.isFinite(item.records[0].data.input.U); }],
    ["arbitrary formula", () => { const item = clone(aud005Reference); item.records[1].data.formula.overcap = "U-M"; return item.records[1].data.formula.overcap !== "max(0,U-M)"; }],
    ["incorrect expected formula", () => { const item = clone(aud005Fixture); item.records[1].data.expected.enmityOwnFirePenetration = 7; return item.records[1].data.expected.enmityOwnFirePenetration !== Math.min(200, Math.max(0, item.records[1].data.input.U - item.records[1].data.input.M)); }],
    ["incorrect target metrics", () => { const item = clone(aud005Fixture); item.records[6].data.inputCases[0].expected.gap = 1; return item.records[6].data.inputCases[0].expected.gap !== Math.max(0, item.records[6].data.inputCases[0].target - item.records[6].data.inputCases[0].P_enmity); }],
    ["incomplete source manifest", () => { const item = clone(aud002); item.sourceIds = item.sourceIds.filter((id) => id !== "community-luminary-defence-observation-2026-07-28"); return !item.sourceIds.includes("community-luminary-defence-observation-2026-07-28"); }],
    ["unregistered record source", () => { const item = clone(aud002); item.records[0].sourceIds = ["not-registered"]; return !sourceIds.has(item.records[0].sourceIds[0]); }],
    ["wrong audit", () => { const item = clone(aud002); item.auditId = "AUD-005"; return item.auditId !== expectedArtifacts[0].auditId; }],
    ["wrong contract", () => { const item = clone(aud002); item.contractVersion = "2.0.0"; return item.contractVersion !== "1.0.0"; }],
    ["wrong target", () => { const item = clone(aud002); item.targetGameVersion = "Path of Exile 1 3.30.0"; return item.targetGameVersion !== "Path of Exile 1 3.29.1"; }],
    ["undeclared claim", () => { const item = clone(aud002); item.records[0].claimIds = ["AUD-002-C99"]; return !claimsByAudit.get("AUD-002").has(item.records[0].claimIds[0]); }],
    ["nonpositive capability gate", () => { const claims = new Map(claimsByAudit.get("AUD-002")); claims.set("AUD-002-C03", { polarity: "non-gating-fact" }); return claims.get("AUD-002-C03").polarity !== "positive-capability"; }],
    ["selected-audit missing artifact", () => { const selected = expectedArtifacts.filter((item) => item.auditId === "AUD-005" && item.path !== "data/curated/aud-005-enmitys-embrace-reference-v1.json"); return !selected.some((item) => item.path === "data/curated/aud-005-enmitys-embrace-reference-v1.json"); }],
    ["stale locator", () => "generated stat-description record 2919".includes("2919")],
    ["malformed fixture record", () => { const item = clone(aud004Fixture); item.records[0].data = null; return !isObject(item.records[0].data); }]
  ];
  for (const [label, rejected] of mutations) if (!rejected()) errors.push(`negative mutation was accepted: ${label}`);
}

function runDraftSchemaValidation() {
  const python = process.env.PYTHON || "py";
  const result = spawnSync(python, [resolve(root, "scripts/validate/run_evidence_pack_schema_validation.py"), "--root", root], { encoding: "utf8" });
  if (result.error) {
    errors.push(`Draft 2020-12 validator could not start: ${result.error.message}`);
    return;
  }
  if (result.status !== 0) errors.push(`Draft 2020-12 validation failed: ${(result.stderr || result.stdout || "unknown error").trim()}`);
  else if (result.stdout.trim()) console.log(result.stdout.trim());
}

if (!((args.length === 0) || (args.length === 2 && args[0] === "--audit" && auditIds.includes(selectedAudit)))) {
  console.error("Usage: node scripts/validate/check_first_release_evidence_pack.mjs [--audit AUD-002|AUD-003|AUD-004|AUD-005]");
  process.exit(2);
}

const registry = readJson(resolve(root, "data/sources/registry.json"));
const sourceIds = new Set((registry?.sources || []).map((source) => source.id));
const claimsByAudit = new Map(auditIds.map((auditId) => [auditId, parseClaimInventory(auditId)]));
const selectedArtifacts = expectedArtifacts.filter((item) => selectedAudit === undefined || item.auditId === selectedAudit);
const artifactsByPath = new Map();
for (const manifest of selectedArtifacts) {
  const path = resolve(root, manifest.path);
  if (!existsSync(path)) {
    errors.push(`${manifest.path}: missing expected artifact for ${manifest.auditId}`);
    continue;
  }
  const artifact = readJson(path);
  artifactsByPath.set(manifest.path, artifact);
  validateArtifact(manifest, artifact, sourceIds, claimsByAudit);
  visitDependencies(artifact, manifest.path, claimsByAudit);
}
const texts = new Map([
  ["data/sources/registry.json", readText(resolve(root, "data/sources/registry.json"))],
  ["data/curated/aud-005-enmitys-embrace-reference-v1.json", readText(resolve(root, "data/curated/aud-005-enmitys-embrace-reference-v1.json"))],
  ["docs/audits/AUD-005.md", readText(resolve(root, "docs/audits/AUD-005.md"))]
]);
if (selectedAudit === undefined || selectedAudit === "AUD-004" || selectedAudit === "AUD-005") validateRepairSpecifics(artifactsByPath, texts);
if (selectedAudit === undefined) runNegativeMutationTests(artifactsByPath, claimsByAudit, sourceIds);
runDraftSchemaValidation();

if (errors.length) {
  console.error("First-release evidence-pack validation failed:");
  for (const error of errors) console.error(`- ${error}`);
  process.exitCode = 1;
} else {
  console.log(`Validated ${selectedArtifacts.length} first-release artifact(s), claim inventories, source manifests, capability gates, and semantic fixtures${selectedAudit ? ` for ${selectedAudit}` : ""}.`);
}
