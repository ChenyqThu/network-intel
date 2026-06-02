# Network Intel (nintel) — local dev orchestration
# Backend: apps/api (FastAPI, :8000)   Frontend: apps/web (Vite, :5173)

.PHONY: help api-install web-install install api web build test api-test web-test pipeline clean

help:
	@echo "make install      - set up backend venv + frontend node_modules"
	@echo "make api          - run the FastAPI backend on :8000"
	@echo "make web          - run the Vite frontend on :5173 (proxies /api -> :8000)"
	@echo "make pipeline      - run engine: build daily + weekly report.json"
	@echo "make test         - run backend + frontend test suites"
	@echo "make build        - production build of the frontend"

api-install:
	cd apps/api && python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/pip install -e . && .venv/bin/python -m nintel.pipeline seed --reset

web-install:
	cd apps/web && npm install

install: api-install web-install

api:
	cd apps/api && .venv/bin/python -m uvicorn nintel.api.app:app --reload --port 8000

web:
	cd apps/web && npm run dev

pipeline:
	cd apps/api && .venv/bin/python -m nintel.pipeline build --type daily && .venv/bin/python -m nintel.pipeline build --type weekly

api-test:
	cd apps/api && .venv/bin/python -m pytest -q

web-test:
	cd apps/web && npm run test -- --run

test: api-test web-test

build:
	cd apps/web && npm run build
