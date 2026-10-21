# Plan: Starlette TestClient HTTPX2 migration

Related Progress: [../../progress/httpx2-testclient.md](../../progress/httpx2-testclient.md)

## Goal

Remove Starlette's deprecation warning during synchronous `TestClient` tests by
installing `httpx2`, while retaining the existing `httpx` dependency used by
runtime adapters and asynchronous tests.

## Scope

- Add the pinned `httpx2` package to development/test dependencies.
- Keep `httpx==0.28.1` unchanged for runtime HTTP integrations.
- Do not change existing `TestClient` imports; Starlette selects `httpx2`
  automatically when it is installed.
- Keep production dependencies limited to packages required at runtime.

## Acceptance criteria

- CI installation from `requirements.txt` contains both `httpx` and `httpx2`.
- A FastAPI/Starlette `TestClient` smoke test imports and handles a request
  without the plain-`httpx` fallback warning.
- Existing runtime `httpx` imports remain unchanged.
