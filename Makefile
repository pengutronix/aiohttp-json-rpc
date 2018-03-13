PYTHON=python3.5
PYTHON_VENV=env

$(PYTHON_VENV)/.created: REQUIREMENTS.dev.txt
	rm -rf $(PYTHON_VENV) && \
	$(PYTHON) -m venv $(PYTHON_VENV) && \
	. $(PYTHON_VENV)/bin/activate && \
	pip install -r ./REQUIREMENTS.dev.txt && \
	date > $(PYTHON_VENV)/.created

env: $(PYTHON_VENV)/.created

clean:
	rm -rf $(PYTHON_VENV)

edit: env
	. $(PYTHON_VENV)/bin/activate && \
	$$EDITOR

shell: env
	. $(PYTHON_VENV)/bin/activate && \
	ipython
