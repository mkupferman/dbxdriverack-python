all: build

clean:
	rm -rf ./dist/ ./*.egg-info ./__pycache__/ ./*/__pycache__/ ./venv/

venv:
	python3 -m venv venv

docs:
	source venv/bin/activate; \
	python3 -m pip install --upgrade '.[docs]'; \
	sphinx-apidoc -f -o docs/src src/dbxdriverack; \
	sphinx-build -M html docs/src docs/output

validate:
	source venv/bin/activate; \
	python3 -m pip install --upgrade '.[validate]'

build: clean venv docs validate
	source venv/bin/activate; \
	python3 -m pip install --upgrade pip; \
	python3 -m pip install --upgrade build; \
	python3 -m build; \
	mypy . --strict --exclude=build/ --exclude=venv/ --exclude=tests/


develop: venv validate
	source venv/bin/activate; \
	python3 -m pip install --upgrade pip; \
	python3 -m pip install --editable '.[dev]'

install:
	python3 -m pip install .
