PYTHON ?= python3
PY_PATH=$(PWD)/src
RUN_PY = PYTHONPATH=$(PY_PATH) $(PYTHON) -m
BLACK_CMD = $(RUN_PY) black --line-length 100 .
# NOTE: exclude any virtual environment subdirectories here
PY_FIND_COMMAND = find -name '*.py' ! -path './venv/*'
MYPY_CONFIG=$(PY_PATH)/mypy_config.ini

init:
	$(PYTHON) -m venv venv

install:
	pip3 install -r requirements.txt

format: isort
	$(BLACK_CMD)

check_format:
	$(BLACK_CMD) --check --diff

mypy:
	$(RUN_PY) mypy $(shell $(PY_FIND_COMMAND)) --config-file $(MYPY_CONFIG) --no-namespace-packages

pylint:
	$(RUN_PY) pylint $(shell $(PY_FIND_COMMAND))

autopep8:
	autopep8 --in-place --aggressive --aggressive $(shell $(PY_FIND_COMMAND))

isort:
	isort $(shell $(PY_FIND_COMMAND))

lint: check_format mypy pylint

test:
	$(RUN_PY) unittest discover -s test -p *_test.py -v

release:
	@echo "\033[0;32mCreating version $(PYPY_VERSION_ARG)\033[0m"
	echo $(PYPY_VERSION_ARG) > VERSION
	git add VERSION
	git commit -m "Release $(PYPY_VERSION_ARG)"
	git push
	git tag -l $(PYPY_VERSION_ARG) | grep -q $(PYPY_VERSION_ARG) || git tag $(PYPY_VERSION_ARG)
	git push origin $(PYPY_VERSION_ARG)
	gh release create $(PYPY_VERSION_ARG) --notes "Release $(PYPY_VERSION_ARG)" --latest --verify-tag
	@echo "\033[0;32mDONE!\033[0m"

.PHONY: init install format check_format mypy pylint autopep8 isort lint test release
