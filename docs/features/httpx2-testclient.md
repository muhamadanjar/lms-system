# Starlette TestClient HTTPX2 migration

Plan: [../../plans/httpx2-testclient.md](../../plans/httpx2-testclient.md)  
Progress: [../../progress/httpx2-testclient.md](../../progress/httpx2-testclient.md)

## Behavior

The test environment installs `httpx2==2.15.1`. Starlette's
`fastapi.testclient.TestClient` detects the package and uses it instead of
falling back to plain `httpx`.

The application continues to use `httpx==0.28.1` for runtime HTTP adapters and
asynchronous tests. The two packages are intentionally retained together;
`httpx2` is not a replacement import for the existing runtime code in this
service.

## Dependency boundary

- `requirements.txt`: includes both `httpx` and `httpx2`.
- `requirements-prod.txt`: keeps only runtime dependencies; `httpx2` is not
  required by the deployed application.

## Verification

A smoke test using FastAPI 0.141.1, Starlette 1.6.0, and HTTPX2 2.15.1
successfully handled a request through `TestClient` with
`StarletteDeprecationWarning` treated as an error.
