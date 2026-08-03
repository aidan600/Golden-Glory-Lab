#!/usr/bin/env node

/*
 * Validates the small, hand-reviewed evidence artifacts introduced by the
 * first-release audit pack. This is an audit-only validator: it does not
 * calculate any game mechanic or run network requests.
 *
 * Inputs: repository JSON, audit Markdown, and data/sources/registry.json.
 * Outputs: stdout diagnostics and a non-zero exit code on a contract error.
 * Network: none.
 * Limits: validates the durable audit envelope and claim/source wiring, not
 * the truth of an external game source.
 */

import { existsSync, readFileSync } from "node:fs";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const selectedAudit = process.argv[2] === "--audit" ? process.argv[3] : undefined;
const errors = [];

const statuses = new Set(["confirmed", "supported", "provisional", "unknown", "superseded"]);
const auditIds = new Set(["AUD-002", "AUD-003", "AUD-004", "AUD-005"]);
const artifactPaths = [
  "data/curated/aud-002-mercenary-input-contract-v1.json",
  "data/curated/aud-003-light-radius-passive-sources-v1.json",
  "data/curated/aud-003-light-radius-observed-stat-terms-v1.json",
  "data/curated/aud-003-link-effect-passive-sources-v1.json",
  "data/curated/aud-003-link-effect-observed-stat-terms-v1.json",
  "data/curated/aud-003-golden-glory-mechanic-v1.json",
  "data/curated/aud-004-flame-link-reference-v1.json",
  "fixtures/mechanics/aud-004-flame-link-gates-v1.json",
  "data/curated/aud-005-enmitys-embrace-reference-v1.json",
  "fixtures/mechanics/aud-005-enmitys-embrace-gates-v1.json"
];

function display(path) {
  return relative(root, path).replaceAll("\\", "/");
}

function readJson(path) {
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch (error) {
    errors.push(display(path) + ": invalid JSON: " + error.message);
    return undefined;
  }
}

function requireString(value, location) {
  if (typeof value !== "string" || value.length === 0) {
    errors.push(location + ": expected a non-empty string");
    return false;
  }
  return true;
}

function requireArray(value, location) {
  if (!Array.isArray(value) || value.length === 0) {
    errors.push(location + ": expected a non-empty array");
    return false;
  }
  return true;
}

function validateRetention(value, location) {
  const required = [
    "sourceLicense",
    "dataLicense",
    "provenance",
    "redistribution",
    "derivation",
    "attribution",
    "retainedMaterial",
    "notVendored",
    "uncertainty"
  ];
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    errors.push(location + ": expected a retention object");
    return;
  }
  for (const key of required) {
    requireString(value[key], location + "." + key);
  }
  for (const key of Object.keys(value)) {
    if (!required.includes(key)) {
      errors.push(location + ": unexpected property " + key);
    }
  }
}

function validateArtifact(path, sourceIds, claimsByAudit) {
  const artifact = readJson(path);
  if (artifact === undefined) {
    return;
  }
  const location = display(path);
  const required = [
    "schemaVersion",
    "artifactId",
    "artifactType",
    "auditId",
    "contractVersion",
    "targetGameVersion",
    "verificationStatus",
    "sourceIds",
    "scope",
    "retention",
    "records"
  ];
  if (artifact === null || typeof artifact !== "object" || Array.isArray(artifact)) {
    errors.push(location + ": expected an object");
    return;
  }
  for (const key of required) {
    if (!Object.hasOwn(artifact, key)) {
      errors.push(location + ": missing required property " + key);
    }
  }
  for (const key of Object.keys(artifact)) {
    if (![...required, "notes"].includes(key)) {
      errors.push(location + ": unexpected property " + key);
    }
  }
  if (artifact.schemaVersion !== "1.0") {
    errors.push(location + ".schemaVersion: expected 1.0");
  }
  if (!auditIds.has(artifact.auditId)) {
    errors.push(location + ".auditId: unknown audit ID");
  }
  if (artifact.contractVersion !== "1.0.0") {
    errors.push(location + ".contractVersion: expected 1.0.0");
  }
  if (artifact.targetGameVersion !== "Path of Exile 1 3.29.1") {
    errors.push(location + ".targetGameVersion: unexpected target version");
  }
  if (!statuses.has(artifact.verificationStatus)) {
    errors.push(location + ".verificationStatus: invalid status");
  }
  requireString(artifact.artifactId, location + ".artifactId");
  requireString(artifact.artifactType, location + ".artifactType");
  requireString(artifact.scope, location + ".scope");
  validateRetention(artifact.retention, location + ".retention");
  if (requireArray(artifact.sourceIds, location + ".sourceIds")) {
    for (const sourceId of artifact.sourceIds) {
      if (!sourceIds.has(sourceId)) {
        errors.push(location + ".sourceIds: unregistered source " + JSON.stringify(sourceId));
      }
    }
  }
  if (!requireArray(artifact.records, location + ".records")) {
    return;
  }
  const recordIds = new Set();
  for (const [index, record] of artifact.records.entries()) {
    const recordLocation = location + ".records[" + index + "]";
    const recordRequired = [
      "id",
      "verificationStatus",
      "claimIds",
      "sourceIds",
      "evidenceLocation",
      "limitations",
      "loadBearing",
      "downstreamConsumers",
      "replacementRule",
      "data"
    ];
    if (record === null || typeof record !== "object" || Array.isArray(record)) {
      errors.push(recordLocation + ": expected an object");
      continue;
    }
    for (const key of recordRequired) {
      if (!Object.hasOwn(record, key)) {
        errors.push(recordLocation + ": missing required property " + key);
      }
    }
    for (const key of Object.keys(record)) {
      if (!recordRequired.includes(key)) {
        errors.push(recordLocation + ": unexpected property " + key);
      }
    }
    if (recordIds.has(record.id)) {
      errors.push(recordLocation + ".id: duplicate record ID " + record.id);
    }
    recordIds.add(record.id);
    requireString(record.id, recordLocation + ".id");
    requireString(record.evidenceLocation, recordLocation + ".evidenceLocation");
    requireString(record.limitations, recordLocation + ".limitations");
    requireString(record.replacementRule, recordLocation + ".replacementRule");
    if (!statuses.has(record.verificationStatus)) {
      errors.push(recordLocation + ".verificationStatus: invalid status");
    }
    if (typeof record.loadBearing !== "boolean") {
      errors.push(recordLocation + ".loadBearing: expected boolean");
    }
    if (requireArray(record.claimIds, recordLocation + ".claimIds")) {
      for (const claimId of record.claimIds) {
        if (!new RegExp("^" + artifact.auditId + "-C[0-9]{2}$").test(claimId)) {
          errors.push(recordLocation + ".claimIds: wrong audit-scoped claim ID " + claimId);
        } else if (!claimsByAudit.get(artifact.auditId)?.has(claimId)) {
          errors.push(recordLocation + ".claimIds: claim absent from " + artifact.auditId + " audit " + claimId);
        }
      }
    }
    if (requireArray(record.sourceIds, recordLocation + ".sourceIds")) {
      for (const sourceId of record.sourceIds) {
        if (!sourceIds.has(sourceId)) {
          errors.push(recordLocation + ".sourceIds: unregistered source " + JSON.stringify(sourceId));
        }
      }
    }
    requireArray(record.downstreamConsumers, recordLocation + ".downstreamConsumers");
    if (record.data === null || typeof record.data !== "object" || Array.isArray(record.data) || Object.keys(record.data).length === 0) {
      errors.push(recordLocation + ".data: expected a non-empty object");
    }
  }
}

function collectAuditClaims(auditId) {
  const path = resolve(root, "docs/audits/" + auditId + ".md");
  const claims = new Set();
  if (!existsSync(path)) {
    errors.push(display(path) + ": missing audit record");
    return claims;
  }
  const content = readFileSync(path, "utf8");
  const requiredSections = [
    "## Status",
    "## Question",
    "## Product impact",
    "## Scope",
    "## Source plan",
    "## Sources",
    "## Evidence",
    "## Claim inventory",
    "## Conflicts and gaps",
    "## Analysis",
    "## Conclusion",
    "## Non-conclusions",
    "## Implementation contract",
    "## Dataset impact",
    "## Fixtures",
    "## Verification",
    "## Follow-up"
  ];
  for (const section of requiredSections) {
    if (!content.includes(section)) {
      errors.push(display(path) + ": missing required section " + section);
    }
  }
  if (!content.includes("1.0.0")) {
    errors.push(display(path) + ": missing contract version 1.0.0");
  }
  for (const match of content.matchAll(new RegExp(auditId + "-C[0-9]{2}", "g"))) {
    claims.add(match[0]);
  }
  if (claims.size === 0) {
    errors.push(display(path) + ": no stable claim IDs found");
  }
  return claims;
}

if (selectedAudit !== undefined && !auditIds.has(selectedAudit)) {
  console.error("Usage: node scripts/validate/check_first_release_evidence_pack.mjs [--audit AUD-002|AUD-003|AUD-004|AUD-005]");
  process.exit(2);
}

const registryPath = resolve(root, "data/sources/registry.json");
const registry = readJson(registryPath);
const sourceIds = new Set(registry?.sources?.map((source) => source.id) || []);
const auditsToCheck = selectedAudit === undefined ? [...auditIds] : [selectedAudit];
const claimsByAudit = new Map(auditsToCheck.map((auditId) => [auditId, collectAuditClaims(auditId)]));

for (const relativePath of artifactPaths) {
  const path = resolve(root, relativePath);
  if (!existsSync(path)) {
    if (selectedAudit === undefined) {
      errors.push(relativePath + ": missing expected audit artifact");
    }
    continue;
  }
  const text = readFileSync(path, "utf8");
  const auditMatch = text.match(/"auditId"\s*:\s*"(AUD-00[2-5])"/);
  if (selectedAudit !== undefined && auditMatch?.[1] !== selectedAudit) {
    continue;
  }
  validateArtifact(path, sourceIds, claimsByAudit);
}

if (errors.length > 0) {
  console.error("First-release evidence-pack validation failed:");
  for (const error of errors) {
    console.error("- " + error);
  }
  process.exitCode = 1;
} else {
  console.log("Validated first-release audit records and evidence artifacts" + (selectedAudit ? " for " + selectedAudit : "") + ".");
}
