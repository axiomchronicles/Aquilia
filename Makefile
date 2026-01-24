# Makefile for Aquilia development

.PHONY: help install test lint format clean dev run

help:
	@echo "Aquilia Development Commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Lint code"
	@echo "  make format     - Format code"
	@echo "  make clean      - Clean build artifacts"
	@echo "  make dev        - Run development server"
	@echo "  make run        - Run production server"

install:
	pip install -e ".[dev]"

test:
	pytest tests/ -v --cov=aquilia --cov-report=term-missing

test-fast:
	pytest tests/ -v -x

lint:
	@echo "Checking code style..."
	python -m py_compile aquilia/**/*.py

format:
	@echo "Formatting code..."
	@find aquilia -name "*.py" -type f -print0 | xargs -0 python -m autopep8 --in-place --aggressive --aggressive 2>/dev/null || true

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

dev:
	aq run --reload --log-level debug

run:
	python main.py

validate:
	aq validate

inspect:
	aq inspect

build:
	python setup.py sdist bdist_wheel

publish: clean build
	twine upload dist/*

install-dev:
	pip install -e ".[dev]"
	pip install black mypy pylint

setup:
	python -m venv env
	@echo "Run: source env/bin/activate"
