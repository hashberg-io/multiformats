"""
    Implementation for the ``skein`` hash functions, using the optional dependency `pyskein <https://pythonhosted.org/pyskein/>`_.
"""

from __future__ import annotations

import hashlib
from typing import Optional

from multiformats.varint import BytesLike
from .utils import Hashfun, validate_hashfun_args

def _skein(version: int, digest_bits: int) -> Hashfun:
    try:
        import skein # type: ignore # pylint: disable = import-outside-toplevel
    except ImportError as e:
        raise ImportError("Module 'skein' must be installed to use 'skein' hash functions. Consider running 'pip install pyskein'.") from e
    h = getattr(skein, f"skein{version}")
    def hashfun(data: BytesLike, size: Optional[int] = None) -> bytes:
        validate_hashfun_args(data, size, digest_bits//8)
        m: hashlib._Hash = h(digest_bits=digest_bits) # pylint: disable = no-member
        m.update(data)
        d = m.digest()
        return d if size is None else d[:size]
    return hashfun

def _jit_register_skein(m, register) -> bool: # type: ignore
    skein_version, digest_bits = (int(m[1]), int(m[2]))
    if digest_bits not in range(8, skein_version+1, 8):
        return False
    if register is not None:
        register(f"skein{skein_version}-{digest_bits}", _skein(skein_version, digest_bits), digest_bits//8)
    return True
