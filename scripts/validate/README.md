# Validation Scripts

This directory contains small checks for repository contracts and future data
pipelines. The baseline check_repository.mjs uses only Node.js standard library
modules. It parses repository JSON, validates the source registry against its
local JSON Schema subset, checks repository-relative Markdown links, and
confirms path references in AGENTS.md.

Run it from the repository root:

    node scripts/validate/check_repository.mjs
