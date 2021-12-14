"""
    Implementation of the [multicodec spec](https://github.com/multiformats/multicodec).

    The `Multicodec` class provides a container for multicodec data:

    ```py
    >>> from multiformats import multicodec
    >>> from multiformats.multicodec import Multicodec
    >>> Multicodec("identity", "multihash", 0x00, "permanent", "raw binary")
    Multicodec(name='identity', tag='multihash', code=0,
               status='permanent', description='raw binary')
    ```

    Core functionality is provided by the `get` and `exists` functions, which can be used to check
    whether a multicodec with given name or code is known, and if so to get the corresponding object:

    ```py
    >>> multicodec.exists("identity")
    True
    >>> multicodec.exists(code=0x01)
    True
    >>> multicodec.get("identity")
    Multicodec(name='identity', tag='multihash', code=0,
               status='permanent', description='raw binary')
    >>> multicodec.get(code=0x01)
    Multicodec(name='cidv1', tag='cid', code=1,
               status='permanent', description='CIDv1')
    ```

    The `table` function can be used to iterate through known multicodecs, optionally restricting
    to one or more tags and/or statuses:

    ```py
    >>> len(list(multicodec.table())) # multicodec.table() returns an iterator
    482
    >>> selected = multicodec.table(tag=["cid", "ipld", "multiaddr"], status="permanent")
    >>> [m.code for m in selected]
    [1, 4, 6, 41, 53, 54, 55, 56, 81, 85, 112, 113, 114, 120,
     144, 145, 146, 147, 148, 149, 150, 151, 152, 176, 177,
     178, 192, 193, 290, 297, 400, 421, 460, 477, 478, 479, 512]
    ```

"""

import csv
import importlib.resources as importlib_resources
import re
import sys
from typing import AbstractSet, Any, cast, Dict, Iterable, Iterator, Mapping, Optional, Set, Sequence, Tuple, Union
from typing_extensions import Literal
from typing_validation import validate


class Multicodec:
    """
        Container class for a multicodec.

        Example usage:

        ```py
            >>> Multicodec(**{
            ...     'name': 'cidv1', 'tag': 'cid', 'code': '0x01',
            ...     'status': 'permanent', 'description': 'CIDv1'})
            Multicodec(name='cidv1', tag='cid', code=1,
                       status='permanent', description='CIDv1')
        ```

    """

    _name: str
    _tag: str
    _code: int
    _status: Literal["draft", "permanent"]
    _description: str

    def __init__(self, *,
                 name: str,
                 tag: str,
                 code: Union[int, str],
                 status: str = "draft",
                 description: str = ""
                ):
        for arg in (name, tag, status, description):
            validate(arg, str)
        validate(code, Union[int, str])
        name = Multicodec._validate_name(name)
        code = Multicodec.validate_code(code)
        status = Multicodec._validate_status(status)
        self._name = name
        self._tag = tag
        self._code = code
        self._status = status
        self._description = description

    @staticmethod
    def _validate_name(name: str) -> str:
        if not re.match(r"^[a-z][a-z0-9_-]+$", name):
            raise ValueError(f"Invalid multicodec name {repr(name)}")
        return name

    @staticmethod
    def validate_code(code: Union[int, str]) -> int:
        """
            Validates a multibase code and transforms it to unsigned integer format (if in hex format).
        """
        if isinstance(code, str):
            if code.startswith("0x"):
                code = code[2:]
            code = int(code, base=16)
        if code < 0:
            raise ValueError(f"Invalid multicodec code {repr(code)}.")
        return code

    @staticmethod
    def _validate_status(status: str) -> Literal["draft", "permanent"]:
        if status not in ("draft", "permanent"):
            raise ValueError(f"Invalid multicodec status {repr(status)}.")
        return cast(Literal["draft", "permanent"], status)

    @property
    def name(self) -> str:
        """
            Multicodec name. Must satisfy the following:

            ```py
            re.match(r"^[a-z][a-z0-9_-]+$", name)
            ```
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

            ```py
            >>> m = multicodec.get(1)
            >>> m.code
            1
            >>> m.hexcode
            '0x01'
            ```
        """
        code = hex(self.code)
        if len(code) % 2 != 0:
            code = "0x0"+code[2:]
        return code

    @property
    def status(self) -> Literal["draft", "permanent"]:
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
            i.e. whether it is in `range(0x300000, 0x400000)`.
        """
        return self.code in range(0x300000, 0x400000)

    def to_json(self) -> Mapping[str, str]:
        """
            Returns a JSON dictionary representation of this multicodec object.

            Example usage:

            ```py
            >>> m = multicodec.get(1)
            >>> m.to_json()
            {'name': 'cidv1', 'tag': 'cid', 'code': '0x01',
             'status': 'permanent', 'description': 'CIDv1'}
            ```
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
            return f"multicodec.get({repr(self.name)})"
        return repr(self)

    def __repr__(self) -> str:
        return f"Multicodec({', '.join(f'{k}={repr(v)}' for k, v in self.to_json().items())})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Multicodec):
            return NotImplemented
        return self.to_json() == other.to_json()


def get(name: Optional[str] = None, *, code: Optional[int] = None) -> Multicodec:
    """
        Gets the multicodec with given name or code.
        Raises `KeyError` if no such multicodec exists.
        Exactly one of `name` and `code` must be specified.

        Example usage:

        ```py
        >>> multicodec.get("identity")
        Multicodec(name='identity', tag='multihash', code=0,
                   status='permanent', description='raw binary')
        >>> multicodec.get(code=0x01)
        Multicodec(name='cidv1', tag='ipld', code=1,
                   status='permanent', description='CIDv1')
        ```
    """
    validate(name, Optional[str])
    validate(code, Optional[int])
    if (name is None) == (code is None):
        raise ValueError("Must specify exactly one between 'name' and 'code'.")
    if name is not None:
        if name not in _name_table:
            raise KeyError(f"No multicodec named {repr(name)}.")
        return _name_table[name]
    if code not in _code_table:
        raise KeyError(f"No multicodec with code {repr(code)}.")
    return _code_table[code]


def exists(name: Optional[str] = None, *, code: Optional[int] = None) -> bool:
    """
        Checks whether there is a multicodec with the given name or code.
        Exactly one of `name` and `code` must be specified.

        Example usage:

        ```py
        >>> multicodec.exists("identity")
        True
        >>> multicodec.exists(code=0x01)
        True
        ```
    """
    validate(name, Optional[str])
    validate(code, Optional[int])
    if (name is None) == (code is None):
        raise ValueError("Must specify exactly one between 'name' and 'code'.")
    if name is not None:
        return name in _name_table
    return code in _code_table


def register(m: Multicodec, *, overwrite: bool = False) -> None:
    """
        Registers a given multicodec. The optional keyword argument `overwrite` (default: `False`)
        can be used to overwrite a multicodec with existing code.

        When `overwrite` is `False`, raises `ValueError` if a multicodec with the same name or code already exists.
        When `overwrite` is `True`, raises `ValueError` if a multicodec with the same name but different code already exists.

        Example usage:

        ```py
            >>> m = Multicodec("my-multicodec", "my-tag", 0x300001, "draft", "...")
            >>> multicodec.register(m)
            >>> multicodec.exists(code=0x300001)
            True
            >>> multicodec.get(code=0x300001).name
            'my-multicodec'
            >>> multicodec.get(code=0x300001).is_private_use
            True
        ```
    """
    validate(m, Multicodec)
    validate(overwrite, bool)
    if not overwrite and m.code in _code_table:
        raise ValueError(f"Multicodec with code {repr(m.code)} already exists: {_code_table[m.code]}")
    if m.name in _name_table and _name_table[m.name].code != m.code:
        raise ValueError(f"Multicodec with name {repr(m.name)} already exists: {_name_table[m.name]}")
    _code_table[m.code] = m
    _name_table[m.name] = m


def unregister(name: Optional[str] = None, *, code: Optional[int] = None) -> None:
    """
        Unregisters the multicodec with given name or code.
        Raises `KeyError` if no such multicodec exists.

        Example usage:

        ```py
        >>> multicodec.unregister(code=0x01) # cidv1
        >>> multicodec.unregister(code=0x01)
        False
        ```
    """
    m = get(name, code=code)
    del _code_table[m.code]
    del _name_table[m.name]



def table(*,
          tag: Union[None, str, AbstractSet[str], Sequence[str]] = None,
          status: Union[None, str, AbstractSet[str], Sequence[str]] = None) -> Iterator[Multicodec]:
    """
        Iterates through the registered multicodecs, in order of ascending code.
        The optional keyword arguments `tag` and `status` can be used to restrict the iterator
        to multicodecs with a given `tag` or `status` respectively.

        Example usage:


        ```py
        >>> len(list(multicodec.table())) # multicodec.table() returns an iterator
        482
        >>> selected = multicodec.table(tag=["cid", "cid", "multiaddr"], status="permanent")
        >>> [m.code for m in selected]
        [1, 4, 6, 41, 53, 54, 55, 56, 81, 85, 112, 113, 114, 120,
         144, 145, 146, 147, 148, 149, 150, 151, 152, 176, 177,
         178, 192, 193, 290, 297, 400, 421, 460, 477, 478, 479, 512]
        ```
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


def build_multicodec_tables(multicodecs: Iterable[Multicodec], *,
                            allow_private_use: bool = False) -> Tuple[Dict[int, Multicodec], Dict[str, Multicodec]]:
    """
        Creates code->multicodec and name->multicodec mappings from a finite iterable of multicodecs,
        returning the mappings.
        The keyword argument `allow_private_use` (default: `False`) can be used to allow multicodec entries
        with private use codes in `range(0x300000, 0x400000)`: if set to `False`, a `ValueError` is raised
        if one such private use code is encountered.

        Raises `ValueError` if the same multicodec code is encountered multiple times, unless exactly one
        of the multicodecs has permanent status (in which case that codec is the one inserted in the table).
        Raises `ValueError` if the same name is encountered multiple times.

        Example usage:

        ```py
            code_table, name_table = build_multicodec_tables(multicodecs)
        ```
    """
    # validate(multicodecs, Iterable[Multicodec]) # TODO: not yet properly supported by typing-validation
    validate(allow_private_use, bool)
    code_table: Dict[int, Multicodec] = {}
    name_table: Dict[str, Multicodec] = {}
    overwritten_draft_codes: Set[int] = set()
    for m in multicodecs:
        if not allow_private_use and m.is_private_use:
            raise ValueError(f"Private use multicodec not allowed: {m}")
        if m.code in code_table:
            if code_table[m.code].status == "permanent":
                if m.status == "draft":
                    # this draft code has been superseded by a permanent one, skip it
                    continue
                raise ValueError(f"Multicodec code {m.hexcode} appears multiple times in table.")
            if m.status != "permanent":
                # overwriting draft code with another draft code: dodgy, need to check at the end
                overwritten_draft_codes.add(m.code)
        code_table[m.code] = m
        if m.name in name_table:
            raise ValueError(f"Multicodec name {m.name} appears multiple times in table.")
        name_table[m.name] = m
    for code in overwritten_draft_codes:
        m = code_table[code]
        if m.status != "permanent":
            raise ValueError(f"Code {m.code} appears multiple times in table, "
                              "but none of the associated multicodecs is permanent.")
    return code_table, name_table

# Create the global code->multicodec and name->multicodec mappings.
# _code_table: Dict[int, Multicodec] = {}
# _name_table: Dict[str, Multicodec] = {}
with importlib_resources.open_text("multiformats.multicodec", "multicodec-table.csv") as csv_table:
    reader = csv.DictReader(csv_table)
    multicodecs = (Multicodec(**{k.strip(): v.strip() for k, v in _row.items()})
                   for _row in reader)
    _code_table, _name_table = build_multicodec_tables(multicodecs)


# additional docs info
__pdoc__ = {
    "build_multicodec_tables": False # exclude from docs
}
