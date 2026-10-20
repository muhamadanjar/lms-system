# LMS container release

Plan: [../../plans/lms-container-release.md](../../plans/lms-container-release.md)  
Progress: [../../progress/lms-container-release.md](../../progress/lms-container-release.md)

## Makefile shortcuts

The root `Makefile` wraps the same Compose profiles and release image contract:

```sh
make docker-up-dev
make docker-build-prod
make docker-migrate-prod
make docker-up-prod
make docker-config-dev
make docker-config-prod
make docker-login-ghcr
make docker-publish
```

Override `DEV_ENV_FILE`, `PROD_ENV_FILE`, `VERSION`, `GHCR_OWNER`, or
`GHCR_IMAGE` when using a different environment file, release version, or
registry namespace.

## Development profile

```sh
cp .env.docker.example .env.docker
# Edit DATABASE__URL, SSH_CREDENTIAL_ENC_KEY, and User Management settings.
docker compose --env-file .env.docker --profile development -f docker-compose.yml up --build lms-dev
```

The app listens on `http://localhost:${LMS_API_PORT:-8000}`. The database must
already be reachable on the host at the address in `DATABASE__URL`; the Compose
service maps `host.docker.internal` to the Docker host. Uploaded private files
are bind-mounted at `var/private-files`.

Stop the development profile with:

```sh
docker compose --env-file .env.docker --profile development -f docker-compose.yml down
```

## Production build profile

The main Compose file mirrors the tileserver pattern. Its `production` profile
builds the `production` Dockerfile stage and tags the resulting local image.
The database, User Management API, and S3-compatible storage remain external.

```sh
cp .env.production.example .env.production
# Set VERSION/LMS_IMAGE and fill all external service values.
docker compose --env-file .env.production --profile production -f docker-compose.yml build lms
docker compose --env-file .env.production --profile production -f docker-compose.yml run --rm migrate
docker compose --env-file .env.production --profile production -f docker-compose.yml up -d lms
```

`LMS_IMAGE` must be a version tag such as
`ghcr.io/example/lms-system:1.2.3`; it has no `latest` fallback. The profile
forces `FILE_STORAGE_BACKEND=s3` and does not create a local storage volume.

## Pull-only production deployment

`production.yml` is the deployment manifest for hosts that should only pull an
already-published GHCR image:

```sh
cp .env.production.example .env.production
docker login ghcr.io

docker compose --env-file .env.production -f production.yml pull
docker compose --env-file .env.production -f production.yml run --rm migrate
docker compose --env-file .env.production -f production.yml up -d lms
```

To roll back, set `LMS_IMAGE` to a previously published version, pull it, run
the required migration compatibility check, and restart the app.

## Release workflow

Push a Conventional Commit to `main` or `master`. The workflow runs regression
tests, semantic-release, and only then builds the Dockerfile `production`
target used by the Compose production profile. It publishes:

- `ghcr.io/<repository-owner>/lms-system:X.Y.Z`
- `ghcr.io/<repository-owner>/lms-system:latest`

The image is `linux/amd64`, uses the built-in GitHub token, and includes OCI
source/version/revision metadata, BuildKit provenance, and an SBOM. The
workflow does not publish an image when semantic-release creates no release.

## Validation

The workflow validates the development profile, production build profile, and
pull-only deployment manifest using the example environment files. It does not
connect to a real database, S3 service, or authentication service in CI.
