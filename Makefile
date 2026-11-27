# Open Voice Agent Studio — one entry point for every workflow. `make help` lists targets.
SHELL := /bin/sh
TEST_DB := postgresql+asyncpg://ovas:ovas@127.0.0.1:55432/ovas_test
PY_DIRS := packages services providers scripts .claude

.PHONY: help install dev up down check fmt lint typecheck test test-db gen gen-check e2e

help: ## List targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-11s %s\n", $$1, $$2}'

install: ## Install Python and JS dependencies
	uv sync
	pnpm install
	pnpm exec lefthook install

dev: ## Run the web app locally against the compose backend
	docker compose up -d --build api runtime tts-kokoro stt-whisper db
	pnpm dev

up: ## Build and start the whole stack
	docker compose up -d --build --wait

down: ## Stop the stack
	docker compose down

fmt: ## Format all code
	uv run ruff format $(PY_DIRS)
	uv run ruff check --fix $(PY_DIRS)
	pnpm exec prettier --write --log-level warn "apps/**/*.{ts,tsx,css,json}"

lint: ## Lint all code
	uv run ruff check $(PY_DIRS)
	uv run ruff format --check $(PY_DIRS)
	pnpm lint

typecheck: ## Typecheck Python and TypeScript
	uv run pyright
	pnpm typecheck

test-db: ## Start the throwaway test database
	docker compose --profile test up -d --wait db-test

test: test-db ## Run all tests
	OVAS_DATABASE_URL=$(TEST_DB) uv run pytest -q --cov --cov-report=term --cov-fail-under=80
	pnpm test

gen: ## Regenerate JSON Schema and TS types from ovas-core
	scripts/gen.sh

gen-check: ## Fail if generated files are stale
	scripts/gen.sh check

check: lint typecheck gen-check test ## Everything CI runs

E2E := docker compose -p ovas-e2e -f docker-compose.yml -f docker-compose.e2e.yml
E2E_WEB_PORT ?= 5173

e2e: ## Browser end-to-end tests against a throwaway stack with the stub LLM
	E2E_WEB_PORT=$(E2E_WEB_PORT) $(E2E) up -d --build --wait db stub-llm api runtime web
	@for i in $$(seq 1 60); do curl -sf http://localhost:$(E2E_WEB_PORT)/api/health >/dev/null && break; sleep 2; done
	E2E_WEB_PORT=$(E2E_WEB_PORT) pnpm --filter @ovas/web e2e; status=$$?; \
	  [ -n "$(KEEP)" ] || $(E2E) down -v; exit $$status
