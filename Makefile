
.PHONY: clean develop build tests black tests_coverage

develop:
	uv sync --active

build:
	uv build

clean:
	rm -rf dist

tests:
	uv run --with pytest pytest

black:
	uv run --with black black -l 82 fluidfoam

tests_coverage:
	uv run --with coverage coverage run -p -m unittest discover
	uv run --with coverage coverage combine
	uv run --with coverage coverage report
	uv run --with coverage coverage html
	uv run --with coverage coverage xml
	@echo "Code coverage analysis complete. View detailed report:"
	@echo "file://${PWD}/.coverage/index.html"
