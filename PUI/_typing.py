"""Shared annotation vocabulary; no backend imports or runtime validation."""
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence, TypeVar, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from .node import PUINode

NodeT = TypeVar('NodeT', bound='PUINode')
T = TypeVar('T')
Number = Union[int, float]
Insets = Union[Number, Sequence[Number]]
Point = Sequence[Number]
Points = Iterable[Point]
Callback = Callable[..., object]
Choices = Union[Mapping[Any, Any], Sequence[Any]]


class Binding(Protocol[T]):
    @property
    def value(self) -> T: ...

    @value.setter
    def value(self, value: T) -> None: ...


class Poster(Protocol):
    def __call__(self, callback: Callable[[], object], *, delay: Number = 0) -> None: ...
