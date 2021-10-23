@echo off
mypy --strict multiformats
pylint multiformats
pytest test --cov=./multiformats
coverage html
@pause
