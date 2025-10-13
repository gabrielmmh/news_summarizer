.PHONY: help setup start stop restart logs clean test

help:
	@echo "Available commands:"
	@echo "  make setup    - Setup environment and create .env file"
	@echo "  make start    - Start all services"
	@echo "  make stop     - Stop all services"
	@echo "  make restart  - Restart all services"
	@echo "  make logs     - Show logs"
	@echo "  make clean    - Clean up containers and volumes"
	@echo "  make test     - Run tests"

setup:
	@echo "Setting up environment..."
	@cp -n .env.example .env || true
	@echo "Please edit .env file with your configuration"
	@mkdir -p logs data

start:
	@echo "Starting services..."
	docker-compose up -d
	@echo "Services started!"
	@echo "Airflow UI: http://localhost:8080 (airflow/airflow)"
	@echo "MinIO UI: http://localhost:9001 (minioadmin/minioadmin)"

stop:
	@echo "Stopping services..."
	docker-compose down

restart:
	@echo "Restarting services..."
	docker-compose restart

logs:
	docker-compose logs -f

logs-airflow:
	docker-compose logs -f airflow-webserver airflow-scheduler

clean:
	@echo "Cleaning up..."
	docker-compose down -v
	@echo "Cleaned up containers and volumes"

test:
	@echo "Running tests..."
	pytest tests/ -v

install-deps:
	pip install -r requirements.txt

crawl-test-istoe:
	python -m src.crawlers.istoe_crawler

crawl-test-moneytimes:
	python -m src.crawlers.moneytimes_crawler
