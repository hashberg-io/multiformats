"""
    Implementation of the `multibase spec <https://github.com/multiformats/multibase>`_.

    Suggested usage:

    >>> from multiformats import multibase
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import binascii
import importlib.resources as importlib_resources
from itertools import product
import json
import math
import re
from typing import Any, Callable, cast, Dict, Iterable, Iterator, List, Mapping, Optional, Tuple, Type, Union
import sys

from typing_extensions import Literal, Final
from typing_validation import validate

from bases import (base2, base16, base8, base10, base36, base58btc, base58flickr, base58ripple,
                   base32, base32hex, base32z, base64, base64url, base45,)
from multiformats_config.multibase import load_multibase_table

from multiformats.multibase import raw
from multiformats.varint import BytesLike
from .raw import RawEncoder, RawDecoder
from .err import MultibaseKeyError, MultibaseValueError

MultibaseStatus = Literal[
    "draft", "final", "reserved", "experimental",
    "candidate", "default" # FIXME: deprecated legacy values
]
"""
    Literal type of possible values for the :attr:`Multibase.status` property.
"""

MultibaseStatusValues: Final[Tuple[MultibaseStatus, ...]] = (
    "draft", "final", "reserved", "experimental", "candidate", "default"
)
"""
    Collection of possible values for the :attr:`Multibase.status` property.
"""

class Multibase:
    """
        Container class for a multibase encoding.

        Example usage:

        >>> Multibase(name="base16", code="f",
                      status="default", description="hexadecimal")

        :param name: the multibase name
        :type name: :obj:`str`
        :param code: the multibase code, as single-char string or ``0x...`` hex-string of a non-empty bytestring
        :type code: :obj:`str`
        :param status: the multibase status
        :type status: ``'draft'``, ``'candidate'`` or ``'default'``, *optional*
        :param description: the multibase description
        :type description: :obj:`str`, *optional*
    """

    _name: str
    _code: str
    _status: MultibaseStatus
    _description: str

    __slots__ = ("__weakref__", "_name", "_code", "_status", "_description")

    def __new__(cls,
                name: str,
                code: str,
                status: str = "draft",
                description: str = ""
                ) -> "Multibase":
        for arg in (name, code, status, description):
            validate(arg, str)
        name = Multibase._validate_name(name)
        code = Multibase.validate_code(code)
        status = Multibase._validate_status(status)
        instance = super().__new__(cls)
        instance._name = name
        instance._code = code
        instance._status = status
        instance._description = description
        return instance

    def __getnewargs__(self) -> tuple[str, str, MultibaseStatus, str]:
        return (self.name, self.code, self.status, self.description)

    @staticmethod
    def _validate_name(name: Optional[str]) -> str:
        validate(name, Optional[str])
        assert name is not None
        if not re.match(r"^[a-z][a-z0-9_-]+$", name): # ensures len(name) > 1
            raise MultibaseValueError(f"Invalid multibase encoding name {repr(name)}")
        return name

    @staticmethod
    def validate_code(code: str) -> str:
        r"""
            Validates a multibase code and transforms it to single-character format (if in hex format).

            Example usage:

            >>> Multibase.validate_code("0x00")
            '\x00'
            >>> Multibase.validate_code("hi")
            MultibaseValueError: Multibase codes must be single-character strings
            or the hex digits '0xYZ' of a single byte.

            :param code: the multibase code, as single character or ``0x...`` hex-string of a non-empty bytestring
            :type code: :obj:`str`

            :raises ValueError: if the code is invalid

        """
        validate(code, str)
        if re.match(r"^0x([0-9a-zA-Z][0-9a-zA-Z])+$", code):
            ord_code = int(code, base=16)
            if ord_code in range(0x20, 0x7F):
                raise MultibaseValueError("Multibase codes in hex format cannot be printable ASCII characters.")
            code = chr(ord_code)
        elif len(code) != 1:
            raise MultibaseValueError("Multibase codes must be single-character strings or the hex digits '0x...' of a non-empty bytestring.")
        return code

    @staticmethod
    def _validate_status(status: str) -> MultibaseStatus:
        # if status not in ("draft", "candidate", "default"):
        if status not in MultibaseStatusValues:
            raise MultibaseValueError(f"Invalid multibase encoding status {repr(status)}.")
        return cast(MultibaseStatus, status)

    @property
    def code(self) -> str:
        """
            Multibase code. Must either have length 1 or satisfy:

            .. code-block:: python

               re.match(r"^0x$", code)

        """
        return self._code

    @property
    def code_printable(self) -> str:
        r"""
            Printable version of :meth:`Multibase.code`:

            - if the code is a single non-printable ASCII character, returns the hex string of its byte
            - otherwise, returns the code itself

            Example usage:

            >>> identity = multibase.get(code="\x00")
            >>> identity.code
            '\x00'
            >>> identity.code_printable
            '0x00'

        """
        code = self.code
        ord_code = ord(code)
        if ord_code not in range(0x20, 0x7F):
            ord_code_num_bytes = max(1, math.ceil(ord_code.bit_length()/8))
            ord_code_bytes = ord_code.to_bytes(ord_code_num_bytes, byteorder="big")
            return "0x"+base16.encode(ord_code_bytes)
        return code

    @property
    def status(self) -> MultibaseStatus:
        """
            Multibase status.
        """
        return self._status

    @property
    def description(self) -> str:
        """ Multibase description. """
        return self._description

    @property
    def name(self) -> str:
        """
            Multibase name. Must satisfy the following:

            .. code-block:: python

                re.match(r"^[a-z][a-z0-9_-]+$", name)

            In the `multibase table <https://github.com/multiformats/multibase/raw/master/multibase.csv>`_,
            this is listed under `encoding`.
        """
        return self._name

    @property
    def raw_encoder(self) -> RawEncoder:
        """
            Returns the raw encoder for this encoding: given bytes, it produces the encoded string without the multibase prefix.
        """
        enc = raw.get(self.name)
        if enc is None:
            raise NotImplementedError(f"Multibase/decoding for {repr(self.name)} is not yet implemented.")
        return enc.encode

    @property
    def raw_decoder(self) -> RawDecoder:
        """
            Returns the raw encoder for this encoding: given a string without the multibase prefix, it produces the decoded data.
        """
        enc = raw.get(self.name)
        if enc is None:
            raise NotImplementedError(f"Multibase/decoding for {repr(self.name)} is not yet implemented.")
        return enc.decode

    def encode(self, b: BytesLike) -> str:
        """
            Encodes bytes into a multibase string: it first uses :meth:`Multibase.raw_encoder`,
            and then prepends the multibase prefix given by :attr:`Multibase.code` and returns the resulting multibase string.

            Example usage:

            >>> base32 = multibase.get("base32")
            >>> base32.encode(b"Hello World!")
            'bjbswy3dpeblw64tmmqqq'

            :param b: the bytes to be encoded
            :type s: :class:`~multiformats.varint.BytesLike`

        """
        return self.code+self.raw_encoder(b)

    def decode(self, s: str) -> bytes:
        """
            Decodes a multibase string into bytes: it first checks that the multibase
            prefix matches the value specified by :attr:`Multibase.code`, then uses
            :meth:`Multibase.raw_decoder` on the string without prefix and returns the bytes.

            Example usage:

            >>> base32 = multibase.get("base32")
            >>> base32.decode("bjbswy3dpeblw64tmmqqq")
            b'Hello World!'

            :param s: the string to be decoded
            :type s: :obj:`str`

            :raises ValueError: if the code from the string is different from the one of this multibase
            :raises ValueError: see :func:`from_str`
            :raises KeyError: see :func:`from_str`
        """
        encoding = from_str(s)
        if encoding != self:
            raise MultibaseValueError(f"Expected {repr(self.name)} encoding, "
                                 f"found {repr(encoding.name)} encoding instead.")
        return self.raw_decoder(s[1:])

    def to_json(self) -> Mapping[str, str]:
        """
            Returns a JSON dictionary representation of this :class:`Multibase` object.

            Example usage:

            >>> base32 = multibase.get("base32")
            >>> base32.to_json()
            {'name': 'base32', 'code': 'b',
             'status': 'default',
             'description': 'rfc4648 case-insensitive - no padding'}

        """
        return {
            "name": self.name,
            "code": self.code_printable,
            "status": self.status,
            "description": self.description
        }

    def __str__(self) -> str:
        if exists(self.name) and get(self.name) == self:
            return f"multibase.get({repr(self.name)})"
        return repr(self)

    def __repr__(self) -> str:
        return f"Multibase({', '.join(f'{k}={repr(v)}' for k, v in self.to_json().items())})"

    @property
    def _as_tuple(self) -> Tuple[Type["Multibase"], str, str, MultibaseStatus]:
        return (Multibase, self.name, self.code, self.status)

    def __hash__(self) -> int:
        return hash(self._as_tuple)

    def __eq__(self, other: Any) -> bool:
        if self is other:
            return True
        if not isinstance(other, Multibase):
            return NotImplemented
        return self._as_tuple == other._as_tuple


def get(name: Optional[str] = None, *, code: Optional[str] = None) -> Multibase:
    """
        Gets the multibase encoding with given name or multibase code.

        Example usage:

        >>> multibase.get("base8")
        Multibase(encoding='base8', code='7',
                  status='draft', description='octal')
        >>> multibase.get(name="base8")
        Multibase(encoding='base8', code='7',
                  status='draft', description='octal')
        >>> multibase.get(code="t")
        Multibase(encoding='base32hexpad', code='t', status='candidate',
                  description='rfc4648 case-insensitive - with padding')

        :param name: the name of this multibase
        :type name: :obj:`str` or :obj:`None`, *optional*
        :param code: the code of this multibase (keyword-only)
        :type name: :obj:`str` or :obj:`None`, *optional*

        :raises ValueError: if the empty string is passed
        :raises KeyError: if no such multibase exists
        :raises ValueError: unless exactly one of ``name`` and ``code`` is specified

    """
    validate(name, Optional[str])
    validate(code, Optional[str])
    if (name is None) == (code is None):
        raise MultibaseValueError("Must specify exactly one between encoding name and code.")
    if code is not None:
        if code not in _code_table:
            raise MultibaseKeyError(f"No multibase encoding with code {repr(code)}.")
        return _code_table[code]
    if name not in _name_table:
        raise MultibaseKeyError(f"No multibase encoding named {repr(name)}.")
    return _name_table[name]


def exists(name: Optional[str] = None, *, code: Optional[str] = None) -> bool:
    """
        Checks whether a multibase encoding with given name or code exists.

        Example usage:

        >>> multibase.exists("base8")
        True
        >>> multibase.exists(code="t")
        True

        :param name: the name of this multibase
        :type name: :obj:`str` or :obj:`None`, *optional*
        :param code: the code of this multibase (keyword-only)
        :type name: :obj:`str` or :obj:`None`, *optional*

        :raises ValueError: if the empty string is passed
        :raises ValueError: unless exactly one of ``name`` and ``code`` is specified
    """
    validate(name, Optional[str])
    validate(code, Optional[str])
    if (name is None) == (code is None):
        raise MultibaseValueError("Must specify exactly one between encoding name and code.")
    if code is not None:
        code = Multibase.validate_code(code)
        return code in _code_table
    return name in _name_table


def register(base: Multibase, *, overwrite: bool = False) -> None:
    """
        Registers a given multibase encoding.

        Example usage:

        >>> base45 = Multibase(name="base45", code=":",
                               status="draft", description="base45 encoding")
        >>> multibase.register(base45)
        >>> multibase.get("base45")
        Multibase(encoding='base45', code=':', status='draft',
                  description='base45 encoding')

        :param base: the multibase to register
        :type base: :class:`Multibase`
        :param overwrite: whether to overwrite a multibase with existing code (optional, default :obj:`False`)
        :type overwrite: :obj:`bool`, *optional*

        :raises ValueError: if ``overwrite`` is :obj:`False` and a multibase with the same name or code already exists
        :raises ValueError: if ``overwrite`` is :obj:`True` and a multibase with the same name but different code already exists

    """
    validate(base, Multibase)
    validate(overwrite, bool)
    if not overwrite and base.code in _code_table:
        raise MultibaseValueError(f"Multibase encoding with code {repr(base.code)} already exists: {_code_table[base.code]}")
    if base.name in _name_table and _name_table[base.name].code != base.code:
        raise MultibaseValueError(f"Multibase encoding with name {repr(base.name)} already exists: {_name_table[base.name]}")
    _code_table[base.code] = base
    _name_table[base.name] = base


def validate_multibase(multibase: Multibase) -> None:
    """
        Validates an instance of :class:`Multibase`.
        If the multibase is registered (i.e. valid), no error is raised.

        :param multibase: the instance to be validated
        :type multibase: :class:`Multibase`

        :raises KeyError: if no multibase with the given name is registered
        :raises ValueError: if a multibase with the given name is registered, but is different from the one given
    """
    validate(multibase, Multibase)
    mc = get(multibase.name)
    if mc != multibase:
        raise MultibaseValueError(f"Multibase named {multibase.name} exists, but is not the one given.")


def unregister(name: Optional[str] = None, *, code: Optional[str] = None) -> None:
    """
        Unregisters the multibase encoding with given name or code.

        Example usage:

        >>> base45 = Multibase(name="base45", code=":",
                               status="draft", description="base45 encoding")
        >>> multibase.register(base45)
        >>> multibase.get("base45")
        Multibase(encoding='base45', code=':', status='draft',
                  description='base45 encoding')
        >>> multibase.unregister(code=":")
        >>> multibase.exists("base45")
        False

        :param name: the multibase name
        :type name: :obj:`str` or :obj:`None`, *optional*
        :param code: the multibase code
        :type code: :obj:`str` or :obj:`None`, *optional*

        :raises KeyError: if no such multibase exists
    """
    enc = get(name=name, code=code)
    del _code_table[enc.code]
    del _name_table[enc.name]


def table() -> Iterator[Multibase]:
    """
        Iterates through the registered multibases, in order of ascending code.

        Example usage:

        >>> [e.code for e in multibase.table()]
        ['\\x00', '0', '7', '9', 'B', 'C', 'F', 'K', 'M', 'T', 'U', 'V',
         'Z','b', 'c', 'f', 'h', 'k', 'm', 'p', 't', 'u', 'v', 'z']

    """
    for code in sorted(_code_table.keys()):
        yield _code_table[code]


def from_str(s: str) -> Multibase:
    """
        Returns the multibase encoding for the given string, according to the code specified by its prefix.

        Example usage:

        >>> multibase.from_str("mSGVsbG8gd29ybGQh")
        Multibase(encoding='base64', code='m', status='default',
                  description='rfc4648 no padding')

        :param s: the multibase encoded string
        :type s: :obj:`str`

        :raises ValueError: if the empty string is passed
        :raises KeyError: if no multibase exists with that code
    """
    validate(s, str)
    if len(s) == 0:
        raise MultibaseValueError("Empty string is not valid for encoded data.")
    if s[0] in _code_table:
        return _code_table[s[0]]
    for code in _code_table:
        if s.startswith(code):
            return get(code=code)
    raise MultibaseKeyError("No known multibase code is a prefix of the given string.")


def encode(data: BytesLike, base: Union[str, "Multibase"]) -> str:
    """
        Encodes the given bytes into a multibase string using the given encoding.

        If the encoding is passed by name, the :func:`get` function is used to retrieve it.
        Multibase encoding is performed by the :meth:`multiformats.multibase.Multibase.encode` method.

        Example usage:

        >>> multibase.encode(b"Hello world!", "base64")
        'mSGVsbG8gd29ybGQh'

        :param data: the data to encode using the multibase
        :type data: :obj:`~multiformats.varint.BytesLike`
        :param base: the multibase to use
        :type base: :obj:`str` or :class:`Multibase`
    """
    validate(base, Union[str, "Multibase"])
    if isinstance(base, str):
        base = get(base)
    return base.encode(data)


def decode(s: str) -> bytes:
    """
        Decodes the given multibase string into bytes.
        The encoding is inferred using the :func:`from_str` function.
        Decoding is then performed by :meth:`Multibase.decode` method.

        Example usage:

        >>> multibase.decode("mSGVsbG8gd29ybGQh")
        b'Hello world!'

        :param s: the string to be decoded
        :type s: :obj:`str`
    """
    base = from_str(s)
    return base.decode(s)


def decode_raw(s: str) -> Tuple[Multibase, bytes]:
    """
        Similar to :func:`decode`, but returns a ``(base, bytestr)`` pair
        of the multibase and decoded bytestring.

        Example usage:

        >>> base, bytestr = multibase.decode_raw("mSGVsbG8gd29ybGQh")
        >>> base
        Multibase(name='base64', code='m',
                  status='default', description='rfc4648 no padding')
        >>> bytestr
        b'Hello world!'

        :param s: the string to be decoded
        :type s: :obj:`str`

    """
    base = from_str(s)
    return base, base.decode(s)

_code_table, _name_table = load_multibase_table()

# def build_multibase_tables(bases: Iterable[Multibase]) -> Tuple[Dict[str, Multibase], Dict[str, Multibase]]:
#     """
#         Creates code->encoding and name->encoding mappings from a finite iterable of encodings, returning the mappings.

#         Example usage:

#         >>> code_table, name_table = build_multicodec_tables(bases)

#         :param bases: the multibases to add to the table
#         ::

#         :raises ValueError: if the same encoding code or name is encountered multiple times
#     """
#     # validate(multicodecs, Iterable[Multicodec]) # TODO: not yet properly supported by typing-validation
#     code_table: Dict[str, Multibase] = {}
#     name_table: Dict[str, Multibase] = {}
#     for e in bases:
#         if e.code in code_table:
#             raise MultibaseValueError(f"Multicodec name {e.name} appears multiple times in table.")
#         code_table[e.code] = e
#         if e.name in name_table:
#             raise MultibaseValueError(f"Multicodec name {e.name} appears multiple times in table.")
#         name_table[e.name] = e
#     return code_table, name_table

# Create the global code->multibase and name->multibase mappings.
# _code_table: Dict[str, Multibase] = {}
# _name_table: Dict[str, Multibase] = {}
# with importlib_resources.open_text("multiformats.multibase", "multibase-table.json", encoding="utf8") as _table_f:
#     _table_json = json.load(_table_f)
#     _code_table, _name_table = build_multibase_tables(Multibase(**row) for row in _table_json)
