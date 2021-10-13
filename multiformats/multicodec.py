"""
    Implementation of the [multicodec spec](https://github.com/multiformats/multicodec).

    The `Multicodec` dataclass provides a container for multicodec data:

    ```py
    >>> from multiformats import multicodec
    >>> from multicodec import Multicodec
    >>> Multicodec("identity", "multihash", 0x00, "permanent", "raw binary")
    Multicodec(name='identity', tag='multihash', code=0,
               status='permanent', description='raw binary')
    ```

    The `exists` and `get` functions can be used to check whether a multicodec with given name or code is known, and if so to get the corresponding object:

    ```py
    >>> multicodec.exists("identity")
    True
    >>> multicodec.exists(0x00)
    True
    >>> multicodec.get("identity")
    Multicodec(name='identity', tag='multihash', code=0,
               status='permanent', description='raw binary')
    >>> multicodec.get(0x00)
    Multicodec(name='identity', tag='multihash', code=0,
               status='permanent', description='raw binary')
    ```

    The `table` function can be used to iterate through known multicodecs, optionally restrictiong to one or more tags and/or statuses:

    ```py
    >>> len(list(multicodec.table()))
    482
    >>> selected = multicodec.table(tag=["ipld", "multiaddr"], status="permanent")
    >>> [m.code for m in selected]
    [1, 4, 6, 41, 53, 54, 55, 56, 85, 112, 113, 114, 120,
     144, 145, 146, 147, 148, 149, 150, 151, 152, 176, 177,
     178, 192, 193, 290, 297, 400, 421, 460, 477, 478, 479]
    ```

    The `register` function can be used to register a custom multicodec as known:

    ```py
    >>> m = Multicodec("my-multicodec", "my-tag", 0x300001, "draft", "...")
    >>> multicodec.register(m)
    >>> multicodec.exists(0x300001)
    True
    >>> multicodec.get(0x300001).name
    'my-multicodec'
    >>> multicodec.get(0x300001).is_private_use
    True # code in range(0x300000, 0x400000)
    ```

    The `unregister` function can be used to unregister an existing multicodec (by name or code):

    ```py
    >>> multicodec.unregister(0x300001)
    >>> multicodec.exists(0x300001)
    False
    ```
"""

import csv
from dataclasses import dataclass
from importlib import resources
import re
from typing import Collection, Dict, Iterable, Iterator, Mapping, Optional, Set, Tuple, Union


@dataclass(frozen=True)
class Multicodec:
    """ Dataclass for a multicodec. """

    name: str
    """ Multicodec name. """

    tag: str
    """ Multicodec tag. """

    code: int
    """ Multicodec code (as a non-negative integer). """

    status: str
    """ Multicodec status (currently only 'draft' or 'permanent')."""

    description: str
    """ Multicodec description. """

    def __post_init__(self):
        if not re.match(r"^[a-z][a-z0-9_-]+$", self.name):
            raise ValueError(f"Invalid multicodec name {repr(self.name)}")
        if self.status not in ("draft", "permanent"):
            raise ValueError(f"Invalid multicodec status {repr(self.status)}.")
        if self.code < 0:
            raise ValueError(f"Invalid multicodec code {self.code}.")

    @property
    def hexcode(self) -> str:
        """
            Multicodec code as a hex string (with hex digits zero-padded to even length).
        """
        code = hex(self.code)
        if len(code) % 2 != 0:
            code = "0x0"+code[2:]
        return code

    @property
    def is_private_use(self) -> bool:
        """
            Whether this multicodec code is reserved for private use,
            i.e. whether it is in `range(0x300000, 0x400000)`.
        """
        return self.code in range(0x300000, 0x400000)

    def to_json(self) -> Mapping[str, str]:
        """
            Returns a JSON dictionary representation of this multicodec object,
            compatible with the one from the table.csv found in the
            [multicodec spec](https://github.com/multiformats/multicodec)
        """
        return {
            "name": self.name,
            "tag": self.tag,
            "code": self.hexcode,
            "status": self.status,
            "description": self.description
        }

    @staticmethod
    def from_json(multicodec: Mapping[str, str]) -> "Multicodec":
        """
            Decodes a `Multicodec` object from a JSON dictionary representation
            compatible with the one from the table.csv found in the
            [multicodec spec](https://github.com/multiformats/multicodec)
        """
        return Multicodec(
            multicodec["name"],
            multicodec["tag"],
            int(multicodec["code"][2:], base=16),
            multicodec["status"],
            multicodec["description"]
        )

    def __str__(self) -> str:
        return str(self.to_json())


def get(name_or_code: Union[str, int]) -> Multicodec:
    """
        Gets the multicodec with given name (if a string is passed) or code (if an int is passed).
        Raises `KeyError` if no such multicodec exists.
    """
    if isinstance(name_or_code, str):
        name: str = name_or_code
        if name not in _name_table:
            raise KeyError(f"No multicodec named {repr(name)}.")
        return _name_table[name]
    code: int = name_or_code
    if code not in _code_table:
        raise KeyError(f"No multicodec with code {repr(code)}.")
    return _code_table[code]


def exists(name_or_code: Union[str, int]) -> bool:
    """
        Checks whether there is a multicodec with the given name (if a string is passed)
        or code (if an int is passed).
    """
    if isinstance(name_or_code, str):
        name: str = name_or_code
        return name in _name_table
    code: int = name_or_code
    return code in _code_table


def register(m: Multicodec, overwrite: bool = False) -> None:
    """
        Registers a given multicodec. The optional keyword argument `overwrite` (default: `False`)
        can be used to overwrite a multicodec with existing code.
    """
    if not overwrite and m.code in _code_table:
        raise ValueError(f"Multicodec with code {repr(m.code)} already exists: {_code_table[m.code]}")
    if m.name in _name_table:
        raise ValueError(f"Multicodec with name {repr(m.name)} already exists: {_name_table[m.name]}")
    _code_table[m.code] = m
    _name_table[m.name] = m


def unregister(name_or_code: Union[str, int]) -> None:
    """
        Unregisters the multicodec with given name (if a string is passed) or code (if an int is passed).
        Raises `KeyError` if no such multicodec exists.
    """
    m = get(name_or_code)
    del _code_table[m.code]
    del _name_table[m.name]


def table(tag: Union[None, str, Collection[str]] = None, status: Union[None, str, Collection[str]] = None) -> Iterator[Multicodec]:
    """
        Iterates through the registered multicodecs, in order of ascending code.
        The optional keyword arguments `tag` and `status` can be used to restrict the iterator
        to multicodecs with a given `tag` or `status` respectively.
    """
    tags: Optional[Collection[str]]
    if tag is None:
        tags = None
    elif isinstance(tag, str):
        tags = [tag]
    else:
        tags = tag
    statuses: Optional[Collection[str]]
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
        returning the mappings. Use as:

        ```py
            code_table, name_table = build_multicodec_tables(multicodecs)
        ```

        The keyword argument `allow_private_use` (default: `False`) can be used to allow multicodec entries
        with private use codes in `range(0x300000, 0x400000)`.
    """
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
            if m.code != "permanent":
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
with resources.open_text("multiformats", "multicodec-table.csv") as csv_table:
    reader = csv.DictReader(csv_table)
    multicodecs = (Multicodec.from_json({k.strip(): v.strip() for k, v in _row.items()})
                   for _row in reader)
    _code_table, _name_table = build_multicodec_tables(multicodecs)
