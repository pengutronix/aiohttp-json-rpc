PYTHON=python3
PYTHON_VENV=env

all: server

$(PYTHON_VENV)/.created: REQUIREMENTS.txt
	rm -rf $(PYTHON_VENV) && \
	$(PYTHON) -m venv $(PYTHON_VENV) && \
	. $(PYTHON_VENV)/bin/activate && \
	pip install -r ./REQUIREMENTS.txt && \
	date > $(PYTHON_VENV)/.created

env: $(PYTHON_VENV)/.created

clean:
	rm -rf $(PYTHON_VENV)

db.sqlite3: env
	. $(PYTHON_VENV)/bin/activate && \
	./manage.py migrate && \
	./manage.py createsuperuser

server: | db.sqlite3
	. $(PYTHON_VENV)/bin/activate && \
	./manage.py runserver
