
.PHONY: clean clean_all develop build_ext_inplace

develop:
	python setup.py develop

build_ext_inplace:
	python setup.py build_ext --inplace

clean:
	rm -rf build

tests:
	python -m unittest discover

tests_coverage:
	mkdir -p .coverage
	coverage run -p -m unittest discover
	coverage combine
	coverage report
	coverage html
	coverage xml
	@echo "Code coverage analysis complete. View detailed report:"
	@echo "file://${PWD}/.coverage/index.html"
