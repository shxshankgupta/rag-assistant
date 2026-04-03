.PHONY: help install dev run test test-cov lint format docker-build docker-up docker-down migrate

help:
	@echo ""
	@echo "  RAG Knowledge Assistant — Dev Commands"
	@echo "  ─────────────────────────────────────────"
	@echo "  make install      Install all dependencies"
	@echo "  make dev          Run dev server with hot-reload"
	@echo "  make worker       Run Celery worker (needs Redis)"
	@echo "  make run          Run production server"
	@echo "  make test         Run test suite"
	@echo "  make test-cov     Run tests with coverage report"
	@echo "  make lint         Run ruff linter"
	@echo "  make format       Auto-format code with ruff"
	@echo "  make migrate      Run Alembic migrations"
	@echo "  make docker-build Build Docker image"
	@echo "  make docker-up    Start with docker-compose"
	@echo "  make docker-down  Stop docker-compose services"
	@echo ""

install:
	pip install --upgrade pip
	pip install -r requirements.txt
	pip install pytest pytest-asyncio pytest-cov httpx ruff

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-config /dev/null

worker:
	celery -A app.workers.celery_app worker -l INFO

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html

lint:
	ruff check app/ tests/

format:
	ruff format app/ tests/
	ruff check --fix app/ tests/

migrate:
	alembic upgrade head

migrate-create:
	@read -p "Migration name: " name; alembic revision --autogenerate -m "$$name"

docker-build:
	docker build -t rag-assistant:latest .

docker-up:
	docker-compose up --build -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f api

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -type f -name "*.pyc" -delete 2>/dev/null; true
	rm -rf .pytest_cache htmlcov .coverage
