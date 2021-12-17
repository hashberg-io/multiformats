"""
    Implementation of the [multibase spec](https://github.com/multiformats/multibase).

    The `Multibase` class provides a container for multibase encoding data:

    ```py
    >>> from multiformats import multibase
    >>> from multiformats.multibase import Multibase
    >>> Multibase(name="base16", code="f",
                  status="default", description="hexadecimal")
        Multibase(name='base16', code='f', status='default', description='hexadecimal')
    ```

    Core functionality is provided by the `encode` and `decode` functions, which can be used to
    encode a bytestring into a string using a chosen multibase encoding and to decode a string
    into a bytestring using the multibase encoding specified by its first character:

    ```py
    >>> multibase.encode(b"Hello World!", "base32")
    'bjbswy3dpeblw64tmmqqq'
    >>> multibase.decode('bjbswy3dpeblw64tmmqqq')
    b'Hello World!'
    ```

    The multibase encoding specified by a given string is accessible using the `from_str` function:
    ```py
    >>> multibase.from_str('bjbswy3dpeblw64tmmqqq')
    Multibase(encoding='base32', code='b',
              status='default',
              description='rfc4648 case-insensitive - no padding')
    ```

    Additional encoding management functionality is provided by the `exists` and `get` functions,
    which can be used to check whether an encoding with given name or code is known, and if so to get the corresponding object:

    ```py
    >>> multibase.exists("base32")
    True
    >>> multibase.get("base32")
    Multibase(encoding='base32', code='b',
              status='default',
              description='rfc4648 case-insensitive - no padding')
    >>> multibase.exists(code="f")
    True
    >>> multibase.get(code="f")
    Multibase(encoding="base16", code="f",
              status="default", description="hexadecimal")
    ```

    Multibase objects have `encode` and `decode` methods that perform functionality analogous to the homonymous functions:

    ```py
    >>> base32 = multibase.get("base32")
    >>> base32.encode(b"Hello World!")
    'bjbswy3dpeblw64tmmqqq'
    >>> base32.decode('bjbswy3dpeblw64tmmqqq')
    b'Hello World!'
    ```

    The `decode` method includes additional encoding validation:

    ```py
    >>> base32.decode('Bjbswy3dpeblw64tmmqqq')
    ValueError: Expected 'base32' encoding, found 'base32upper' encoding instead.
    ```

    The `table` function can be used to iterate through known multibase encodings:

    ```py
    >>> list(enc.name for enc in multibase.table())
    ['identity', 'base2', 'base8', 'base10', 'base32upper',
     'base32padupper', 'base16upper', 'base36upper', 'base64pad',
     'base32hexpadupper', 'base64urlpad', 'base32hexupper',
     'base58flickr', 'base32', 'base32pad', 'base16', 'base32z',
     'base36', 'base64', 'proquint', 'base32hexpad', 'base64url',
     'base32hex', 'base58btc']
    ```
"""

from abc import ABC, abstractmethod
import binascii
import importlib.resources as importlib_resources
from itertools import product
import json
import math
import re
from typing import Any, Callable, cast, Dict, Iterable, Iterator, List, Mapping, Optional, Tuple, Type, Union
import sys

from typing_extensions import Literal
from typing_validation import validate

from bases import (base2, base16, base8, base10, base36, base58btc, base58flickr, base58ripple,
                   base32, base32hex, base32z, base64, base64url, base45,)

from multiformats.multibase import raw
from multiformats.varint import BytesLike
from .raw import RawEncoder, RawDecoder


class Multibase:
    """
        Container class for a multibase encoding.

        Example usage:

        ```py
            Multibase(name="base16", code="f",
                      status="default", description="hexadecimal")
        ```
    """

    _name: str
    _code: str
    _status: Literal["draft", "candidate", "default"]
    _description: str

    __slots__ = ("__weakref__", "_name", "_code", "_status", "_description")

    def __init__(self, *,
                 name: str,
                 code: str,
                 status: str = "draft",
                 description: str = ""
                ):
        for arg in (name, code, status, description):
            validate(arg, str)
        name = Multibase._validate_name(name)
        code = Multibase.validate_code(code)
        status = Multibase._validate_status(status)
        self._name = name
        self._code = code
        self._status = status
        self._description = description

    @staticmethod
    def _validate_name(name: Optional[str]) -> str:
        validate(name, Optional[str])
        assert name is not None
        if not re.match(r"^[a-z][a-z0-9_-]+$", name): # ensures len(name) > 1
            raise ValueError(f"Invalid multibase encoding name {repr(name)}")
        return name

    @staticmethod
    def validate_code(code: str) -> str:
        """
            Validates a multibase code and transforms it to single-character format (if in hex format).

            Example usage:

            ```py
            >>> Multibase.validate_code("0x00")
            '\\x00'
            >>> Multibase.validate_code("hi")
            ValueError: Multibase codes must be single-character strings
            or the hex digits '0xYZ' of a single byte.
            ```
        """
        validate(code, str)
        if re.match(r"^0x[0-9a-zA-Z][0-9a-zA-Z]$", code):
            ord_code = int(code, base=16)
            code = chr(ord_code)
        elif len(code) != 1:
            raise ValueError("Multibase codes must be single-character strings or the hex digits '0xYZ' of a single byte.")
        if ord(code) not in range(0x00, 0x80):
            raise ValueError("Multibase codes must be ASCII characters.")
        return code

    @staticmethod
    def _validate_status(status: str) -> Literal["draft", "candidate", "default"]:
        if status not in ("draft", "candidate", "default"):
            raise ValueError(f"Invalid multibase encoding status {repr(status)}.")
        return cast(Literal["draft", "candidate", "default"], status)

    @property
    def code(self) -> str:
        """
            Multibase code. Must either have length 1 or satisfy:

            ```py
            re.match(r"^0x$", code)
            ```
        """
        return self._code

    @property
    def code_printable(self) -> str:
        """
            Printable version of `Multibase.code`:

            - if the code is a single non-printable ASCII character, returns the hex string of its byte
            - otherwise, returns the code itself

            Example usage:

            ```py
            >>> identity = multibase.get(code="\\x00")
            >>> identity.code
            '\\x00'
            >>> identity.code_printable
            '0x00'
            ```
        """
        code = self.code
        ord_code = ord(code)
        if ord_code not in range(0x20, 0x7F):
            return "0x"+base16.encode(bytes([ord_code]))
        return code

    @property
    def status(self) -> Literal["draft", "candidate", "default"]:
        """ Multibase status. Must be 'draft', 'candidate' or 'default'."""
        return self._status

    @property
    def description(self) -> str:
        """ Multibase description. """
        return self._description

    @property
    def name(self) -> str:
        """
            Multibase name. Must satisfy the following:

            ```py
            re.match(r"^[a-z][a-z0-9_-]+$", name)
            ```

            In the [multibase table](https://github.com/multiformats/multibase/raw/master/multibase.csv),
            this is listed under `encoding`.
        """
        return self._name

    @property
    def raw_encoder(self) -> RawEncoder:
        """
            Returns the raw encoder for this encoding:
            given bytes, it produces the encoded string without the multibase prefix.
        """
        enc = raw.get(self.name)
        if enc is None:
            raise NotImplementedError(f"Multibase/decoding for {repr(self.name)} is not yet implemented.")
        return enc.encode

    @property
    def raw_decoder(self) -> RawDecoder:
        """
            Returns the raw encoder for this encoding:
            given a string without the multibase prefix, it produces the decoded data.
        """
        enc = raw.get(self.name)
        if enc is None:
            raise NotImplementedError(f"Multibase/decoding for {repr(self.name)} is not yet implemented.")
        return enc.decode

    def encode(self, data: BytesLike) -> str:
        """
            Encodes bytes into a multibase string: it first uses `Multibase.raw_encoder`,
            and then prepends the multibase prefix given by `Multibase.code` and returns
            the resulting multibase string.

            Example usage:

            ```py
            >>> base32 = multibase.get("base32")
            >>> base32.encode(b"Hello World!")
            'bjbswy3dpeblw64tmmqqq'
            ```
        """
        return self.code+self.raw_encoder(data)

    def decode(self, string: str) -> bytes:
        """
            Decodes a multibase string into bytes: it first checks that the multibase
            prefix matches the value specified by `Multibase.code`, then uses
            `Multibase.raw_encoder` on the string without prefix and returns the bytes.

            Example usage:

            ```py
            >>> base32 = multibase.get("base32")
            >>> base32.decode("bjbswy3dpeblw64tmmqqq")
            b'Hello World!'
            ```
        """
        encoding = from_str(string)
        if encoding != self:
            raise ValueError(f"Expected {repr(self.name)} encoding, "
                             f"found {repr(encoding.name)} encoding instead.")
        return self.raw_decoder(string[1:])

    def to_json(self) -> Mapping[str, str]:
        """
            Returns a JSON dictionary representation of this `Multibase` object.

            Example usage:

            ```py
            >>> base32 = multibase.get("base32")
            >>> base32.to_json()
            {'name': 'base32', 'code': 'b',
             'status': 'default',
             'description': 'rfc4648 case-insensitive - no padding'}
            ```
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
    def _as_tuple(self) -> Tuple[Type["Multibase"], str, str, Literal["draft", "candidate", "default"]]:
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
        Gets the multibase encoding with given name or multibase code. Exactly one
        of `name` or `code` must be passed:

        - `name` can be passed as either a positional or keyword argument
        - `code` must be passed as a keyword argument

        Raises `ValueError` if the empty string is passed. Raises `KeyError` if no such encoding exists.

        Example usage:

        ```py
        >>> multibase.get("base8")
        Multibase(encoding='base8', code='7',
                  status='draft', description='octal')
        >>> multibase.get(name="base8")
        Multibase(encoding='base8', code='7',
                  status='draft', description='octal')
        >>> multibase.get(code="t")
        Multibase(encoding='base32hexpad', code='t', status='candidate',
                  description='rfc4648 case-insensitive - with padding')
        ```
    """
    validate(name, Optional[str])
    validate(code, Optional[str])
    if (name is None) == (code is None):
        raise ValueError("Must specify exactly one between encoding name and code.")
    if code is not None:
        if code not in _code_table:
            raise KeyError(f"No multibase encoding with code {repr(code)}.")
        return _code_table[code]
    if name not in _name_table:
        raise KeyError(f"No multibase encoding named {repr(name)}.")
    return _name_table[name]


def exists(name: Optional[str] = None, *, code: Optional[str] = None) -> bool:
    """
        Checks whether a multibase encoding with given name or code exists. Exactly one
        of `name` or `code` must be passed:

        - `name` can be passed as either a positional or keyword argument
        - `code` must be passed as a keyword argument

        Raises `ValueError` if the empty string is passed.

        Example usage:

        ```py
        >>> multibase.exists("base8")
        True
        >>> multibase.exists(code="t")
        True
        ```
    """
    validate(name, Optional[str])
    validate(code, Optional[str])
    if (name is None) == (code is None):
        raise ValueError("Must specify exactly one between encoding name and code.")
    if code is not None:
        code = Multibase.validate_code(code)
        return code in _code_table
    return name in _name_table


def register(enc: Multibase, *, overwrite: bool = False) -> None:
    """
        Registers a given multibase encoding. The optional keyword argument `overwrite` (default: `False`)
        can be used to overwrite a multibase encoding with existing code.

        When `overwrite` is `False`, raises `ValueError` if a multibase encoding with the same name or code already exists.
        When `overwrite` is `True`, raises `ValueError` if a multibase encoding with the same name but different code already exists.

        Example usage:

        ```py
        >>> base45 = Multibase(name="base45", code=":",
                               status="draft", description="base45 encoding")
        >>> multibase.register(base45)
        >>> multibase.get("base45")
        Multibase(encoding='base45', code=':', status='draft',
                  description='base45 encoding')
        ```
    """
    validate(enc, Multibase)
    validate(overwrite, bool)
    if not overwrite and enc.code in _code_table:
        raise ValueError(f"Multibase encoding with code {repr(enc.code)} already exists: {_code_table[enc.code]}")
    if enc.name in _name_table and _name_table[enc.name].code != enc.code:
        raise ValueError(f"Multibase encoding with name {repr(enc.name)} already exists: {_name_table[enc.name]}")
    _code_table[enc.code] = enc
    _name_table[enc.name] = enc


def validate_multibase(multibase: Multibase) -> None:
    """
        Validates a multibase:

        - raises `KeyError` if no multibase with the given name is registered
        - raises `ValueError` if a multibase with the given name is registered, but is different from the one given
        - raises no error if the given multibase is registered
    """
    validate(multibase, Multibase)
    mc = get(multibase.name)
    if mc != multibase:
        raise ValueError(f"Multibase named {multibase.name} exists, but is not the one given.")


def unregister(name: Optional[str] = None, *, code: Optional[str] = None) -> None:
    """
        Unregisters the multibase encoding with given name (if a string is passed) or code (if an int is passed).
        Raises `KeyError` if no such multibase encoding exists.

        Example usage:

        ```py
        >>> base45 = Multibase(name="base45", code=":",
                               status="draft", description="base45 encoding")
        >>> multibase.register(base45)
        >>> multibase.get("base45")
        Multibase(encoding='base45', code=':', status='draft',
                  description='base45 encoding')
        >>> multibase.unregister(code=":")
        >>> multibase.exists("base45")
        False
        ```
    """
    enc = get(name=name, code=code)
    del _code_table[enc.code]
    del _name_table[enc.name]


def table() -> Iterator[Multibase]:
    """
        Iterates through the registered encodings, in order of ascending code.

        Example usage:

        ```py
        >>> [e.code for e in multibase.table()]
        ['\\x00', '0', '7', '9', 'B', 'C', 'F', 'K', 'M', 'T', 'U', 'V',
         'Z','b', 'c', 'f', 'h', 'k', 'm', 'p', 't', 'u', 'v', 'z']
        ```
    """
    for code in sorted(_code_table.keys()):
        yield _code_table[code]


def from_str(string: str) -> Multibase:
    """
        Returns the multibase encoding for the given string, according to the code specified by its prefix.
        Raises `ValueError` if the empty string is passed.
        Raises `KeyError` if no encoding exists with that code.

        Example usage:

        ```py
        >>> multibase.from_str("mSGVsbG8gd29ybGQh")
        Multibase(encoding='base64', code='m', status='default',
                  description='rfc4648 no padding')
        ```
    """
    validate(string, str)
    if len(string) == 0:
        raise ValueError("Empty string is not valid for encoded data.")
    if string[0] in _code_table:
        return _code_table[string[0]]
    for code in _code_table:
        if string.startswith(code):
            return get(code=code)
    raise KeyError("No known multibase code is a prefix of the given string.")


def encode(data: BytesLike, enc: Union[str, "Multibase"]) -> str:
    """
        Encodes the given bytes into a multibase string using the given encoding.
        If the encoding is passed by name or code (i.e. as a string), the `get`
        function is used to retrieve it. Multibase encoding is performed by `Multibase.encode`.

        Example usage:

        ```py
        >>> multibase.encode(b"Hello world!", "base64")
        'mSGVsbG8gd29ybGQh'
        ```
    """
    validate(enc, Union[str, "Multibase"])
    if isinstance(enc, str):
        enc = get(enc)
    return enc.encode(data)


def decode(string: str) -> bytes:
    """
        Decodes the given multibase string into bytes.
        The encoding is inferred using the `from_str` function.
        Decoding is then performed by `Multibase.decode`.

        Example usage:

        ```py
        >>> multibase.decode("mSGVsbG8gd29ybGQh")
        b'Hello world!'
        ```
    """
    enc = from_str(string)
    return enc.decode(string)


def decode_raw(string: str) -> Tuple[Multibase, bytes]:
    """
        Similar to `decode`, but returns a `(base, bytestr)` pair
        of the multibase and decoded bytestring.

        Example usage:

        ```py
        >>> base, bytestr = multibase.decode_raw("mSGVsbG8gd29ybGQh")
        >>> base
        Multibase(name='base64', code='m',
                  status='default', description='rfc4648 no padding')
        >>> bytestr
        b'Hello world!'
        ```
    """
    enc = from_str(string)
    return enc, enc.decode(string)


def build_multibase_tables(encodings: Iterable[Multibase]) -> Tuple[Dict[str, Multibase], Dict[str, Multibase]]:
    """
        Creates code->encoding and name->encoding mappings from a finite iterable of encodings, returning the mappings.

        Raises `ValueError` if the same encoding code or name is encountered multiple times

        Example usage:

        ```py
            code_table, name_table = build_multicodec_tables(encodings)
        ```
    """
    # validate(multicodecs, Iterable[Multicodec]) # TODO: not yet properly supported by typing-validation
    code_table: Dict[str, Multibase] = {}
    name_table: Dict[str, Multibase] = {}
    for e in encodings:
        if e.code in code_table:
            raise ValueError(f"Multicodec name {e.name} appears multiple times in table.")
        code_table[e.code] = e
        if e.name in name_table:
            raise ValueError(f"Multicodec name {e.name} appears multiple times in table.")
        name_table[e.name] = e
    return code_table, name_table

# Create the global code->multibase and name->multibase mappings.
_code_table: Dict[str, Multibase]
_name_table: Dict[str, Multibase]
with importlib_resources.open_text("multiformats.multibase", "multibase-table.json") as table_f:
    table_json = json.load(table_f)
    _code_table, _name_table = build_multibase_tables(Multibase(**row) for row in table_json)

# additional docs info
__pdoc__ = {
    "build_multibase_tables": False # exclude from docs
}
