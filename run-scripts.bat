mypy multiformats
@pause
pylint multiformats
@pause
pdoc --config latex_math=True --config show_type_annotations=True --force --html --output-dir docs multiformats
@pause
pytest test --cov=./multiformats
coverage html
@pause
