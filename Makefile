IMAGE_NAME ?= lms-system
VERSION ?= $(shell git tag --list '[0-9]*.[0-9]*.[0-9]*' --sort=-version:refname 2>/dev/null | head -n 1 | awk 'NF { print; found=1 } END { if (!found) print "0.0.0" }')
IMAGE_TAG := $(IMAGE_NAME):$(VERSION)
GHCR_OWNER ?= muhamadanjar
GHCR_IMAGE ?= ghcr.io/$(GHCR_OWNER)/$(IMAGE_NAME)
BUILD_CONTEXT := .
DEV_ENV_FILE ?= .env.docker
PROD_ENV_FILE ?= .env.production

COMPOSE_DEV := VERSION=$(VERSION) LMS_DOCKER_ENV_FILE=$(DEV_ENV_FILE) docker compose --env-file $(DEV_ENV_FILE)
COMPOSE_PROD := VERSION=$(VERSION) LMS_DOCKER_ENV_FILE=$(PROD_ENV_FILE) docker compose --env-file $(PROD_ENV_FILE)

.PHONY: docker-build docker-build-dev docker-build-prod docker-run \
	docker-login-ghcr check-release-version docker-publish \
	docker-config-dev docker-config-prod docker-up-dev docker-up-prod \
	docker-migrate-prod docker-down docker-down-prod

docker-build:
	docker build --target production --build-arg VERSION=$(VERSION) \
		-f docker/Dockerfile -t $(IMAGE_TAG) $(BUILD_CONTEXT)

docker-build-dev:
	docker build --target dev --build-arg VERSION=$(VERSION) \
		-f docker/Dockerfile -t $(IMAGE_NAME):dev $(BUILD_CONTEXT)

docker-build-prod:
	$(COMPOSE_PROD) --profile production build lms

docker-run:
	docker run --rm -p 8000:8000 $(IMAGE_TAG)

# Authenticate once with a GitHub token that can write packages before publishing.
docker-login-ghcr:
	docker login ghcr.io

# Publishing is restricted to a semantic version tag at HEAD.
check-release-version:
	@test "$(VERSION)" != "0.0.0" || (echo "No semantic Git tag found; set a release tag before publishing." >&2; exit 1)
	@git tag --points-at HEAD --list "$(VERSION)" | grep --fixed-strings --line-regexp "$(VERSION)" >/dev/null || (echo "VERSION=$(VERSION) must be a semantic Git tag pointing at HEAD." >&2; exit 1)

docker-publish: check-release-version
	docker buildx build --platform linux/amd64 \
		--build-arg VERSION=$(VERSION) \
		--file docker/Dockerfile \
		--target production \
		--tag $(GHCR_IMAGE):$(VERSION) \
		--tag $(GHCR_IMAGE):latest \
		--provenance=mode=max \
		--sbom=true \
		--push $(BUILD_CONTEXT)

docker-config-dev:
	$(COMPOSE_DEV) --profile development config

docker-config-prod:
	$(COMPOSE_PROD) --profile production config

docker-up-dev:
	$(COMPOSE_DEV) --profile development up --build lms-dev

docker-up-prod:
	$(COMPOSE_PROD) --profile production up --build --detach lms

docker-migrate-prod:
	$(COMPOSE_PROD) --profile production run --rm migrate

docker-down:
	$(COMPOSE_DEV) --profile development down

docker-down-prod:
	$(COMPOSE_PROD) --profile production down
