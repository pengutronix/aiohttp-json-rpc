.PHONY: help
help:
	@echo "Run 'make release-to-pypi' or 'make dist'"

.PHONY: release-to-pypi
release-to-pypi:
	python -m setup release
	twine upload dist/*

.PHONY: dist
dist:
	python -m setup dist
