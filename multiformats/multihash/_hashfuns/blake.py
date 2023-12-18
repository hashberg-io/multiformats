"""
    Implementation for the ``blake2`` and ``blake3`` hash functions, using the optional dependency `blake3 <https://github.com/oconnor663/blake3-py>`_.
"""

# pylint: disable = no-member, not-callable

from __future__ import annotations

import hashlib
from typing import Optional

from multiformats.varint import BytesLike
from .utils import Hashfun, validate_hashfun_args

def _hashlib_blake2(version: str, digest_bits: int) -> Hashfun:
    h = getattr(hashlib, f"blake2{version}")
    def hashfun(data: BytesLike, size: Optional[int] = None) -> bytes:
        validate_hashfun_args(data, size, digest_bits//8)
        m: hashlib._Hash = h(digest_size=digest_bits//8)
        m.update(data)
        d = m.digest()
        return d if size is None else d[:size]
    return hashfun

def _jit_register_blake2(m, register) -> bool: # type: ignore
    blake2_version, digest_bits = (m[1], int(m[2]))
    if digest_bits not in range(8, 513 if blake2_version == "b" else 257, 8):
        return False
    if register is not None:
        register(f"blake2{blake2_version}-{digest_bits}", _hashlib_blake2(blake2_version, digest_bits), digest_bits//8)
    return True

def _blake3() -> Hashfun:
    try:
        from blake3 import blake3 # pylint: disable = import-outside-toplevel
    except ImportError as e:
        raise ImportError("Module 'blake3' must be installed to use 'blake3' hash function. Consider running 'pip install blake3'.") from e
    def hashfun(data: BytesLike, size: Optional[int] = None) -> bytes:
        validate_hashfun_args(data, size, None, size_required=True, name="blake3")
        assert size is not None
        m = blake3()
        m.update(data)
        d: bytes = m.digest(size)
        return d
    return hashfun

def _jit_register_blake3(m, register) -> bool: # type: ignore
    if register is not None:
        register("blake3", _blake3(), None)
    return True
