PYTHON ?= python3
PIP ?= pip
MAYBE_UV = uv
PIP_COMPILE = uv pip compile

# Core paths
PACKAGES_PATH=$(PWD)/packages
PY_VENV=$(PWD)/venv
PY_VENV_REL_PATH=$(subst $(PWD)/,,$(PY_VENV))

# Python execution
PY_PATH=$(PWD)
RUN_PY = PYTHONPATH=$(PY_PATH) $(PYTHON) -m

# Formatting and linting
PY_FIND_COMMAND = find . -name '*.py' | grep -vE "($(PY_VENV_REL_PATH))"
BLACK_CMD = $(RUN_PY) black --line-length 100 $(shell $(PY_FIND_COMMAND))
MYPY_CONFIG=$(PY_PATH)/mypy_config.ini

init:
	@if [ -d "$(PY_VENV_REL_PATH)" ]; then \
		echo "\033[33mVirtual environment already exists\033[0m"; \
	else \
		$(PYTHON) -m venv $(PY_VENV_REL_PATH); \
	fi
	@echo "\033[0;32mRun 'source $(PY_VENV_REL_PATH)/bin/activate' to activate the virtual environment\033[0m"

install:
	$(PIP) install --upgrade pip
	$(PIP) install uv
	$(PIP_COMPILE) --strip-extras --output-file=$(PACKAGES_PATH)/requirements.txt $(PACKAGES_PATH)/base_requirements.in
	$(MAYBE_UV) pip install -r $(PACKAGES_PATH)/requirements.txt

install_dev:
	$(PIP) install --upgrade pip
	$(PIP) install uv
	$(PIP_COMPILE) --strip-extras --output-file=$(PACKAGES_PATH)/requirements-dev.txt $(PACKAGES_PATH)/base_requirements.in $(PACKAGES_PATH)/dev_requirements.in
	$(MAYBE_UV) pip install -r $(PACKAGES_PATH)/requirements-dev.txt

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

upgrade: install
	$(MAYBE_UV) pip install --upgrade $$(pip freeze | awk '{split($$0, a, "=="); print a[1]}')
	$(MAYBE_UV) pip freeze > $(PACKAGES_PATH)/requirements.txt

release:
	@echo "\033[0;32mCreating version $(PYPY_VERSION_ARG)\033[0m"
	echo $(PYPY_VERSION_ARG) > VERSION
	git add VERSION
	git commit -m "Release $(PYPY_VERSION_ARG)"
	git push
	git tag -l $(PYPY_VERSION_ARG) | grep -q $(PYPY_VERSION_ARG) || git tag $(PYPY_VERSION_ARG)
	git push origin $(PYPY_VERSION_ARG)
	sleep 5
	gh release create $(PYPY_VERSION_ARG) --notes "Release $(PYPY_VERSION_ARG)" --latest --verify-tag
	@echo "\033[0;32mDONE!\033[0m"

clean:
	rm -rf $(PY_VENV)
	rm -rf .ruff_cache
	rm -rf .mypy_cache
	rm -rf .coverage

.PHONY: init install install_dev format check_format mypy pylint autopep8 isort lint test upgrade release clean
