"""
    Implementation for the ``keccak`` hash functions, using the optional dependency `pycryptodomex <https://github.com/Legrandin/pycryptodome/>`_.
"""

from __future__ import annotations

from typing import Optional

from multiformats.varint import BytesLike
from .utils import Hashfun, validate_hashfun_args

def _keccak(digest_bits: int) -> Hashfun:
    try:
        from Cryptodome.Hash import keccak  # pylint: disable = import-outside-toplevel
    except ImportError as e:
        raise ImportError("Module 'pycryptodome' must be installed to use 'keccak' hash functions. Consider running 'pip install pycryptodome'.") from e

    def hashfun(data: BytesLike, size: Optional[int] = None) -> bytes:
        validate_hashfun_args(data, size, digest_bits//8)
        m = keccak.new(digest_bits=digest_bits)
        m.update(data)
        d = m.digest()
        return d if size is None else d[:size]
    return hashfun

def _jit_register_keccak(m, register) -> bool: # type: ignore
    digest_bits = int(m[1])
    if register is not None:
        register(f"keccak-{digest_bits}", _keccak(digest_bits), digest_bits//8)
    return True
