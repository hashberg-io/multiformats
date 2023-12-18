"""
    Implementation of the `multicodec spec <https://github.com/multiformats/multicodec>`_.

    Suggested usage:

    >>> from multiformats import multicodec
"""

from __future__ import annotations

import importlib.resources as importlib_resources
from io import BufferedIOBase
import json
import re
import sys
from typing import AbstractSet, Any, cast, Dict, Iterable, Iterator, Mapping, Optional, overload, Set, Sequence, Tuple, Type, TypeVar, Union
from typing_extensions import Literal, Final
from typing_validation import validate
from multiformats_config.multicodec import load_multicodec_table

from multiformats import varint
from multiformats.varint import BytesLike
from .err import MulticodecKeyError, MulticodecValueError

def _hexcode(code: int) -> str:
    hexcode = hex(code)
    if len(hexcode) % 2 != 0:
        hexcode = "0x0"+hexcode[2:]
    return hexcode

MulticodecStatus = Literal[
    "draft", "permanent", "deprecated"
]
"""
    Literal type of possible values for the :attr:`Multicodec.status` property.
"""

MulticodecStatusValues: Final[Tuple[MulticodecStatus, ...]] = (
    "draft", "permanent", "deprecated"
)
"""
    Collection of possible values for the :attr:`Multicodec.status` property.
"""

class Multicodec:
    """
        Container class for a multicodec.

        Example usage:

        >>> Multicodec(**{
        ...     'name': 'cidv1', 'tag': 'cid', 'code': '0x01',
        ...     'status': 'permanent', 'description': 'CIDv1'})
        Multicodec(name='cidv1', tag='cid', code=1,
                   status='permanent', description='CIDv1')

        :param name: the multicodec name
        :type name: :obj:`str`
        :param tag: the multicodec tag
        :type tag: :obj:`str`
        :param code: the multicodec code, as integer or ``0xYZ`` hex-string
        :type code: :obj:`int` or :obj:`str`
        :param status: the multicodec status
        :type status: ``'draft'`` or ``'permanent'``, *optional*
        :param description: the multicodec description
        :type description: :obj:`str`, *optional*
    """

    _name: str
    _tag: str
    _code: int
    _status: MulticodecStatus
    _description: str

    __slots__ = ("__weakref__", "_name", "_tag", "_code", "_status", "_description")

    def __new__(cls,
                name: str,
                tag: str,
                code: Union[int, str],
                status: str = "draft",
                description: str = ""
               ) -> "Multicodec":
        # pylint: disable = too-many-arguments
        for arg in (name, tag, status, description):
            validate(arg, str)
        validate(code, Union[int, str])
        name = Multicodec._validate_name(name)
        code = Multicodec.validate_code(code)
        status = Multicodec._validate_status(status)
        instance = super().__new__(cls)
        instance._name = name
        instance._tag = tag
        instance._code = code
        instance._status = status
        instance._description = description
        return instance

    def __getnewargs__(self) -> tuple[str, str, int, MulticodecStatus, str]:
        return (self.name, self.tag, self.code, self.status, self.description)

    @staticmethod
    def _validate_name(name: str) -> str:
        if not re.match(r"^[a-z][a-z0-9_-]+$", name):
            raise MulticodecValueError(f"Invalid multicodec name {repr(name)}")
        return name

    @staticmethod
    def validate_code(code: Union[int, str]) -> int:
        """
            Validates a multicodec code and transforms it to unsigned integer format (if in hex format).

            :param code: the multicodec code, as integer or `0xYZ` hex-string
            :type code: :obj:`int` or :obj:`str`

            :raises ValueError: if the code is invalid

        """
        if isinstance(code, str):
            if code.startswith("0x"):
                code = code[2:]
            code = int(code, base=16)
        if code < 0:
            raise MulticodecValueError(f"Invalid multicodec code {repr(code)}.")
        return code

    @staticmethod
    def _validate_status(status: str) -> MulticodecStatus:
        if status not in MulticodecStatusValues:
            raise MulticodecValueError(f"Invalid multicodec status {repr(status)}.")
        return cast(MulticodecStatus, status)

    @property
    def name(self) -> str:
        """
            Multicodec name. Must satisfy the following:

            .. code-block:: python

                re.match(r"^[a-z][a-z0-9_-]+$", name)
        """
        return self._name

    @property
    def tag(self) -> str:
        """ Multicodec tag. """
        return self._tag

    @property
    def code(self) -> int:
        """ Multicodec code. Must be a non-negative integer. """
        return self._code

    @property
    def hexcode(self) -> str:
        """
            Multicodec code as a hex string (with hex digits zero-padded to even length):

            Example usage:

            >>> m = multicodec.get(1)
            >>> m.code
            1
            >>> m.hexcode
            '0x01'

        """
        return _hexcode(self._code)

    @property
    def status(self) -> MulticodecStatus:
        """ Multicodec status. """
        return self._status

    @property
    def description(self) -> str:
        """ Multicodec description. """
        return self._description

    @property
    def is_private_use(self) -> bool:
        """
            Whether this multicodec code is reserved for private use,
            i.e. whether it is in ``range(0x300000, 0x400000)``.
        """
        return self.code in range(0x300000, 0x400000)

    def wrap(self, raw_data: BytesLike) -> bytes:
        """
            Wraps raw binary data into multicodec data:

            .. code-block:: console

                <raw data> --> <code><raw data>

            Example usage:

            >>> ip4 = multicodec.get("ip4")
            >>> ip4
            Multicodec(name='ip4', tag='multiaddr', code='0x04', status='permanent', description='')
            >>> raw_data = bytes([192, 168, 0, 254])
            >>> multicodec_data = ip4.wrap(raw_data)
            >>> raw_data.hex()
              'c0a800fe'
            >>> multicodec_data.hex()
            '04c0a800fe'
            >>> varint.encode(0x04).hex()
            '04' #       0x04 ^^^^ is the multicodec code for 'ip4'

            :param raw_data: the raw data to be wrapped
            :type raw_data: :obj:`~multiformats.varint.BytesLike`

            :raise ValueError: see :func:`~multiformats.varint.encode`

        """
        return varint.encode(self.code)+raw_data

    def unwrap(self, multicodec_data: BytesLike) -> bytes:
        """
            Unwraps multicodec binary data to raw data:

            .. code-block::

                <code><raw data> --> <raw data>

            Additionally checks that the code listed by the data
            matches the code of this multicodec.

            Example usage:

            >>> multicodec_data = bytes.fromhex("c0a800fe")
            >>> raw_data = ip4.unwrap(multicodec_data)
            >>> multicodec_data.hex()
            '04c0a800fe'
            >>> raw_data.hex()
              'c0a800fe'
            >>> varint.encode(0x04).hex()
            '04' #       0x04 ^^^^ is the multicodec code for 'ip4'

            :param multicodec_data: the multicodec data to be unwrapped
            :type multicodec_data: :obj:`~multiformats.varint.BytesLike`

            :raise ValueError: if the unwrapped multicodec code does not match this multicodec's code
            :raise ValueError: see :func:`multiformats.multicodec.unwrap_raw`
            :raise KeyError: see :func:`multiformats.multicodec.unwrap_raw`
        """
        code, _, raw_data = unwrap_raw(multicodec_data)
        # code, _, raw_data = varint.decode_raw(multicodec_data)
        if code != self.code:
            hexcode = _hexcode(code)
            raise MulticodecValueError(f"Found code {hexcode} when unwrapping data, expected code {self.hexcode}.")
        return bytes(raw_data)

    def to_json(self) -> Mapping[str, str]:
        """
            Returns a JSON dictionary representation of this multicodec object.

            Example usage:

            >>> m = multicodec.get(1)
            >>> m.to_json()
            {'name': 'cidv1', 'tag': 'cid', 'code': '0x01',
             'status': 'permanent', 'description': 'CIDv1'}

        """
        return {
            "name": self.name,
            "tag": self.tag,
            "code": self.hexcode,
            "status": self.status,
            "description": self.description
        }

    def __str__(self) -> str:
        if exists(self.name) and get(self.name) == self:
            return f"multicodec({repr(self.name)}, tag={repr(self.tag)})"
        return repr(self)

    def __repr__(self) -> str:
        return f"Multicodec({', '.join(f'{k}={repr(v)}' for k, v in self.to_json().items())})"

    @property
    def _as_tuple(self) -> Tuple[Type["Multicodec"], str, str, int, MulticodecStatus]:
        return (Multicodec, self.name, self.tag, self.code, self.status)

    def __hash__(self) -> int:
        return hash(self._as_tuple)

    def __eq__(self, other: Any) -> bool:
        if self is other:
            return True
        if not isinstance(other, Multicodec):
            return NotImplemented
        return self._as_tuple == other._as_tuple


def get(name: Optional[str] = None, *, code: Optional[int] = None) -> Multicodec:
    """
        Gets the multicodec with given name or code.

        Example usage:

        >>> multicodec.get("identity")
        Multicodec(name='identity', tag='multihash', code=0,
                   status='permanent', description='raw binary')
        >>> multicodec.get(code=0x01)
        Multicodec(name='cidv1', tag='ipld', code=1,
                   status='permanent', description='CIDv1')

        :param name: the multicodec name
        :type name: :obj:`str` or :obj:`None`, *optional*
        :param code: the multicodec code
        :type code: :obj:`int` or :obj:`None`, *optional*

        :raises KeyError: if no such multicodec exists
        :raises ValueError: unless exactly one of ``name`` and ``code`` is specified
    """
    validate(name, Optional[str])
    validate(code, Optional[int])
    if (name is None) == (code is None):
        raise MulticodecValueError("Must specify exactly one between 'name' and 'code'.")
    if name is not None:
        if name not in _name_table:
            raise MulticodecKeyError(f"No multicodec named {repr(name)}.")
        return _name_table[name]
    if code not in _code_table:
        raise MulticodecKeyError(f"No multicodec with code {repr(code)}.")
    return _code_table[code]


def multicodec(name: str, *, tag: Optional[str] = None) -> Multicodec:
    """
        An alias for :func:`get`, for use with multicodec name only.
        If a tag is passed, ensures that the multicodec tag matches the one given.

        Example usage:

        >>> from multiformats.multicodec import multicodec
        >>> multicodec("identity")
        Multicodec(name='identity', tag='multihash', code=0,
                   status='permanent', description='raw binary')

        :param name: the multicodec name
        :type name: :obj:`str`
        :param tag: the optional multicodec tag
        :type tag: :obj:`str` or :obj:`None`, *optional*

        :raises KeyError: see :func:`get`
    """
    codec = get(name)
    if tag is not None and codec.tag != tag:
        raise MulticodecKeyError(f"Multicodec {repr(name)} exists, but its tag is not {repr(tag)}.")
    return codec


def exists(name: Union[None, str, Multicodec] = None, *, code: Optional[int] = None) -> bool:
    """
        Checks whether there is a multicodec with the given name or code.

        Example usage:

        >>> multicodec.exists("identity")
        True
        >>> multicodec.exists(code=0x01)
        True

        :param name: the multicodec name
        :type name: :obj:`str` or :obj:`None`, *optional*
        :param code: the multicodec code
        :type code: :obj:`int` or :obj:`None`, *optional*

        :raises ValueError: unless exactly one of ``name`` and ``code`` is specified
    """
    validate(name, Optional[str])
    validate(code, Optional[int])
    if (name is None) == (code is None):
        raise MulticodecValueError("Must specify exactly one between 'name' and 'code'.")
    if name is not None:
        return name in _name_table
    return code in _code_table


def wrap(codec: Union[str, int, Multicodec], raw_data: BytesLike) -> bytes:
    """
        Wraps raw binary data into multicodec data:

        .. code-block::

            <raw data> --> <code><raw data>

        Example usage:

        >>> raw_data = bytes([192, 168, 0, 254])
        >>> multicodec_data = multicodec.wrap("ip4", raw_data)
        >>> raw_data.hex()
          'c0a800fe'
        >>> multicodec_data.hex()
        '04c0a800fe'
        >>> varint.encode(0x04).hex()
        '04' #       0x04 ^^^^ is the multicodec code for 'ip4'

        :param codec: the multicodec that the raw data refers to
        :type codec: :obj:`str`, :obj:`int` or :class:`Multicodec`
        :param raw_data: the raw binary data
        :type raw_data: :obj:`~multiformats.varint.BytesLike`

        :raises KeyError: see :func:`get`
    """
    if isinstance(codec, str):
        codec = get(codec)
    elif isinstance(codec, int):
        codec = get(code=codec)
    else:
        validate(codec, Multicodec)
    return codec.wrap(raw_data)

def unwrap(multicodec_data: BytesLike) -> Tuple[Multicodec, bytes]:
    """
        Unwraps multicodec binary data to multicodec and raw data:

        Example usage:

        >>> multicodec_data = bytes.fromhex("04c0a800fe")
        >>> codec, raw_data = multicodec.unwrap(multicodec_data)
        >>> multicodec_data.hex()
        '04c0a800fe'
        >>> raw_data.hex()
          'c0a800fe'
        >>> codec
        Multicodec(name='ip4', tag='multiaddr', code='0x04', status='permanent', description='')

        :param multicodec_data: the binary data prefixed with multicodec code
        :type multicodec_data: :obj:`~multiformats.varint.BytesLike`

        :raises KeyError: if the code does not correspond to a know multicodec
    """
    code, _, raw_data = unwrap_raw(multicodec_data)
    return get(code=code), bytes(raw_data)


_BufferedIOT = TypeVar("_BufferedIOT", bound=BufferedIOBase)

@overload
def unwrap_raw(multicodec_data: BytesLike) -> Tuple[int, int, memoryview]:
    ...

@overload
def unwrap_raw(multicodec_data: _BufferedIOT) -> Tuple[int, int, _BufferedIOT]:
    ...

def unwrap_raw(multicodec_data: Union[BytesLike, BufferedIOBase]) -> Tuple[int, int, Union[memoryview, BufferedIOBase]]:
    """
        Similar to :func:`unwrap`, but returns a triple of multicodec code, number of bytes read and remaining bytes.

        Example usage:

        >>> multicodec_data = bytes.fromhex("04c0a800fe")
        >>> code, num_bytes_read, remaining_bytes = multicodec.unwrap_raw(multicodec_data)
        >>> code
        4
        >>> num_bytes_read
        1
        >>> remaining_bytes
        <memory at 0x000001BE46B17640>
        >>> multicodec_data.hex()
        '04c0a800fe'
        >>> bytes(remaining_bytes).hex()
          'c0a800fe'

        :param multicodec_data: the binary data prefixed with multicodec code
        :type multicodec_data: :obj:`~multiformats.varint.BytesLike`

        :raises KeyError: if the code does not correspond to a know multicodec
    """
    code, n, raw_data = varint.decode_raw(multicodec_data)
    if not exists(code=code):
        raise MulticodecKeyError(f"No multicodec is known with unwrapped code {_hexcode(code)}.")
    return code, n, raw_data


def validate_multicodec(codec: Multicodec) -> None:
    """
        Validates an instance of :class:`Multicodec`.
        If the multicodec is registered (i.e. valid), no error is raised.

        :param codec: the instance to be validated
        :type codec: :class:`Multicodec`

        :raises KeyError: if no multicodec with the given name is registered
        :raises ValueError: if a multicodec with the given name is registered, but is different from the one given

    """
    validate(codec, Multicodec)
    mc = get(codec.name)
    if mc != codec:
        raise MulticodecValueError(f"Multicodec named {codec.name} exists, but is not the one given.")

def register(codec: Multicodec, *, overwrite: bool = False) -> None:
    """
        Registers a given multicodec.

        Example usage:

        >>> m = Multicodec("my-multicodec", "my-tag", 0x300001, "draft", "...")
        >>> multicodec.register(m)
        >>> multicodec.exists(code=0x300001)
        True
        >>> multicodec.get(code=0x300001).name
        'my-multicodec'
        >>> multicodec.get(code=0x300001).is_private_use
        True

        :param codec: the multicodec to register
        :type codec: :class:`Multicodec`
        :param overwrite: whether to overwrite a multicodec with existing code (optional, default :obj:`False`)
        :type overwrite: :obj:`bool`, *optional*

        :raises ValueError: if ``overwrite`` is :obj:`False` and a multicodec with the same name or code already exists
        :raises ValueError: if ``overwrite`` is :obj:`True` and a multicodec with the same name but different code already exists
    """
    validate(codec, Multicodec)
    validate(overwrite, bool)
    if not overwrite and codec.code in _code_table:
        raise MulticodecValueError(f"Multicodec with code {repr(codec.code)} already exists: {_code_table[codec.code]}")
    if codec.name in _name_table and _name_table[codec.name].code != codec.code:
        raise MulticodecValueError(f"Multicodec with name {repr(codec.name)} already exists: {_name_table[codec.name]}")
    _code_table[codec.code] = codec
    _name_table[codec.name] = codec


def unregister(name: Optional[str] = None, *, code: Optional[int] = None) -> None:
    """
        Unregisters the multicodec with given name or code.

        Example usage:

        >>> multicodec.unregister(code=0x01) # cidv1
        >>> multicodec.unregister(code=0x01)
        False

        :param name: the multicodec name
        :type name: :obj:`str` or :obj:`None`, *optional*
        :param code: the multicodec code
        :type code: :obj:`int` or :obj:`None`, *optional*

        :raises KeyError: if no such multicodec exists
        :raises ValueError: unless exactly one of ``name`` and ``code`` is specified
    """
    m = get(name, code=code)
    del _code_table[m.code]
    del _name_table[m.name]



def table(*,
          tag: Union[None, str, AbstractSet[str], Sequence[str]] = None,
          status: Union[None, str, AbstractSet[str], Sequence[str]] = None) -> Iterator[Multicodec]:
    """
        Iterates through the registered multicodecs, in order of ascending code.

        Example usage:

        >>> len(list(multicodec.table())) # multicodec.table() returns an iterator
        482
        >>> selected = multicodec.table(tag=["cid", "cid", "multiaddr"], status="permanent")
        >>> [m.code for m in selected]
        [1, 4, 6, 41, 53, 54, 55, 56, 81, 85, 112, 113, 114, 120,
         144, 145, 146, 147, 148, 149, 150, 151, 152, 176, 177,
         178, 192, 193, 290, 297, 400, 421, 460, 477, 478, 479, 512]

        :param tag: one or more tags to be selected (if :obj:`None`, all tags are included)
        :type tag: :obj:`None`, :obj:`str`, set or sequence of :obj:`str`, *optional*
        :param status: one or more statuses to be selected (if :obj:`None`, all statuses are included)
        :type status: :obj:`None`, :obj:`str`, set or sequence of :obj:`str`, *optional*

    """
    validate(tag, Union[None, str, AbstractSet[str], Sequence[str]])
    validate(status, Union[None, str, AbstractSet[str], Sequence[str]])
    tags: Union[None, AbstractSet[str], Sequence[str]]
    if tag is None:
        tags = None
    elif isinstance(tag, str):
        tags = [tag]
    else:
        tags = tag
    statuses: Union[None, AbstractSet[str], Sequence[str]]
    if status is None:
        statuses = None
    elif isinstance(status, str):
        statuses = [status]
    else:
        statuses = status
    for code in sorted(_code_table.keys()):
        m = _code_table[code]
        if tags is not None and m.tag not in tags:
            continue
        if statuses is not None and m.status not in statuses:
            continue
        yield m

_code_table, _name_table = load_multicodec_table()

# def build_multicodec_tables(codecs: Iterable[Multicodec], *,
#                             allow_private_use: bool = False) -> Tuple[Dict[int, Multicodec], Dict[str, Multicodec]]:
#     """
#         Creates code->multicodec and name->multicodec mappings from a finite iterable of multicodecs,
#         returning the mappings.

#         Example usage:

#         >>> code_table, name_table = build_multicodec_tables(codecs)

#         :param codecs: multicodecs to be registered
#         :type codecs: iterable of :class:`Multicodec`
#         :param allow_private_use: whether to allow multicodec entries with private use codes in ``range(0x300000, 0x400000)`` (default :obj:`False`)
#         :type allow_private_use: :obj:`bool`, *optional*

#         :raises ValueError: if ``allow_private_use`` and a multicodec with private use code is encountered
#         :raises ValueError: if the same multicodec code is encountered multiple times, unless exactly one of the multicodecs
#         has permanent status (in which case that codec is the one inserted in the table)
#         :raises ValueError: if the same name is encountered multiple times

#     """
#     # validate(codecs, Iterable[Multicodec]) # TODO: not yet properly supported by typing-validation
#     validate(allow_private_use, bool)
#     code_table: Dict[int, Multicodec] = {}
#     name_table: Dict[str, Multicodec] = {}
#     overwritten_draft_codes: Set[int] = set()
#     for m in codecs:
#         if not allow_private_use and m.is_private_use:
#             raise MulticodecValueError(f"Private use multicodec not allowed: {m}")
#         if m.code in code_table:
#             if code_table[m.code].status == "permanent":
#                 if m.status == "draft":
#                     # this draft code has been superseded by a permanent one, skip it
#                     continue
#                 raise MulticodecValueError(f"Multicodec code {m.hexcode} appears multiple times in table.")
#             if m.status != "permanent":
#                 # overwriting draft code with another draft code: dodgy, need to check at the end
#                 overwritten_draft_codes.add(m.code)
#         code_table[m.code] = m
#         if m.name in name_table:
#             raise MulticodecValueError(f"Multicodec name {m.name} appears multiple times in table.")
#         name_table[m.name] = m
#     for code in overwritten_draft_codes:
#         m = code_table[code]
#         if m.status != "permanent":
#             raise MulticodecValueError(f"Code {m.code} appears multiple times in table, "
#                               "but none of the associated multicodecs is permanent.")
#     return code_table, name_table

# Create the global code->multicodec and name->multicodec mappings.
# _code_table: Dict[int, Multicodec] = {}
# _name_table: Dict[str, Multicodec] = {}
# with importlib_resources.open_text("multiformats.multicodec", "multicodec-table.json") as _table_f:
#     _table_json = json.load(_table_f)
#     _code_table, _name_table = build_multicodec_tables(Multicodec(**row) for row in _table_json)
