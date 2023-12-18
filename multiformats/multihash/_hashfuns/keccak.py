"""
    Implementation for the ``keccak`` hash functions, using the optional dependency `pysha3 <https://github.com/tiran/pysha3>`_.
"""

from __future__ import annotations

import hashlib
from typing import Optional

from multiformats.varint import BytesLike
from .utils import Hashfun, validate_hashfun_args

def _keccak(digest_bits: int) -> Hashfun:
    # FIXME: pysha3 is not longer available
    raise NotImplementedError("keccak hashes are not currently supported.")
    # pylint: disable = unreachable
    try:
        import sha3 # type: ignore # pylint: disable = import-outside-toplevel
    except ImportError as e:
        raise ImportError("Module 'sha3' must be installed to use 'keccak' hash functions. Consider running 'pip install pysha3'.") from e
    h = getattr(sha3, f"keccak_{digest_bits}")
    def hashfun(data: BytesLike, size: Optional[int] = None) -> bytes:
        validate_hashfun_args(data, size, digest_bits//8)
        m: hashlib._Hash = h() # pylint: disable = no-member
        m.update(data)
        d = m.digest()
        return d if size is None else d[:size]
    return hashfun

def _jit_register_keccak(m, register) -> bool: # type: ignore
    # FIXME: pysha3 is not longer available
    raise NotImplementedError("keccak hashes are not currently supported.")
    # pylint: disable = unreachable
    digest_bits = int(m[1])
    if register is not None:
        register(f"keccak-{digest_bits}", _keccak(digest_bits), digest_bits//8)
    return True
