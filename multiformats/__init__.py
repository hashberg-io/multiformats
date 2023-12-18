"""
    Implementation of multiformat protocols, according to the `Multiformats <https://multiformats.io/>`_ specifications.

    Suggested usage:

    >>> from multiformats import *

    The above will import the following names:

    .. code-block:: python

        varint, multicodec, multibase, multihash, multiaddr, CID

    The first five are modules implementing homonymous specifications,
    while :class:`~multiformats.cid.CID` is a class for Content IDentifiers.
"""

from __future__ import annotations

__version__ = "0.3.1"

from . import varint
from . import multicodec
from . import multibase
from . import multihash
from .cid import CID
from . import multiaddr

__all__ = [
    "varint",
    "multicodec",
    "multibase",
    "multihash",
    "multiaddr",
    "CID",
]
