"""
    Implementation of the [multibase spec](https://github.com/multiformats/multibase).

    The `Encoding` dataclass provides a container for multibase encoding data:

    ```py
    >>> from multiformats import multibase
    >>> from multiformats.multibase import Encoding
    >>> Encoding(encoding="base16", code="f",
                 status="default", description="hexadecimal")
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

    The multibase encoding specified by a given string is accessible using the `encoding_of` function:
    ```py
    >>> multibase.encoding_of('bjbswy3dpeblw64tmmqqq')
    Encoding(encoding='base32', code='b',
             status='default',
             description='rfc4648 case-insensitive - no padding')
    ```

    Additional encoding management functionality is provided by the `exists` and `encoding` functions,
    which can be used to check whether an encoding with given name or code is known, and if so to get the corresponding object:

    ```py
    >>> multibase.exists("base32")
    True
    >>> multibase.exists("f")
    True
    >>> multibase.encoding("base32")
    Encoding(encoding='base32', code='b',
             status='default',
             description='rfc4648 case-insensitive - no padding')
    >>> multibase.encoding("f")
    Encoding(encoding="base16", code="f",
             status="default", description="hexadecimal")
    ```

    Encoding objects have `encode` and `decode` methods that perform functionality analogous to the homonymous functions:

    ```py
    >>> base32 = multibase.encoding("base32")
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

    The `table` function can be used to iterate through known multibase encodings

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
import csv
from itertools import product
import math
import re
from typing import Any, Callable, cast, Dict, Iterable, Iterator, List, Mapping, Optional, Tuple, Union
import sys

from typing_extensions import Literal

from bases import (base2, base16, base8, base10, base36, base58btc, base58flickr, base58ripple,
                   base32, base32hex, base32z, base64, base64url, base45,)
from bases.encoding import BaseEncoding

from multiformats.multibase import raw_encoding as raw_encoding
from .raw_encoding import RawEncoder, RawDecoder

if sys.version_info[1] >= 7:
    import importlib.resources as importlib_resources
else:
    import importlib_resources


class Encoding:
    """
        Container class for a multibase encoding.

        Example usage:

        ```py
            Encoding(name="base16", code="f",
            status="default", description="hexadecimal")
        ```

        For compatibility with the [multibase table](https://github.com/multiformats/multibase/raw/master/multibase.csv),
        the `name` argument can alternatively be specified as `encoding`:

        ```py
            Encoding(encoding="base16", code="f",
            status="default", description="hexadecimal")
        ```
    """

    _name: str
    _code: str
    _status: Literal["draft", "candidate", "default"]
    _description: str

    def __init__(self, *,
                 name: str,
                 code: str,
                 status: str = "draft",
                 description: str = ""
                ):
        for arg in (name, code, status, description):
            if not isinstance(arg, str):
                raise TypeError(f"Expected string, found {repr(arg)}.")
        name = Encoding._validate_name(name)
        code = Encoding.validate_code(code)
        status = Encoding._validate_status(status)
        self._name = name
        self._code = code
        self._status = status
        self._description = description

    @staticmethod
    def _validate_name(name: Optional[str]) -> str:
        assert name is not None
        if not re.match(r"^[a-z][a-z0-9_-]+$", name): # ensures len(name) > 1
            raise ValueError(f"Invalid multibase encoding name {repr(name)}")
        return name

    @staticmethod
    def validate_code(code: str) -> str:
        """
            Validates a multibase code and transforms it to single-character format (if in hex format).
        """
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
            Printable version of `Encoding.code`:

            - if the code is a single non-printable ASCII character, returns the hex string of its byte
            - otherwise, returns the code itself
        """
        code = self.code
        ord_code = ord(code)
        if ord_code not in range(0x20, 0x7F):
            return "0x"+base16.encode(bytes([ord_code]))
        return code

    @property
    def status(self) -> Literal["draft", "candidate", "default"]:
        """ Encoding status. Must be 'draft', 'candidate' or 'default'."""
        return self._status

    @property
    def description(self) -> str:
        """ Encoding description. """
        return self._description

    @property
    def name(self) -> str:
        """
            Encoding name. Must satisfy the following:

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
        enc = raw_encoding.get(self.name)
        if enc is None:
            raise NotImplementedError(f"Encoding/decoding for {repr(self.name)} is not yet implemented.")
        return enc.encode

    @property
    def raw_decoder(self) -> RawDecoder:
        """
            Returns the raw encoder for this encoding:
            given a string without the multibase prefix, it produces the decoded data.
        """
        enc = raw_encoding.get(self.name)
        if enc is None:
            raise NotImplementedError(f"Encoding/decoding for {repr(self.name)} is not yet implemented.")
        return enc.decode

    def encode(self, data: bytes) -> str:
        """
            Encodes bytes into a multibase string: it first uses `Encoding.raw_encoder`,
            and then prepends the multibase prefix given by `Encoding.code` and returns
            the resulting multibase string.

            Example usage:

            ```py
            >>> base32 = multibase.encoding("base32")
            >>> base32.encode(b"Hello World!")
            'bjbswy3dpeblw64tmmqqq'
            ```
        """
        return self.code+self.raw_encoder(data)

    def decode(self, data: str) -> bytes:
        """
            Decodes a multibase string into bytes: it first checks that the multibase
            prefix matches the value specified by `Encoding.code`, then uses
            `Encoding.raw_encoder` on the string without prefix and returns the bytes.

            Example usage:

            ```py
            >>> base32 = multibase.encoding("base32")
            >>> base32.decode("bjbswy3dpeblw64tmmqqq")
            b'Hello World!'
            ```
        """
        encoding = encoding_of(data)
        if encoding != self:
            raise ValueError(f"Expected {repr(self.name)} encoding, "
                             f"found {repr(encoding.name)} encoding instead.")
        return self.raw_decoder(data[1:])

    def to_json(self) -> Mapping[str, str]:
        """
            Returns a JSON dictionary representation of this `Encoding` object,
            compatible with the one from the multibase.csv table found in the
            [multibase spec](https://github.com/multiformats/multibase).

            Example usage:

            ```py
            >>> base32 = multibase.encoding("base32")
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
        return f"Encoding({', '.join(f'{k}={v}' for k, v in self.to_json().items())})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Encoding):
            return NotImplemented
        return self.to_json() == other.to_json()


def encoding(name: Optional[str] = None, *, code: Optional[str] = None) -> Encoding:
    """
        Gets the multibase encoding with given name (if a string of length >= 2 is passed)
        or multibase code (if a string of length 1 is passed). Raises `ValueError` if the
        empty string is passed. Raises `KeyError` if no such encoding exists.

        Example usage:

        ```py
        >>> multibase.encoding(name="base8")
        Encoding(encoding='base8', code='7',
                 status='draft', description='octal')
        >>> multibase.encoding(code="t")
        Encoding(encoding='base32hexpad', code='t', status='candidate',
                 description='rfc4648 case-insensitive - with padding')
        ```
    """
    if (name is None) == (code is None):
        raise ValueError("Must specify exactly one between encoding name and code.")
    if code is not None:
        if code not in _code_table:
            raise KeyError(f"No multibase encoding with code {repr(code)}.")
        return _code_table[code]
    if name not in _name_table:
        raise KeyError(f"No multibase encoding named {repr(name)}.")
    return _name_table[name]

def get(name: Optional[str] = None, *, code: Optional[str] = None) -> Encoding:
    """
        An alias to `encoding`, for uniformity of API with other sub-modules.
    """
    return encoding(name, code=code)

def exists(name: Optional[str] = None, *, code: Optional[str] = None) -> bool:
    """
        Checks whether a multibase encoding with given name (if a string of length >= 2 is passed)
        or multibase code (if a string of length 1 is passed) exists. Raises `ValueError` if the
        empty string is passed.

        Example usage:

        ```py
        >>> multibase.exists("base8")
        True
        >>> multibase.exists('t')
        True
        ```
    """
    if (name is None) == (code is None):
        raise ValueError("Must specify exactly one between encoding name and code.")
    if code is not None:
        code = Encoding.validate_code(code)
        return code in _code_table
    return name in _name_table


def register(enc: Encoding, *, overwrite: bool = False) -> None:
    """
        Registers a given multibase encoding. The optional keyword argument `overwrite` (default: `False`)
        can be used to overwrite a multibase encoding with existing code.

        If `overwrite` is `False`, raises `ValueError` if a multibase encoding with the same name or code already exists.
        If `overwrite` is `True`, raises `ValueError` if a multibase encoding with the same name but different code already exists.

        Example usage:

        ```py
        >>> base45 = Encoding(encoding="base45", code=":",
                              status="draft", description="base45 encoding")
        >>> multibase.register(base45)
        >>> multibase.encoding("base45")
        Encoding(encoding='base45', code=':', status='draft',
                 description='base45 encoding')
        ```
    """
    if not overwrite and enc.code in _code_table:
        raise ValueError(f"Multibase encoding with code {repr(enc.code)} already exists: {_code_table[enc.code]}")
    if enc.name in _name_table and _name_table[enc.name].code != enc.code:
        raise ValueError(f"Multibase encoding with name {repr(enc.name)} already exists: {_name_table[enc.name]}")
    _code_table[enc.code] = enc
    _name_table[enc.name] = enc


def unregister(name: Optional[str] = None, *, code: Optional[str] = None) -> None:
    """
        Unregisters the multibase encoding with given name (if a string is passed) or code (if an int is passed).
        Raises `KeyError` if no such multibase encoding exists.

        Example usage:

        ```py
        >>> base45 = Encoding(encoding="base45", code=":",
                              status="draft", description="base45 encoding")
        >>> multibase.register(base45)
        >>> multibase.encoding("base45")
        Encoding(encoding='base45', code=':', status='draft',
                 description='base45 encoding')
        >>> multibase.unregister(code=":")
        >>> multibase.exists("base45")
        False
        ```
    """
    enc = encoding(name=name, code=code)
    del _code_table[enc.code]
    del _name_table[enc.name]


def table() -> Iterator[Encoding]:
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


def encoding_of(data: str) -> Encoding:
    """
        Returns the multibase encoding for the data, according to the code specified by its prefix.
        Raises `ValueError` if the empty string is passed.
        Raises `KeyError` if no encoding exists with that code.

        Example usage:

        ```py
        >>> multibase.encoding_of("mSGVsbG8gd29ybGQh")
        Encoding(encoding='base64', code='m', status='default',
                 description='rfc4648 no padding')
        ```
    """
    if len(data) == 0:
        raise ValueError("Empty string is not valid for encoded data.")
    for code in _code_table:
        if data.startswith(code):
            return encoding(code=code)
    raise KeyError("No known multibase code is a prefix of the given data.")


def encode(data: bytes, enc: Union[str, "Encoding"]) -> str:
    """
        Encodes the given bytes into a multibase string using the given encoding.
        If the encoding is passed by name or code (i.e. as a string), the `encoding`
        function is used to retrieve it. Encoding is performed by `Encoding.encode`.

        Example usage:

        ```py
        >>> multibase.encode(b"Hello world!", "base64")
        'mSGVsbG8gd29ybGQh'
        ```
    """
    if isinstance(enc, str):
        enc = encoding(enc)
    return enc.encode(data)


def decode(data: str) -> bytes:
    """
        Decodes the given multibase string into bytes.
        The encoding is inferred using the `encoding_of` function.
        Decoding is then performed by `Encoding.decode`.

        Example usage:

        ```py
        >>> multibase.decode("mSGVsbG8gd29ybGQh")
        b'Hello world!'
        ```
    """
    enc = encoding_of(data)
    return enc.decode(data)


def build_multibase_tables(encodings: Iterable[Encoding]) -> Tuple[Dict[str, Encoding], Dict[str, Encoding]]:
    """
        Creates code->encoding and name->encoding mappings from a finite iterable of encodings, returning the mappings.

        Raises `ValueError` if the same encoding code or name is encountered multiple times

        Example usage:

        ```py
            code_table, name_table = build_multicodec_tables(encodings)
        ```
    """
    code_table: Dict[str, Encoding] = {}
    name_table: Dict[str, Encoding] = {}
    for e in encodings:
        if e.code in code_table:
            raise ValueError(f"Multicodec name {e.name} appears multiple times in table.")
        code_table[e.code] = e
        if e.name in name_table:
            raise ValueError(f"Multicodec name {e.name} appears multiple times in table.")
        name_table[e.name] = e
    return code_table, name_table

# Create the global code->multicodec and name->multicodec mappings.
# _code_table: Dict[str, Encoding] = {}
# _name_table: Dict[str, Encoding] = {}
with importlib_resources.open_text("multiformats.multibase", "multibase-table.csv") as csv_table:
    reader = csv.DictReader(csv_table)
    clean_rows = ({k.strip(): v.strip() for k, v in row.items()} for row in reader)
    renamed_rows = ({(k if k != "encoding" else "name"): v for k, v in row.items()} for row in clean_rows)
    multicodecs = (Encoding(**row) for row in renamed_rows)
    _code_table, _name_table = build_multibase_tables(multicodecs)


# additional docs info
__pdoc__ = {
    "build_multibase_tables": False # exclude from docs
}
