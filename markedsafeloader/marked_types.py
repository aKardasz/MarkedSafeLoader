# Wrapper for immutable types: we override __new__ and use __slots__.
import datetime
from types import NoneType
from typing import TypedDict
from yaml import Mark


class Markers(TypedDict):
    start: Mark
    end: Mark
 

class MarkedInt(int):
    def __new__(cls, value, __mark__=None):
        obj = super().__new__(cls, value)
        obj.__mark__ = __mark__
        return obj

class MarkedFloat(float):
    __slots__ = ('__mark__',)
    def __new__(cls, value, __mark__=None):
        obj = super().__new__(cls, value)
        obj.__mark__ = __mark__
        return obj

class BoolMeta(type):
    @classmethod
    def __subclasscheck__(cls, subclass):
            # Custom logic for subclass check
        return subclass is bool or subclass is MarkedBool

    def __instancecheck__(self, instance):
            return instance is bool

class MarkedBool(int, metaclass=BoolMeta):
    @property
    def __class__(self):
        # hack maybe???
        return bool

    @property
    def __mark__(self):
        return self._x

    @__mark__.setter
    def __mark__(self, value):
        self._x = value
    
    def __new__(cls, value):
        return super().__new__(cls, bool(value))
    def __and__(self, other):
        return MarkedBool(super().__and__(other))
    def __or__(self, other):
        return MarkedBool(super().__or__(other))
    def __xor__(self, other):
        return MarkedBool(super().__xor__(other))
    def __repr__(self):
        return "MarkedBool(True)" if self else "BoolMark(False)"

class NoneMeta(type):
    @classmethod
    def __subclasscheck__(cls, subclass):
        return subclass is NoneType or subclass is MarkedNone

    def __instancecheck__(self, instance):
            return instance is None

class MarkedNone(metaclass=NoneMeta):
    """behaves like None"""
    _hash = None.__hash__()
    
    def __init__(self, value):
        # added to throw away original none value
        pass

    @property
    def __mark__(self):
        return self._x

    @__mark__.setter
    def __mark__(self, value):
        self._x = value

    def __bool__(self):
        return False
    def __eq__(self, other):
        return other is None or isinstance(other, MarkedNone)
    def __hash__(self):
        return self._hash

class MarkedStr(str):
    __slots__ = ('__mark__',)
    def __new__(cls, value, __mark__=None):
        obj = super().__new__(cls, value)
        obj.__mark__ = __mark__
        return obj

class MarkedTuple(tuple):
    def __new__(cls, iterable, __mark__=None):
        # Create a tuple from an iterable.
        obj = super().__new__(cls, iterable)
        obj.__mark__ = __mark__
        return obj

class MarkedBytes(bytes):
    def __new__(cls, source, __mark__=None):
        obj = super().__new__(cls, source)
        obj.__mark__ = __mark__
        return obj


class MarkedList(list):
    def __init__(self, iterable=(), __mark__=None):
        super().__init__(iterable)
        self.__mark__ = __mark__

class MarkedDict(dict):
    def __init__(self, *args, __mark__=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.__mark__ = __mark__

class MarkedSet(set):
    def __init__(self, iterable=(), __mark__=None):
        super().__init__(iterable)
        self.__mark__ = __mark__

class MarkedByteArray(bytearray):
    def __init__(self, source, __mark__=None):
        super().__init__(source)
        self.__mark__ = __mark__

import datetime

class MarkedDateTime(datetime.datetime):
    def __new__(cls, year, month, day, hour=0, minute=0, second=0, microsecond=0,
                tzinfo=None, *, fold=0, __mark__=None):
        obj = super().__new__(cls, year, month, day, hour, minute, second,
                              microsecond, tzinfo, fold=fold)
        obj.__mark__ = __mark__
        return obj

class MarkedDate(datetime.date):
    def __new__(cls, year, month, day, __mark__=None):
        obj = super().__new__(cls, year, month, day)
        obj.__mark__ = __mark__
        return obj