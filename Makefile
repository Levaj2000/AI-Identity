# AI Identity — Development Commands
# Run `make help` to see all available targets.

.DEFAULT_GOAL := help
COMPOSE := docker compose

.PHONY: setup up down restart logs ps \
        shell-api shell-gw psql \
        migrate seed test clean help

# ── Setup ───────────────────────────────────────────────────────────────

setup: ## One-time: generate .env with security keys
	@bash scripts/docker-setup.sh

# ── Lifecycle ───────────────────────────────────────────────────────────

up: ## Build and start all services (detached)
	$(COMPOSE) up --build -d

down: ## Stop all services
	$(COMPOSE) down

restart: ## Restart all services
	$(COMPOSE) restart

# ── Observability ───────────────────────────────────────────────────────

logs: ## Tail API + Gateway logs
	$(COMPOSE) logs -f api gateway

ps: ## Show running containers
	$(COMPOSE) ps

# ── Shell Access ────────────────────────────────────────────────────────

shell-api: ## Open bash in API container
	$(COMPOSE) exec api bash

shell-gw: ## Open bash in Gateway container
	$(COMPOSE) exec gateway bash

psql: ## Open psql in Postgres container
	$(COMPOSE) exec db psql -U postgres ai_identity

# ── Database ────────────────────────────────────────────────────────────

migrate: ## Run Alembic migrations
	$(COMPOSE) exec api alembic upgrade head

seed: ## Seed sample agents and API keys
	$(COMPOSE) exec api python scripts/seed.py

# ── Testing ─────────────────────────────────────────────────────────────

test: ## Run pytest in API and Gateway containers
	$(COMPOSE) exec api pytest api/tests/ -v
	$(COMPOSE) exec gateway pytest gateway/tests/ -v

# ── Cleanup ─────────────────────────────────────────────────────────────

clean: ## Stop + remove volumes (⚠ destructive — deletes DB data)
	$(COMPOSE) down -v

# ── Help ────────────────────────────────────────────────────────────────

help: ## Show this help
	@echo ""
	@echo "AI Identity — Development Commands"
	@echo "───────────────────────────────────"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'
	@echo ""
