---
description: 'Use when adding or changing pytest coverage for backend APIs, sync workflows, Savant aggregation, Yahoo OAuth logic, or dashboard-related Python behavior under tests/.'
applyTo: 'tests/**/*.py'
---

# Python Test Guidance

## Test Style
- Follow the current pytest style in `tests/test_main_api.py`, `tests/test_sync_service.py`, `tests/test_savant_client.py`, and `tests/test_metrics.py`.
- Prefer focused tests around the changed behavior rather than broad end-to-end rewrites.
- Use descriptive test names that state the scenario and expected outcome.

## Isolation
- Mock Yahoo and Savant boundaries by default for unit tests.
- Use live integration behavior only in the existing integration or manual test paths unless the user explicitly asks for broader live coverage.
- Keep fixtures and test data small and tailored to the branch of behavior being validated.

## Coverage Expectations
- Add or update tests when changing API payload shape, sync mode behavior, cache behavior, or ranking calculations.
- Assert user-visible outputs and important metadata, not only status codes.
- When repeated setup appears across tests, prefer promoting it into a shared helper or fixture rather than duplicating it again.