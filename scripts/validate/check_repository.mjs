#!/usr/bin/env node

/*
 * Repository-local validation with no package dependency.
 *
 * The source registry schema intentionally uses a small JSON Schema subset.
 * This checker implements every validation keyword used by that schema, so the
 * registry is validated against the schema rather than against a duplicate
 * hand-written contract.
 */

import { existsSync, readFileSync, readdirSync } from "node:fs";
import { dirname, extname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const errors = [];

function walk(directory, extension) {
  const found = [];
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    if (entry.name === ".git") {
      continue;
    }
    const path = resolve(directory, entry.name);
    if (entry.isDirectory()) {
      found.push(...walk(path, extension));
    } else if (extname(entry.name) === extension) {
      found.push(path);
    }
  }
  return found;
}

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

function valueType(value) {
  if (Array.isArray(value)) {
    return "array";
  }
  if (value === null) {
    return "null";
  }
  return typeof value;
}

function resolveReference(schemaRoot, reference) {
  if (!reference.startsWith("#/")) {
    throw new Error("unsupported schema reference " + reference);
  }
  return reference
    .slice(2)
    .split("/")
    .reduce((current, part) => current[part], schemaRoot);
}

function validate(value, schema, path, schemaRoot, collector) {
  if (schema.$ref) {
    validate(value, resolveReference(schemaRoot, schema.$ref), path, schemaRoot, collector);
    return;
  }

  if (Object.hasOwn(schema, "const") && value !== schema.const) {
    collector.push(path + ": must equal " + JSON.stringify(schema.const));
  }
  if (schema.enum && !schema.enum.includes(value)) {
    collector.push(path + ": must be one of " + schema.enum.join(", "));
  }
  if (schema.anyOf) {
    const matches = schema.anyOf.some((option) => {
      const optionErrors = [];
      validate(value, option, path, schemaRoot, optionErrors);
      return optionErrors.length === 0;
    });
    if (!matches) {
      collector.push(path + ": does not satisfy any permitted source location");
    }
  }
  if (schema.type && valueType(value) !== schema.type) {
    collector.push(path + ": expected " + schema.type + ", got " + valueType(value));
    return;
  }

  if (schema.type === "object") {
    for (const key of schema.required || []) {
      if (!Object.hasOwn(value, key)) {
        collector.push(path + ": missing required property " + key);
      }
    }
    const properties = schema.properties || {};
    if (schema.additionalProperties === false) {
      for (const key of Object.keys(value)) {
        if (!Object.hasOwn(properties, key)) {
          collector.push(path + ": unexpected property " + key);
        }
      }
    }
    for (const [key, childSchema] of Object.entries(properties)) {
      if (Object.hasOwn(value, key)) {
        validate(value[key], childSchema, path + "." + key, schemaRoot, collector);
      }
    }
  }

  if (schema.type === "array") {
    if (schema.minItems !== undefined && value.length < schema.minItems) {
      collector.push(path + ": must have at least " + schema.minItems + " item(s)");
    }
    if (schema.items) {
      value.forEach((item, index) => {
        validate(item, schema.items, path + "[" + index + "]", schemaRoot, collector);
      });
    }
  }

  if (schema.type === "string") {
    if (schema.minLength !== undefined && value.length < schema.minLength) {
      collector.push(path + ": must not be empty");
    }
    if (schema.pattern && !(new RegExp(schema.pattern).test(value))) {
      collector.push(path + ": does not match required pattern");
    }
  }
}

function validateRegistry() {
  const schema = readJson(resolve(root, "data/sources/registry.schema.json"));
  const registry = readJson(resolve(root, "data/sources/registry.json"));
  if (schema !== undefined && registry !== undefined) {
    validate(registry, schema, "data/sources/registry.json", schema, errors);
  }
}

function checkMarkdownLinks() {
  const linkPattern = /!?\[[^\]]*\]\(([^)\s]+)(?:\s+["'][^"']*["'])?\)/g;
  for (const markdownPath of walk(root, ".md")) {
    const content = readFileSync(markdownPath, "utf8");
    for (const match of content.matchAll(linkPattern)) {
      let target = match[1];
      if (target.startsWith("<") && target.endsWith(">")) {
        target = target.slice(1, -1);
      }
      const pathOnly = target.split("#", 1)[0];
      if (
        pathOnly === "" ||
        pathOnly.startsWith("http://") ||
        pathOnly.startsWith("https://") ||
        pathOnly.startsWith("mailto:")
      ) {
        continue;
      }
      const destination = resolve(dirname(markdownPath), decodeURIComponent(pathOnly));
      if (relative(root, destination).startsWith("..") || !existsSync(destination)) {
        errors.push(display(markdownPath) + ": missing repository-relative link " + target);
      }
    }
  }
}

function checkAgentReferences() {
  const agentPath = resolve(root, "AGENTS.md");
  if (!existsSync(agentPath)) {
    errors.push("AGENTS.md: missing");
    return;
  }
  const tick = String.fromCharCode(96);
  const pattern = new RegExp(tick + "([^" + tick + "]+)" + tick, "g");
  const references = readFileSync(agentPath, "utf8").matchAll(pattern);
  for (const match of references) {
    const candidate = match[1];
    if (!candidate.includes("/") || candidate.includes(" ")) {
      continue;
    }
    const path = resolve(root, candidate);
    if (relative(root, path).startsWith("..") || !existsSync(path)) {
      errors.push("AGENTS.md: missing referenced path " + candidate);
    }
  }
}

const jsonFiles = walk(root, ".json");
for (const path of jsonFiles) {
  readJson(path);
}
validateRegistry();
checkMarkdownLinks();
checkAgentReferences();

if (errors.length > 0) {
  console.error("Repository validation failed:");
  for (const error of errors) {
    console.error("- " + error);
  }
  process.exitCode = 1;
} else {
  console.log(
    "Validated " +
      jsonFiles.length +
      " JSON file(s), source registry schema conformance, Markdown links, and AGENTS.md references."
  );
}
