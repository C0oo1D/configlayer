"""List of constants"""
from configparser import DEFAULTSECT

from .utils import UID


__all__ = ('DEFAULT_ID', 'DEFAULT_SECTION')


DEFAULT_ID = UID('Default')     # Unique default value constant
DEFAULT_SECTION = DEFAULTSECT   # Default section name constant
