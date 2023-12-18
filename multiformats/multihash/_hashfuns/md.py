"""
    Implementation for the ``md5`` and ``ripemd`` hash functions,
    using `hashlib <https://docs.python.org/3/library/hashlib.html>`_ and `pycryptodomex <https://github.com/Legrandin/pycryptodome/>`_.
"""

from __future__ import annotations

import hashlib
from typing import Optional

from multiformats.varint import BytesLike
from .utils import Hashfun, validate_hashfun_args

def _md5(data: BytesLike, size: Optional[int] = None) -> bytes:
    validate_hashfun_args(data, size, 16)
    m: hashlib._Hash = hashlib.md5() # pylint: disable = no-member
    m.update(data)
    d = m.digest()
    return d if size is None else d[:size]

def _jit_register_md5(m, register) -> bool: # type: ignore
    if register is not None:
        register("md5", _md5, 16)
    return True

def _ripemd(digest_bits: int) -> Hashfun:
    assert digest_bits == 160, "Only 'ripemd-160' is currently supported."
    try:
        from Cryptodome.Hash import RIPEMD160 # pylint: disable = import-outside-toplevel
    except ImportError as e:
        raise ImportError("Module 'Cryptodome' must be installed to use the 'ripemd-160' hash function. Consider running 'pip install pycryptodomex'.") from e
    def hashfun(data: BytesLike, size: Optional[int] = None) -> bytes:
        validate_hashfun_args(data, size, digest_bits//8)
        m = RIPEMD160.new()
        m.update(data)
        d = m.digest()
        return d if size is None else d[:size]
    return hashfun

def _jit_register_ripemd(m, register) -> bool: # type: ignore
    digest_bits = int(m[1])
    if register is not None:
        register(f"ripemd-{digest_bits}", _ripemd(digest_bits), digest_bits//8)
    return True
