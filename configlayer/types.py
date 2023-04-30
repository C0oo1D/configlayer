"""Config layer type annotations and other types"""
from __future__ import annotations
from ast import literal_eval
from typing import Any, Iterable, Sequence, NamedTuple, TypeVar, Callable, TypeAlias
from pathlib import Path
from dataclasses import dataclass


__all__ = ('path_t', 'state_t', 'holder_t', 'mb_holder_t', 'fields_t', 'on_set_t',
           'ClsObj', 'ItemError', 'ValidWrong', 'Field')


T = TypeVar('T')

path_t = str | Path                             # Generic path type
state_t = bool | None                           # State is bool or None
holder_t = Iterable[T] | Sequence[T]            # Any objects holder type (__iter__ or __getitem__)

# bug mypy #14824: TypeAlias needed (Type variable "T" is invalid as target for type alias [misc])
mb_holder_t: TypeAlias = T | Iterable[T] | Sequence[T]  # Maybe holder_t, as_holder() possible type

fields_t = dict[str, T]                         # Fields holder type
on_set_t = tuple[mb_holder_t[str] | None, bool, Callable[[str, Any, Any], None]]


class ClsObj(NamedTuple):
    cls: type | None
    obj: object | None


class ItemError(NamedTuple):
    key: Any
    value: Any
    result: Any = ''


class ValidWrong(tuple):
    valid: Any
    wrong: Any
    errors: Iterable[ItemError]

    def __new__(cls, valid, wrong, errors: Iterable[ItemError] = ()):
        self = super().__new__(cls, (valid, wrong))
        self.valid = valid
        self.wrong = wrong
        self.errors = errors
        return self


@dataclass(slots=True)
class Field:
    """Field additional descriptor's holder
    Used if custom export/import functions needed at value declaration of inherited ConfigBase
    Also used internally in ConfigBase"""
    default: Any
    export_func: Callable = repr
    import_func: Callable = literal_eval
    type: type = object  # internal usage, filled at ConfigBase init
