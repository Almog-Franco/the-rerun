# Own venv: the system Python on many machines has a broken numpy/pandas pair,
# and nothing here needs either.
VENV := .venv
PIP  := $(VENV)/bin/pip

.PHONY: all up down venv install reset load api test clean

all: up install reset load
	@echo ""
	@echo "Ready. Start the API with:  make api"

up:
	docker compose up -d --wait
	@echo "postgres ready on localhost:5433"

down:
	docker compose down -v

venv:
	@test -d $(VENV) || python3 -m venv $(VENV)

install: venv
	@$(PIP) install -q --upgrade pip
	@$(PIP) install -q -r requirements.txt
	@echo "python deps installed"

reset:
	@./bin/pipeline reset

load:
	@./bin/pipeline run --all

api:
	$(VENV)/bin/uvicorn api.main:app --port 8080 --reload

test:
	$(VENV)/bin/pytest

clean: down
	rm -rf $(VENV) .pytest_cache **/__pycache__
