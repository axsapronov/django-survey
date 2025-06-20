
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