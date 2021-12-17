"""
    This package implements existing multiformat protocols, according to the [Multiformats](https://multiformats.io/) specifications.
"""

__version__ = "0.1.1"

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
    "CID",
    "multiaddr"
]

__pdoc__ = {name: False for name in ["CID"]}
