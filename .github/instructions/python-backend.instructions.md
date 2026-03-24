---
description: 'Use when writing or changing FastAPI routes, Yahoo OAuth flows, Savant sync logic, cache behavior, pandas transformations, or ranking calculations in src/backend Python files.'
applyTo: 'src/backend/**/*.py'
---

# Python Backend Guidance

## Structure
- Preserve the current module boundaries in `src/backend/`.
- Follow the existing route and helper layout in `src/backend/main.py` when adding API behavior.
- Follow the orchestration pattern in `src/backend/sync_service.py` for season sync, correction windows, and cache writes.
- Follow the metric pipeline and metric names already used in `src/backend/metrics.py`.

## Data And Cache Work
- Treat cached daily aggregate records and precomputed windows as first-class behavior, not incidental implementation details.
- Keep data transformations additive and traceable. Prefer explicit helper functions over inline multi-step DataFrame mutation inside route handlers.
- Reuse existing cache managers and cache key patterns before creating new storage paths.
- Preserve current field names in API payloads and ranking records unless the user explicitly asks for a contract change.

## FastAPI And Error Handling
- Use `HTTPException` for request validation and API-facing failures.
- Raise clear Python exceptions in backend service code when work cannot continue; do not silently swallow failures.
- Keep API responses consistent with the surrounding endpoints in `src/backend/main.py`.
- Prefer extending existing helper functions before introducing new route-local logic.

## Pandas And Metrics
- Keep metric names consistent with the current domain language: `xwOBA`, `Pull Air %`, `BB:K`, and `SB per PA`.
- Preserve the current ranking flow: date resolution, daily record loading, aggregation, z-score normalization, capping, composite score, then ranking.
- When changing DataFrame logic, keep date parsing and record conversion explicit.

## Implementation Guardrails
- Add new constants near related existing constants instead of hardcoding new values repeatedly.
- Prefer standard library and current project dependencies over adding new packages.
- If a change affects endpoint behavior, sync workflow, or config usage, update docs and add or adjust tests in the same task.