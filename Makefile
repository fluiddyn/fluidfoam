
.PHONY: clean clean_all develop

develop:
	python -m build
	pip install dist/fluidfoam*.whl --user

clean:
	rm -rf dist

tests:
	python -m unittest discover

black:
	black -l 82 fluidfoam

tests_coverage:
	mkdir -p .coverage
	coverage run -p -m unittest discover
	coverage combine
	coverage report
	coverage html
	coverage xml
	@echo "Code coverage analysis complete. View detailed report:"
	@echo "file://${PWD}/.coverage/index.html"
