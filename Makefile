.PHONY: up down seed demo test eval lint clean

VENV ?= .venv
PYTHON ?= $(VENV)/bin/python
PYTEST ?= $(VENV)/bin/pytest
RUFF ?= $(VENV)/bin/ruff

up:
	docker compose up -d

down:
	docker compose down

seed:
	$(PYTHON) -m backend.app.sim.world

demo:
	$(PYTHON) -m backend.app.eval.demo

test:
	$(PYTEST) backend/tests -v

eval:
	$(PYTHON) -m backend.app.eval.harness

lint:
	$(RUFF) check backend
	$(RUFF) format --check backend

clean:
	rm -rf __pycache__ .pytest_cache *.pyc backend/**/__pycache__
