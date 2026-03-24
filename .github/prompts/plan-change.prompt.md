---
name: 'Plan Repo Change'
description: 'Create a scoped implementation plan for a change in this fantasy baseball rankings repo.'
argument-hint: 'Describe the feature, fix, or refactor to plan'
agent: 'Plan'
---

Create an implementation plan for this repository change: ${input}

Requirements:
- Use the current project structure and conventions from [README.md](../../README.md) and [ARCHITECTURE.md](../../ARCHITECTURE.md).
- Identify the specific backend, frontend, tests, and docs files that should change.
- Prefer the smallest viable set of changes.
- Call out API contract changes, cache implications, sync workflow implications, and testing impact when relevant.
- If the request is underspecified, list the missing decisions instead of guessing.

Output format:
1. Goal
2. Files to touch
3. Implementation steps
4. Tests to add or run
5. Docs to update
6. Risks or open questions