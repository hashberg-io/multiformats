"""
    Implementation for the ``sha2-256-trunc254-padded`` hash function,
    using `hashlib <https://docs.python.org/3/library/hashlib.html>`_.

    Future support planned for the ``poseidon-bls12_381-a2-fc1`` hash functions,
    possibly using `poseidon-hash <https://github.com/ingonyama-zk/poseidon-hash>`_.
    Additional references on the Poseidon hash function:

    - https://www.poseidon-hash.info/
    - https://github.com/filecoin-project/neptune
"""

from __future__ import annotations

import hashlib
from hashlib import sha256
from typing import Optional

from multiformats.varint import BytesLike
from .utils import validate_hashfun_args

def _sha_256_trunc254_padded(data: BytesLike, size: Optional[int] = None) -> bytes:
    validate_hashfun_args(data, size, 32)
    m: hashlib._Hash = sha256() # pylint: disable = no-member
    m.update(data)
    d = m.digest()
    d = d[:-1]+bytes([d[-1]&0x00111111])
    return d if size is None else d[:size]

def _jit_register_sha_256_trunc254_padded(m, register) -> bool: # type: ignore
    if register is not None:
        register("sha2-256-trunc254-padded", _sha_256_trunc254_padded, 32) # 32B = 256 bits
    return True
