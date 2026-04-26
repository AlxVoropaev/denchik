.PHONY: help up down logs backend-shell frontend-shell test test-backend test-frontend e2e build clean

help:
	@echo "Targets:"
	@echo "  up              — start backend + frontend (docker compose up)"
	@echo "  down            — stop containers"
	@echo "  logs            — tail logs"
	@echo "  test            — run all tests (backend + frontend)"
	@echo "  test-backend    — pytest inside backend container"
	@echo "  test-frontend   — vitest inside frontend container"
	@echo "  e2e             — Playwright e2e tests"
	@echo "  backend-shell   — bash inside backend container"
	@echo "  frontend-shell  — bash inside frontend container"
	@echo "  clean           — remove volumes and built images"

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

build:
	docker compose build

test: test-backend test-frontend

test-backend:
	docker compose run --rm backend pytest

test-frontend:
	docker compose run --rm frontend npm test -- --run

e2e:
	docker compose run --rm frontend npm run e2e

backend-shell:
	docker compose run --rm backend bash

frontend-shell:
	docker compose run --rm frontend bash

clean:
	docker compose down -v --rmi local
	rm -rf data/*.db data/attachments
