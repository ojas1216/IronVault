.PHONY: help install dev build test deploy clean logs

# ─── Colors ───────────────────────────────────────────────────────────────────
BOLD  := $(shell tput bold 2>/dev/null || echo '')
RESET := $(shell tput sgr0 2>/dev/null || echo '')
GREEN := $(shell tput setaf 2 2>/dev/null || echo '')
CYAN  := $(shell tput setaf 6 2>/dev/null || echo '')

help: ## Show this help
	@echo ""
	@echo "$(BOLD)Enterprise MDM System$(RESET)"
	@echo "$(CYAN)──────────────────────────────────────────────$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""

# ─── Setup ────────────────────────────────────────────────────────────────────

install: ## Install all dependencies (backend + dashboard)
	@echo "$(BOLD)Installing backend dependencies...$(RESET)"
	cd backend && pip install -r requirements.txt
	@echo "$(BOLD)Installing dashboard dependencies...$(RESET)"
	cd admin_dashboard && npm install
	@echo "$(BOLD)Installing desktop agent dependencies...$(RESET)"
	cd desktop_agent && pip install -r requirements.txt

env: ## Copy .env.example to .env
	@if [ ! -f .env ]; then \
	  cp .env.example .env; \
	  echo "$(GREEN).env created — fill in your secrets$(RESET)"; \
	else \
	  echo ".env already exists — skipping"; \
	fi

# ─── Development ─────────────────────────────────────────────────────────────

dev: ## Start all services in development mode
	@echo "$(BOLD)Starting dev environment...$(RESET)"
	docker-compose -f docker-compose.yml up postgres redis -d
	@sleep 3
	$(MAKE) dev-backend &
	$(MAKE) dev-dashboard

dev-backend: ## Start backend only (hot reload)
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-dashboard: ## Start admin dashboard only (Vite HMR)
	cd admin_dashboard && npm run dev

migrate: ## Run database migrations
	cd backend && alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create MSG="add column")
	cd backend && alembic revision --autogenerate -m "$(MSG)"

# ─── Build ───────────────────────────────────────────────────────────────────

build: ## Build all Docker images
	docker-compose build --no-cache

build-backend: ## Build backend Docker image only
	docker-compose build --no-cache backend

build-dashboard: ## Build dashboard Docker image only
	docker-compose build --no-cache dashboard

# ─── Testing ─────────────────────────────────────────────────────────────────

test: ## Run all tests
	$(MAKE) test-backend
	$(MAKE) test-dashboard

test-backend: ## Run backend tests (pytest)
	cd backend && pytest tests/ -v --cov=app --cov-report=term-missing

test-dashboard: ## Run dashboard tests (jest)
	cd admin_dashboard && npm test -- --watchAll=false

test-security: ## Run OWASP security scan
	cd backend && bandit -r app/ -ll
	cd backend && pip-audit

# ─── Production ──────────────────────────────────────────────────────────────

deploy: ## Deploy with Docker Compose (production)
	docker-compose pull
	docker-compose up -d --remove-orphans

deploy-ssl: ## Deploy with SSL (requires nginx/ssl certs)
	docker-compose -f docker-compose.yml -f docker-compose.ssl.yml up -d

down: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

# ─── Utilities ───────────────────────────────────────────────────────────────

logs: ## Tail logs from all services
	docker-compose logs -f

logs-backend: ## Tail backend logs
	docker-compose logs -f backend

lint: ## Lint backend (ruff) + dashboard (eslint)
	cd backend && ruff check app/
	cd admin_dashboard && npm run lint

format: ## Format code (black + prettier)
	cd backend && black app/
	cd admin_dashboard && npx prettier --write src/

clean: ## Remove build artifacts, caches, __pycache__
	find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find backend -name "*.pyc" -delete 2>/dev/null || true
	find backend -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf admin_dashboard/dist admin_dashboard/node_modules/.cache
	docker system prune -f

health: ## Check health of all running services
	@curl -s http://localhost:8000/health | python3 -m json.tool || echo "Backend not running"
	@curl -s http://localhost:3000 -o /dev/null -w "Dashboard: HTTP %{http_code}\n" || echo "Dashboard not running"

seed: ## Seed the database with demo data
	cd backend && python -m scripts.seed_demo_data

backup-db: ## Backup PostgreSQL database
	docker-compose exec postgres pg_dump -U $${POSTGRES_USER:-mdm_user} $${POSTGRES_DB:-mdm_db} \
	  > backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)Backup created!$(RESET)"
