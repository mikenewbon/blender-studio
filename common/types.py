from typing import TypeVar, Type

T = TypeVar('T', bound=object)


def assert_cast(typ: Type[T], val: object) -> T:
    assert isinstance(val, typ)
    return val
