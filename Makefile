.PHONY: help install install-py install-web test lint lint-web type-check build run-api run-web

PYTHON ?= python
NPM ?= npm

help:
	@echo "Report Navigator Developer Commands:"
	@echo "  make install     Install all dependencies (Python + Web) and generate sample PDF"
	@echo "  make test        Run pytest test suite"
	@echo "  make lint        Run frontend Next.js linter"
	@echo "  make type-check  Run TypeScript type checker on frontend"
	@echo "  make build       Build Next.js production frontend"
	@echo "  make run-api     Run FastAPI backend (port 8000)"
	@echo "  make run-web     Run Next.js development frontend (port 3000)"

install: install-py install-web
	$(PYTHON) create_sample_report.py

install-py:
	$(PYTHON) -m pip install -r requirements.txt

install-web:
	cd web && $(NPM) install

test:
	$(PYTHON) -m pytest -v

lint:
	cd web && $(NPM) run lint

type-check:
	cd web && npx tsc --noEmit

build:
	cd web && $(NPM) run build

run-api:
	$(PYTHON) -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload

run-web:
	cd web && $(NPM) run dev
