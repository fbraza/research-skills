from {{ cookiecutter.package_name }}.definitions import defs


def test_definitions_load() -> None:
    assert defs is not None
