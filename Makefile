
pip-tools:
	pip install -U pip
	pip install -U poetry

# poetry add poetry-plugin-up --group dev

# install-plugin:
# 	poetry self add poetry-plugin-up

install-requirements: pip-tools
	poetry install

install-check:
	poetry run pre-commit install
	poetry run pre-commit install-hooks

install: install-requirements install-check
	echo "Done"

test:
	poetry run python manage.py test

i18n-collect:
	poetry run python manage.py makemessages --all --no-location --ignore=env --no-obsolete --no-wrap

i18n: i18n-collect
	poetry run python manage.py compilemessages
	git add survey/locale

release:
	poetry build
	poetry run twine upload --verbose dist/*

check:
	poetry run pre-commit run --show-diff-on-failure --color=always --all-files
