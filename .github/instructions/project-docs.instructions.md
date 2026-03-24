---
description: 'Use when code changes affect README content, setup steps, configuration, sync workflow, endpoints, testing guidance, or user-visible dashboard behavior in markdown or Python files.'
applyTo: 'README.md, docs/**/*.md, src/**/*.py'
---

# Project Documentation Guidance

## When To Update Docs
- Update [README.md](../../README.md) when features, setup steps, API endpoints, configuration, or dashboard workflows change.
- Update files under `docs/` when OAuth setup, Yahoo testing, or other detailed workflows change.
- Keep code and docs aligned in the same task when public behavior changes.

## Scope
- Document user-visible behavior and operator workflows, not internal implementation trivia.
- Prefer updating the closest existing document instead of creating a new markdown file unless the change clearly needs a new guide.
- Keep endpoint names, query parameters, and example flows consistent with the current implementation.

## Quality Bar
- Use concise language and concrete steps.
- If behavior changed, update examples and command snippets that would otherwise drift out of date.