@echo off
mypy --strict multiformats
pylint --rcfile=.pylintrc --disable=fixme multiformats
pytest test --cov=./multiformats
coverage html
@pause
