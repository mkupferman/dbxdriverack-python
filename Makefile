all: build

clean:
	rm -rf ./dist/ ./*.egg-info ./__pycache__/ ./*/__pycache__/ ./venv/

venv:
	python -m virtualenv venv

docs:
	source venv/bin/activate; \
	python -m pip install --upgrade '.[docs]'; \
	sphinx-apidoc -f -o docs/src src/dbxdriverack; \
	sphinx-build -M html docs/src docs/output

build: clean venv docs
	source venv/bin/activate; \
	python -m pip install --upgrade pip; \
	python -m pip install --upgrade build; \
	python -m build; \
	mypy . --strict --exclude=build/ --exclude=venv/ --exclude=tests/


develop: venv
	source venv/bin/activate; \
	python -m pip install --upgrade pip; \
	python -m pip install --editable '.[dev]'

install:
	python -m pip install .
