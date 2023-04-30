"""Config layer exceptions"""
from typing import Callable, Any


_UNIQUE = object()


# Common exceptions


class InternalError(Exception):
    """Something in code goes wrong, program works not as expected!"""


class InputError(Exception):
    """Input parameter(s) of func or class method is wrong
    All parameters are optional, can be names or exceptions (if needed to override message)
    Parameters must_be and received can be started from ':' sign, to join message without space"""
    def __init__(self, *items: Exception | str,  msg='', item_name='parameter', func_name='',
                 args=(), force_header=False, **kwargs: Any):
        self.items = items
        self.msg = msg
        self.item_name = item_name
        self.func_name = func_name
        self.kwargs = kwargs
        self.header = self.must_be = self.received = ''
        self.sentences: tuple = ()

        # Handle exceptions
        if not all(isinstance(x, str) for x in items):
            super().__init__('; '.join(map(repr, items)), *args)
            return

        # Make header
        header = f'Provided wrong {item_name}'
        func = f' to {func_name}' if func_name else ''
        match len(items):
            case 0: header = f'{header}(s){func}' if (force_header or func or
                                                      not (msg or kwargs)) else ''
            case 1: header = f'{header}{func}: {items[0]}'
            # bug mypy: not see check for str at line 30, so type ignored
            case _: header = f'{header}s{func}: {", ".join(items)}'                                 # type: ignore[arg-type]
        self.header = header

        # Make received, must_be and sentences
        must_recv, sentences = [], []
        for k, v in kwargs.items():
            if k == 'sentences':
                sentences.extend(v)
                continue

            # bug mypy: isinstance can accept Callable as type, so type ignored
            if val := (v if isinstance(v, str) else
                       v() if isinstance(v, Callable) else f': {v!r}'):                             # type: ignore[arg-type]
                sentence = f'{k.replace("_", " ")}{"" if val[0] in ":,=" else " "}{val}'
                if k == 'must_be' or k == 'received':
                    setattr(self, k, v)
                    must_recv.append(sentence)
                else:
                    sentences.append(sentence)
        self.sentences = tuple(sentences)

        # Build message and fill exception
        msgs = (header, msg, ', but '.join(must_recv), *sentences)
        super().__init__('. '.join(x[0].upper() + x[1:] for x in msgs if x), *args)


class InitError(Exception):
    """Object initialization failed during class.__init__() method processing"""


class CheckValueError(ValueError):
    """Object value check failed"""


class CheckTypeError(TypeError):
    """Object type check failed"""


# Config related exceptions


class ConfigError(Exception):
    """Any config-related error type"""


class OptionsCheckError(ConfigError):
    """Options check failed, planned set of values is invalid"""


def _replace_unique(value, default=''):
    if value != _UNIQUE:
        try:
            value = repr(value)
        except Exception as e:
            value = repr(e)
    else:
        value = default
    return value


class FieldError(ConfigError):
    """Requested wrong field operation"""
    def __init__(self, operation: str, config: str, field: str, to_value=_UNIQUE,
                 from_value=_UNIQUE, by_func='', reason='', failed=True, type_name='config'):
        from_value = f' from {from_value!r}' if (from_value := _replace_unique(from_value)) else ''
        to_value = f' to {to_value!r}' if (to_value := _replace_unique(to_value)) else ''
        by_func = f' by {by_func}' if by_func else ''
        failed = f' {"failed" if failed else "completed"}'
        reason = f',{"" if failed else " but"} {reason}' if reason else ''
        super().__init__(f'{operation.capitalize()} {config!r} {type_name} field {field!r}'
                         f'{from_value}{to_value}{by_func}{failed}{reason}')


class ProfilesError(ConfigError):
    """Requested wrong profiles operation"""


class IOImportError(ConfigError):
    """Requested wrong io import operation"""


class IOExportError(ConfigError):
    """Requested wrong io export operation"""


class FileError(ConfigError):
    """Requested wrong file operation"""
