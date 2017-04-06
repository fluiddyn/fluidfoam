
.PHONY: clean clean_all develop build_ext_inplace

develop:
	python setup.py develop

build_ext_inplace:
	python setup.py build_ext --inplace

clean:
	rm -rf build

tests:
	python -m unittest discover
