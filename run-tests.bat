@echo off
mypy multiformats
pylint multiformats
pytest test --cov=./multiformats
coverage html
@pause
