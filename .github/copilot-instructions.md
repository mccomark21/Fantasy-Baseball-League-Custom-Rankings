# Project Guidelines

## Architecture
- This repo is a fantasy baseball rankings system with a FastAPI backend in `src/backend/` and a Plotly Dash frontend in `src/frontend/`.
- Yahoo league data and Baseball Savant data flow into cached daily aggregates, then into ranking calculations and dashboard views.
- Preserve the current split of responsibilities: API and orchestration in `main.py` and `sync_service.py`, stat processing in `savant_client.py` and `metrics.py`, UI structure in `layouts.py`, interactivity in `callbacks.py`.
- Use [ARCHITECTURE.md](../ARCHITECTURE.md) and [README.md](../README.md) as the source of truth for system behavior and user-visible workflows.

## Change Scope
- Prefer minimal, surgical edits that fit the existing structure.
- Do not perform broad refactors, renames, or file moves unless the user asks for them.
- Verify the current implementation in the relevant files before changing code.
- Follow existing patterns in nearby code before introducing a new abstraction or dependency.

## Build And Test
- Use the project virtual environment when running Python commands.
- Prefer focused pytest runs for the files or behavior you changed before wider test runs.
- When changing backend endpoints, sync behavior, or ranking logic, check the relevant tests under `tests/`.

## Conventions
- Keep constants explicit instead of scattering new magic numbers.
- Keep user-visible API and dashboard behavior aligned with [README.md](../README.md).
- Update docs when public endpoints, setup steps, configuration, sync workflow, or dashboard behavior change.
- Use proper file editing tools for file creation and modification; do not rely on shell redirection for writing files.