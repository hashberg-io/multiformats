"""
    Implementation of the [unsigned-varint spec](https://github.com/multiformats/unsigned-varint)
"""

from io import BufferedIOBase, BytesIO
from typing import List, Union

_max_num_bytes: int = 9

def encode(x: int) -> bytes:
    """
        Encodes a non-negative integer as an unsigned varint, returning the encoded bytes.

        Raises `ValueError` if:
        - `x < 0` (varints encode unsigned integers)
        - `x >= 2**63` (from specs, varints are limited to 9 bytes)
    """
    if x < 0:
        raise ValueError("Integer is negative.")
    varint_bytelist: List[int] = []
    while True:
        next_byte = x & 0b0111_1111
        x >>= 7
        if x > 0:
            varint_bytelist.append(next_byte | 0b1000_0000)
        else:
            varint_bytelist.append(next_byte)
            break
        if len(varint_bytelist) >= _max_num_bytes:
            raise ValueError(f"Varints must be at most {_max_num_bytes} bytes long.")
    return bytes(varint_bytelist)


def decode(varint: Union[bytes, bytearray, BufferedIOBase]) -> int:
    """
        Decodes an unsigned varint from a `bytes` object or a buffered binary stream.
        If a stream is passed, only the bytes encoding the varint are read from it.
        If a `bytes` or `bytearray` object is passed, the varint encoding must use all bytes.

        Raises `ValueError` if:

        - `varint` contains no bytes (from specs, the number 0 is encoded as 0b0000_0000)
        - the 9th byte of `varint` is a continuation byte (from specs, no number >= 2**63 is allowed)
        - the last byte of `varint` is a continuation byte (invalid format)
        - the decoded integer could be encoded in fewer bytes than were read (from specs, encoding must be minimal)
        - `varint` is a `bytes` or `bytearray` object and the number of bytes used by the encoding is fewer than its length
    """
    stream = BytesIO(varint) if isinstance(varint, (bytes, bytearray)) else varint
    expect_next = True
    num_bytes_read = 0
    x = 0
    while expect_next:
        _next_byte: bytes = stream.read(1)
        if len(_next_byte) == 0:
            if num_bytes_read == 0:
                raise ValueError("Varints must be at least 1 byte long.")
            raise ValueError(f"Byte #{num_bytes_read-1} was a continuation byte, but byte #{num_bytes_read} not available.")
        next_byte: int = _next_byte[0]
        x += (next_byte & 0b0111_1111) << (7 * num_bytes_read)
        expect_next = (next_byte >> 7) == 0b1
        num_bytes_read += 1
        if expect_next and num_bytes_read >= _max_num_bytes:
            raise ValueError(f"Varints must be at most {_max_num_bytes} bytes long.")
    if isinstance(varint, (bytes, bytearray)) and len(varint) > num_bytes_read:
        raise ValueError("A bytes or bytearray object was passed, but not all bytes were used by the encoding.")
    if num_bytes_read > 1 and x < 2**(7*(num_bytes_read-1)):
        raise ValueError(f"Number {x} was not minimally encoded (as a {num_bytes_read} bytes varint).")
    return x
