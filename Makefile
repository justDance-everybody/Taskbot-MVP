# Feishu Bot Makefile

.PHONY: help install install-dev test test-unit test-int test-e2e lint format type-check clean dev build run docker-build docker-run setup-env

# Default target
help:
	@echo "Available commands:"
	@echo "  install      - Install production dependencies"
	@echo "  install-dev  - Install development dependencies"
	@echo "  test         - Run all tests (unit + integration)"
	@echo "  test-unit    - Run unit tests only"
	@echo "  test-int     - Run integration tests only"
	@echo "  test-e2e     - Run end-to-end tests"
	@echo "  lint         - Run code linting"
	@echo "  format       - Format code with black and isort"
	@echo "  type-check   - Run type checking with mypy"
	@echo "  clean        - Clean up temporary files"
	@echo "  dev          - Start development server"
	@echo "  build        - Build the application"
	@echo "  run          - Run the application"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-run   - Run Docker container"
	@echo "  setup-env    - Setup environment files"

# Installation
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt
	pre-commit install

# Testing
test: test-unit test-int

test-unit:
	pytest tests/unit/ -v --cov=app --cov-report=term-missing --cov-report=html

test-int:
	pytest tests/integration/ -v --cov=app --cov-append --cov-report=term-missing

test-e2e:
	pytest tests/e2e/ -v

test-coverage:
	pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html --cov-report=xml

# Code quality
lint:
	flake8 app tests
	black --check app tests
	isort --check-only app tests

format:
	black app tests
	isort app tests

type-check:
	mypy app --ignore-missing-imports

# Security
security:
	bandit -r app -f json -o bandit-report.json
	safety check --json --output safety-report.json

# Cleanup
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/

# Development
dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-with-ngrok:
	@echo "Starting development server with ngrok..."
	@echo "Make sure ngrok is installed and configured"
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
	ngrok http 8000

# Production
build:
	python -m build

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000

# Docker
docker-build:
	docker build -t feishu-bot:latest .

docker-run:
	docker run -p 8000:8000 --env-file .env feishu-bot:latest

docker-dev:
	docker-compose up --build

docker-down:
	docker-compose down

# Environment setup
setup-env:
	@if [ ! -f .env ]; then \
		echo "Creating .env file from template..."; \
		cp .env.example .env; \
		echo "Please edit .env file with your actual configuration"; \
	else \
		echo ".env file already exists"; \
	fi
	@if [ ! -f config.yaml ]; then \
		echo "Creating config.yaml file from template..."; \
		cp config.yaml.example config.yaml; \
		echo "Please edit config.yaml file with your actual configuration"; \
	else \
		echo "config.yaml file already exists"; \
	fi

# Database operations (for future use)
db-init:
	@echo "Database initialization would go here"

db-migrate:
	@echo "Database migration would go here"

db-reset:
	@echo "Database reset would go here"

# Deployment
deploy-staging:
	@echo "Deploying to staging environment..."
	@echo "This would typically include:"
	@echo "- Building Docker image"
	@echo "- Pushing to registry"
	@echo "- Updating staging deployment"

deploy-prod:
	@echo "Deploying to production environment..."
	@echo "This would typically include:"
	@echo "- Building Docker image"
	@echo "- Pushing to registry"
	@echo "- Updating production deployment"
	@echo "- Running health checks"

# Monitoring and logs
logs:
	@echo "Fetching application logs..."
	docker-compose logs -f app

health-check:
	@echo "Running health check..."
	curl -f http://localhost:8000/health || exit 1

# Development utilities
shell:
	python -c "import IPython; IPython.embed()"

notebook:
	jupyter notebook

# Pre-commit hooks
pre-commit:
	pre-commit run --all-files

# Documentation
docs:
	@echo "Generating documentation..."
	@echo "This would generate API documentation"

# All-in-one setup for new developers
setup: setup-env install-dev
	@echo "Setup complete!"
	@echo "Next steps:"
	@echo "1. Edit .env and config.yaml with your configuration"
	@echo "2. Run 'make test' to verify everything works"
	@echo "3. Run 'make dev' to start development server"

# Quick development workflow
quick-test: format lint test-unit

# Full CI pipeline locally
ci: clean install-dev lint type-check test security
	@echo "Local CI pipeline completed successfully!"
