"""
    Implementation of the [unsigned-varint spec](https://github.com/multiformats/unsigned-varint)
"""

from typing import List

_max_num_bytes: int = 9

def encode(x: int) -> bytes:
    """
        Encodes a non-negative integer as an unsigned varint.

        Raises `ValueError` if `x < 0` and if `x >= 2**63`, according to the specs.
    """
    if x < 0:
        raise ValueError("The unsigned-varint encoding is for non-negative integers only.")
    orig_x = x
    varint_bytes: List[int] = []
    while True:
        next_byte = x & 0b0111_1111
        x >>= 7
        if x > 0:
            varint_bytes.append(next_byte | 0b1000_0000)
        else:
            varint_bytes.append(next_byte)
            break
        if len(varint_bytes) >= _max_num_bytes:
            raise ValueError(f"The unsigned-varint spec limits varints to {_max_num_bytes} bytes {orig_x, x, varint_bytes}.")
    return bytes(varint_bytes)

def decode(varint: bytes) -> int:
    """
        Decodes an unsigned varint.

        Raises `ValueError` if `len(varint) == 0` and if `len(varint) > 9`, according to the specs.
    """
    if len(varint) == 0:
        raise ValueError("Varints must be at least 1 byte long.")
    if len(varint) > _max_num_bytes:
        raise ValueError(f"Varints must be at most {_max_num_bytes} bytes long.")
    x = 0
    for i, byte_i in enumerate(varint):
        x += (byte_i & 0b0111_1111) << (7 * i)
        cont = byte_i >> 7
        if cont == 0b1 and i == len(varint)-1:
            raise ValueError("Last byte of varint is a continuation byte.")
        if cont == 0b0 and i != len(varint)-1:
            raise ValueError(f"Byte #{i} of varint is not a continuation byte and not the last byte.")
    if len(varint) > 1 and x < 2**(7*(len(varint)-1)):
        raise ValueError(f"Number {x} was not minimally encoded (as a {len(varint)} bytes varint).")
    return x
