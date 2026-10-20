# Progress: LMS container release

Plan: [../../plans/lms-container-release.md](../../plans/lms-container-release.md)

## Status: implementation complete; validation recorded

## Log

- [x] Confirm the scope and runtime boundary with the existing tileserver pattern.
- [x] Decide on profile-based development and production Compose services.
- [x] Decide on private GHCR, immutable release tags, and semantic-release gating.
- [x] Define external database, User Management, and production S3 boundaries.
- [x] Implement Dockerfile, profile-based Compose, pull-only deployment
      manifest, workflow, dependency split, and environment examples.
- [x] Validate the Compose profiles and pull-only deployment manifest.
- [x] Build and smoke-test production and development Docker targets.
- [x] Add Makefile shortcuts for profile lifecycle, validation, and GHCR publish.
- [x] Record operator commands, security boundaries, and rollback guidance.

## Validation notes

- `docker compose config` passed for development and production profiles in
  `docker-compose.yml`, plus the pull-only `production.yml` manifest.
- The Compose production profile built and smoke-tested the production image;
  the development profile also built successfully.
- Production image imported `app.main` successfully and reports the non-root
  runtime command and `/health/db` healthcheck.
- The development image ran the full suite with a valid test key: `226 passed`.
- Two unrelated learning-progress file tests remain failing outside the
  containerization changes: one instructor authorization assertion and one file
  repository lookup assertion.
- The host environment's direct full-suite command could not collect
  `asyncssh`; the Docker development image installs that declared dependency.
