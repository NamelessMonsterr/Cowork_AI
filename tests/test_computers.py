import inspect

import pytest

from assistant.computer import Computer, WindowsComputer


def get_required_attrs():
    # TODO: migrate to a cleaner solution that allows type-checking (e.g. pydantic?)
    return [
        name
        for name, member in inspect.getmembers(Computer)
        if not name.startswith("__")
        and (inspect.isfunction(member) or isinstance(member, property))
    ]


# Test the actual available computers
all_computers = [WindowsComputer]


@pytest.mark.parametrize("computer_class", all_computers, ids=lambda c: c.__name__)
def test_computer_implements_interface(computer_class):
    for func in get_required_attrs():
        assert hasattr(
            computer_class, func
        ), f"{computer_class.__name__} is missing required attribute '{func}'"
