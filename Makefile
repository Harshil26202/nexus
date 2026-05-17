.PHONY: help dev down build migrate seed logs clean test lint format

DOCKER_COMPOSE = docker compose
BACKEND_DIR = ./backend
FRONTEND_DIR = ./frontend

help:
	@echo "NEXUS — AI-Native Engineering Intelligence Platform"
	@echo ""
	@echo "  make dev        Start full stack (all services)"
	@echo "  make down       Stop all services"
	@echo "  make build      Rebuild all Docker images"
	@echo "  make migrate    Run database migrations"
	@echo "  make seed       Seed demo data"
	@echo "  make logs       Tail all service logs"
	@echo "  make test       Run full test suite"
	@echo "  make lint       Lint backend + frontend"
	@echo "  make clean      Remove volumes and containers"

dev:
	cp -n .env.example .env 2>/dev/null || true
	$(DOCKER_COMPOSE) up --build -d
	@echo "✓ NEXUS running:"
	@echo "  Dashboard  → http://localhost:3000"
	@echo "  API        → http://localhost:8000"
	@echo "  API Docs   → http://localhost:8000/docs"
	@echo "  Grafana    → http://localhost:3001"
	@echo "  Prometheus → http://localhost:9090"

down:
	$(DOCKER_COMPOSE) down

build:
	$(DOCKER_COMPOSE) build --no-cache

migrate:
	$(DOCKER_COMPOSE) exec backend alembic upgrade head

seed:
	$(DOCKER_COMPOSE) exec backend python -m app.scripts.seed_demo_data

logs:
	$(DOCKER_COMPOSE) logs -f backend agent-worker frontend

logs-backend:
	$(DOCKER_COMPOSE) logs -f backend

logs-agents:
	$(DOCKER_COMPOSE) logs -f agent-worker

test:
	$(DOCKER_COMPOSE) exec backend pytest tests/ -v --tb=short
	cd $(FRONTEND_DIR) && npm run test

test-backend:
	$(DOCKER_COMPOSE) exec backend pytest tests/ -v

lint:
	$(DOCKER_COMPOSE) exec backend ruff check app/ && mypy app/
	cd $(FRONTEND_DIR) && npm run lint

format:
	$(DOCKER_COMPOSE) exec backend ruff format app/
	cd $(FRONTEND_DIR) && npm run format

clean:
	$(DOCKER_COMPOSE) down -v --remove-orphans
	docker system prune -f

shell-backend:
	$(DOCKER_COMPOSE) exec backend bash

shell-db:
	$(DOCKER_COMPOSE) exec postgres psql -U nexus nexus
