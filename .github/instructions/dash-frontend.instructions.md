---
description: 'Use when changing Plotly Dash layouts, callbacks, table rendering, theme behavior, or API-driven dashboard interactions in src/frontend Python files.'
applyTo: 'src/frontend/**/*.py'
---

# Dash Frontend Guidance

## Structure
- Preserve the current split between app bootstrapping in `app.py`, layout construction in `layouts.py`, and interaction logic in `callbacks.py`.
- Keep callbacks focused on one interaction flow when possible.
- Reuse existing helper functions and constants before adding new callback-local formatting logic.

## Dashboard Behavior
- Keep frontend behavior aligned with backend payloads instead of reshaping contracts casually in the UI.
- Preserve the current date-range, weight, theme, and rankings-table workflows unless the user asks to redesign them.
- Follow existing column labels and table formatting conventions when expanding the rankings table.

## Styling And State
- Avoid scattering new style dictionaries across unrelated callbacks.
- Keep theme-aware values grouped with existing theme constants and table-style helpers.
- Prefer clear display-state updates over implicit side effects between callbacks.

## Implementation Guardrails
- Use the same API base paths and response assumptions already established in `callbacks.py`.
- If a frontend change depends on backend contract changes, coordinate both sides and update docs together.