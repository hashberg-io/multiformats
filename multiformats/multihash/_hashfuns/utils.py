"""
    Utilities for hash function implementation.
"""

from __future__ import annotations

from typing import Optional
from typing_extensions import Literal, Protocol, runtime_checkable
from typing_validation import validate
from multiformats.varint import BytesLike
from multiformats.multihash.err import MultihashValueError

@runtime_checkable
class Hashfun(Protocol):
    """
        Protocol for raw hash functions.

        .. code-block:: python

            @runtime_checkable
            class Hashfun(Protocol):
                def __call__(self, data: BytesLike, size: Optional[int] = None) -> bytes:
                    ...

    """

    def __call__(self, data: BytesLike, size: Optional[int] = None) -> bytes:
        ...

def validate_hashfun_args(data: BytesLike,
                          size: Optional[int],
                          max_digest_size: Optional[int],
                          *,
                          size_required: bool = False,
                          name: str = "") -> None:
    """
        Utility function to validate the arguments passed to hash functions.
    """
    validate(data, BytesLike)
    validate(size, Optional[int])
    if size is not None and size < 0:
        raise MultihashValueError("If specified, digest size must be non-negative integer.")
    if size is not None and max_digest_size is not None and size > max_digest_size:
        raise MultihashValueError("If specified, digest size must not exceed maximum digest size for hash function.")
    if size_required and size is None:
        raise MultihashValueError(f"Digest size is mandatory for hash function{' '+name if name else ''}.")

def repeat_hashfun(hashfun: Hashfun,
                   repeat: int = 1,
                   truncate: Literal["end", "always"] = "end") -> Hashfun:
    """
        Utility function for repeated hashing.
    """
    validate(hashfun, Hashfun)
    validate(repeat, int)
    validate(truncate, Literal["end", "always"])
    if repeat <= 0:
        raise MultihashValueError("Argument 'repeat' must be positive integer.")
    if repeat == 1:
        return hashfun
    if truncate == "always":
        def repeated_hashfun(data: BytesLike, size: Optional[int]=None) -> bytes:
            for _ in range(repeat):
                data = hashfun(data, size)
            return data
    else:
        def repeated_hashfun(data: BytesLike, size: Optional[int]=None) -> bytes:
            for _ in range(repeat-1):
                data = hashfun(data, None)
            data = hashfun(data, size)
            return data
    return repeated_hashfun
