# Cursor Integration

This repository uses Cursor project rules in .cursor/rules/*.mdc and reusable
plain-Markdown commands in .cursor/commands/*.md. The convention was checked
against Cursor's [Project Rules documentation](https://docs.cursor.com/context/rules)
and [Commands documentation](https://docs.cursor.com/en/agent/chat/commands) on
2026-08-01.

The integration is deliberately small: the rule points to the repository's
canonical policy rather than duplicating it, and the command starts an
evidence-aware audit contract. AGENTS.md remains the vendor-neutral root guide.
