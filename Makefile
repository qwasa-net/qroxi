#
tea:
	python3 -m qroxi --resplit

#
clean:
	find . -name '*.pyc' -delete

#
dev-venv:
	python3 -m venv .venv --clear
	.venv/bin/pip install -U pip

dev-install: dev-venv
	.venv/bin/pip install -U black ruff isort

dev-format: dev-install
	.venv/bin/isort qroxi
	.venv/bin/black qroxi

dev-lint: dev-format
	.venv/bin/ruff check qroxi