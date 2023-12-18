"""
    Implementation for the ``kangarootwelve`` hash function, using `pycryptodomex <https://github.com/Legrandin/pycryptodome/>`_.
"""

from __future__ import annotations

from typing import Optional

from multiformats.varint import BytesLike
from .utils import Hashfun, validate_hashfun_args

def _kangarootwelve() -> Hashfun:
    try:
        from Cryptodome.Hash import KangarooTwelve # pylint: disable = import-outside-toplevel
    except ImportError as e:
        raise ImportError("Module 'Cryptodome' must be installed to use the 'kangarootwelve' hash function. "
                          "Consider running 'pip install pycryptodomex'.") from e
    def hashfun(data: BytesLike, size: Optional[int] = None) -> bytes:
        validate_hashfun_args(data, size, None, size_required=True, name="kangarootwelve")
        assert size is not None
        m = KangarooTwelve.new()
        m.update(data)
        return m.read(size)
    return hashfun

def _jit_register_kangarootwelve(m, register) -> bool: # type: ignore
    if register is not None:
        register("kangarootwelve", _kangarootwelve(), None)
    return True
