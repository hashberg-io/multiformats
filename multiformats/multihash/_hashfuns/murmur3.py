"""
    Implementation for the ``murmur3`` hash functions, using the optional dependency `mmh3 <https://github.com/hajimes/mmh3>`_.
"""

from __future__ import annotations

from typing import Optional

from multiformats.varint import BytesLike
from .utils import Hashfun, validate_hashfun_args

def _murmur3(version: str, digest_bits: int) -> Hashfun:
    try:
        import mmh3 # pylint: disable = import-outside-toplevel
    except ImportError as e:
        raise ImportError("Module 'mmh3' must be installed to use 'murmur3' hash functions. Consider running 'pip install mmh3'.") from e
    if version == "32":
        def hashfun(data: BytesLike, size: Optional[int] = None) -> bytes:
            validate_hashfun_args(data, size, 4)
            if not isinstance(data, bytes):
                data = bytes(data)
            d: bytes = mmh3.hash(data, signed=False).to_bytes(4, byteorder="big") # pylint: disable = c-extension-no-member
            return d if size is None else d[:size]
    elif digest_bits == 128: # version == "x64"
        def hashfun(data: BytesLike, size: Optional[int] = None) -> bytes:
            validate_hashfun_args(data, size, 16)
            if not isinstance(data, bytes):
                data = bytes(data)
            d: bytes = mmh3.hash128(data, signed=False).to_bytes(16, byteorder="big") # pylint: disable = c-extension-no-member
            return d if size is None else d[:size]
    else: # version == "x64"
        def hashfun(data: BytesLike, size: Optional[int] = None) -> bytes:
            validate_hashfun_args(data, size, 8)
            if not isinstance(data, bytes):
                data = bytes(data)
            d: bytes = mmh3.hash128(data, signed=False).to_bytes(16, byteorder="big") # pylint: disable = c-extension-no-member
            return d[:8] if size is None else d[:size]
    return hashfun

def _jit_register_murmur3(m, register) -> bool: # type: ignore
    if m[1] == "32":
        if register is not None:
            register("murmur3-32", _murmur3("32", 32), 32//8)
        return True
    # version == "x64"
    assert m[2] == "x64"
    digest_bits = int(m[3])
    if register is not None:
        register(f"murmur3-x64-{digest_bits}", _murmur3("x64", digest_bits), digest_bits//8)
    return True
