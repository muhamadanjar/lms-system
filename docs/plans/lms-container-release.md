# Plan: LMS container release

Related Progress: [../../progress/lms-container-release.md](../../progress/lms-container-release.md)

## Goal

Provide reproducible development and production container workflows for the LMS
backend. Development and locally built production images follow the adjacent
tileserver Compose profile pattern. Production deployment can separately pull
an immutable LMS image from private GHCR. Database, authentication, and object
storage remain external.

## Container contract

- `docker/Dockerfile` contains `builder`, `dev`, and `production` stages.
- The production stage uses Python 3.12 slim, a non-root `lms` user, Uvicorn,
  and the existing `/health/db` endpoint.
- `requirements-prod.txt` contains runtime dependencies only. Development keeps
  the existing test dependencies.
- `docker-compose.yml` defines `development` and `production` profiles:
  `lms-dev` builds the `dev` target; `lms` and `migrate` build the `production`
  target and use the configured `LMS_IMAGE` tag.
- `production.yml` is the pull-only deployment manifest for `lms` and
  `migrate` using an already-published immutable `LMS_IMAGE` reference.

## Release contract

The existing test and semantic-release jobs remain the release gate. When
semantic-release creates a numeric `X.Y.Z` tag, GitHub Actions builds and pushes
`ghcr.io/<repository-owner>/lms-system:X.Y.Z` and `:latest` for `linux/amd64`.
The workflow uses the built-in GitHub token, OCI metadata, BuildKit provenance,
and an SBOM. Commits without a semantic release do not publish an image.

## Configuration and security

- `.env.docker` and `.env.production` are operator-created and ignored.
- Development uses local storage and a host database.
- Production forces `FILE_STORAGE_BACKEND=s3`; S3 credentials, database URLs,
  authentication URLs, and `SSH_CREDENTIAL_ENC_KEY` are injected at runtime.
- No credential or private file is copied into the image or committed to the
  repository.
