# EstimatApp - Makefile
# Equivalente a npm scripts en package.json

.PHONY: help install dev start test test-v lint format check coverage clean all

# Comando por defecto - muestra ayuda
help:
	@echo "EstimatApp - Comandos disponibles:"
	@echo ""
	@echo "  make install    - Instala dependencias del proyecto"
	@echo "  make dev        - Inicia servidor en modo desarrollo (hot reload)"
	@echo "  make start      - Inicia servidor en modo produccion"
	@echo "  make test       - Ejecuta todos los tests"
	@echo "  make test-v     - Ejecuta tests con salida detallada"
	@echo "  make lint       - Verifica el codigo con ruff"
	@echo "  make format     - Formatea el codigo con ruff"
	@echo "  make check      - Ejecuta lint + tests (CI)"
	@echo "  make coverage   - Ejecuta tests con reporte de cobertura"
	@echo "  make clean      - Limpia archivos temporales"
	@echo "  make all        - Ejecuta format + lint + coverage"
	@echo ""

# Instalar dependencias
install:
	uv sync --all-extras

# Servidor de desarrollo con hot reload
dev:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Servidor de produccion
start:
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

# Tests
test:
	uv run pytest

# Tests con salida detallada
test-v:
	uv run pytest -v

# Linting
lint:
	uv run ruff check .

# Formateo de codigo
format:
	uv run ruff format .

# Verificacion completa (para CI)
check: lint test

# Cobertura de tests
coverage:
	uv run pytest --cov=app --cov-report=term-missing --cov-report=html

# Limpiar archivos temporales
clean:
	@if exist __pycache__ rd /s /q __pycache__
	@if exist .pytest_cache rd /s /q .pytest_cache
	@if exist htmlcov rd /s /q htmlcov
	@if exist .coverage del /f .coverage
	@for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
	@echo Limpieza completada

# Ejecutar todo (formato + lint + cobertura)
all: format lint coverage
