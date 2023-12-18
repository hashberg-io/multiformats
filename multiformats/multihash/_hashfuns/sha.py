"""
    Implementation for the ``sha`` and ``shake`` hash functions,
    using `hashlib <https://docs.python.org/3/library/hashlib.html>`_ and `pycryptodomex <https://github.com/Legrandin/pycryptodome/>`_.
"""

from __future__ import annotations

import hashlib
from typing import Optional

from multiformats.varint import BytesLike
from .utils import Hashfun, validate_hashfun_args

def _sha(version: int, digest_bits: int) -> Hashfun:
    name = ("sha1", f"sha{digest_bits}", f"sha3_{digest_bits}")[version-1]
    h = getattr(hashlib, name)
    def hashfun(data: BytesLike, size: Optional[int] = None) -> bytes:
        validate_hashfun_args(data, size, digest_bits//8)
        m: hashlib._Hash = h() # pylint: disable = no-member
        m.update(data)
        d = m.digest()
        return d if size is None else d[:size]
    return hashfun

def _jit_register_sha1(m, register) -> bool: # type: ignore
    if register is not None:
        register("sha1", _sha(1, 160), 20) # 20B = 160 bits
    return True

def _shake(digest_bits: int) -> Hashfun:
    assert digest_bits in (256, 512)
    h = getattr(hashlib, f"shake_{digest_bits//2}")
    def hashfun(data: BytesLike, size: Optional[int] = None) -> bytes:
        validate_hashfun_args(data, size, digest_bits//8)
        m: hashlib._Hash = h() # pylint: disable = no-member
        m.update(data)
        d = m.digest(digest_bits//8) # type: ignore
        return d if size is None else d[:size]
    return hashfun

def _jit_register_sha23ke(m, register) -> bool: # type: ignore
    if m[1] == "ke":
        digest_bits = 2*int(m[2])
        if register is not None:
            register(f"shake-{digest_bits//2}", _shake(digest_bits), digest_bits//8)
        return True
    sha_version, digest_bits = (int(m[1]), int(m[2]))
    if register is not None:
        register(f"sha{sha_version}-{digest_bits}", _sha(sha_version, digest_bits), digest_bits//8)
    return True

def _sha2_512(digest_bits: int) -> Hashfun:
    assert digest_bits in (224, 256)
    try:
        from Cryptodome.Hash import SHA512 # pylint: disable = import-outside-toplevel
    except ImportError as e:
        raise ImportError("Module 'Cryptodome' must be installed to use the 'sha2-256' hash functions. "
                          "Consider running 'pip install pycryptodomex'.") from e
    def hashfun(data: BytesLike, size: Optional[int] = None) -> bytes:
        validate_hashfun_args(data, size, digest_bits//8)
        m = SHA512.new(truncate=str(digest_bits))
        m.update(data)
        d = m.digest()
        return d if size is None else d[:size]
    return hashfun

def _jit_register_sha2_512(m, register) -> bool: # type: ignore
    digest_bits = int(m[1])
    if register is not None:
        register(f"sha2-512-{digest_bits}", _sha2_512(digest_bits), digest_bits//8)
    return True

def _dbl_sha23(version: int, digest_bits: int) -> Hashfun:
    name = ("sha1", f"sha{digest_bits}", f"sha3_{digest_bits}")[version-1]
    h = getattr(hashlib, name)
    def hashfun(data: BytesLike, size: Optional[int] = None) -> bytes:
        validate_hashfun_args(data, size, digest_bits//8)
        m: hashlib._Hash = h() # pylint: disable = no-member
        m.update(data)
        d = m.digest()
        return d if size is None else d[:size]
    return hashfun

def _jit_register_dbl_sha23(m, register) -> bool: # type: ignore
    sha_version, digest_bits = (int(m[1]), int(m[2]))
    if register is not None:
        register(f"sha{sha_version}-{digest_bits}", _dbl_sha23(sha_version, digest_bits), digest_bits//8)
    return True
