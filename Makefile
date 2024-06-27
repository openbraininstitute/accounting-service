SHELL := /bin/bash

export ENVIRONMENT ?= dev
export APP_NAME := accounting-service
export APP_VERSION := $(shell git describe --abbrev --dirty --always --tags)
export COMMIT_SHA := $(shell git rev-parse HEAD)
export IMAGE_NAME ?= $(APP_NAME)
export IMAGE_TAG ?= $(APP_VERSION)-$(ENVIRONMENT)

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-23s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies into .venv
	pdm install --no-self

compile-deps:  ## Create or update the lock file, without upgrading the version of the dependencies
	pdm lock --update-reuse

upgrade-deps:  ## Create or update the lock file, using the latest version of the dependencies
	pdm lock

check-deps:  ## Check that the dependencies in the existing lock file are valid
	pdm lock --check

format:  # Run formatters
	pdm run python -m ruff format
	pdm run python -m ruff check --fix

lint:  ## Run linters
	pdm run python -m ruff format --check
	pdm run python -m ruff check
	pdm run python -m mypy app

build:  ## Build the docker images
	docker compose build app

run: export COMPOSE_PROFILES=run
run: build  ## Run the application in docker
	docker compose up --watch --remove-orphans

kill: export COMPOSE_PROFILES=run,test
kill:  ## Take down the application and remove the volumes
	docker compose down --remove-orphans --volumes

clean: export COMPOSE_PROFILES=run,test
clean: ## Take down the application and remove the volumes and the images
	docker compose down --remove-orphans --volumes --rmi all

test: build  ## Run tests in docker
	docker compose run --rm test

test-local: export DB_HOST=127.0.0.1
test-local: export DB_PORT=5434
test-local: export AWS_DEFAULT_REGION=us-east-1
test-local: export AWS_ENDPOINT_URL=http://127.0.0.1:9324
test-local:  ## Run tests locally
	docker compose up --wait db-test
	pdm run python -m alembic upgrade head
	pdm run python -m pytest

migration: export DB_HOST=127.0.0.1
migration: export DB_PORT=5433
migration:  ## Create the alembic migration
	docker compose up --wait db
	pdm run python -m alembic upgrade head
	pdm run python -m alembic revision --autogenerate

show-config: export COMPOSE_PROFILES=run,test
show-config:  ## Show the docker-compose configuration in the current environment
	docker compose config

sh: build  ## Run a shell in the app container
	docker compose run --rm app bash
