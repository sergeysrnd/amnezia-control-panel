.PHONY: install test lint build dev-api dev-api-manage dev-web

install:
	cd backend && uv sync --dev
	cd frontend && npm ci

test:
	cd backend && uv run pytest -q
	cd frontend && npm test

lint:
	cd backend && uv run ruff check . ../tools
	cd frontend && npm run lint

build:
	cd frontend && npm run build

dev-api:
	cd backend && uv run uvicorn amnezia_panel.main:app --host 127.0.0.1 --port 8000 --reload

dev-api-manage:
	cd backend && AMNEZIA_ENABLE_MUTATIONS=true uv run uvicorn amnezia_panel.main:app --host 127.0.0.1 --port 8000

dev-web:
	cd frontend && npm run dev
