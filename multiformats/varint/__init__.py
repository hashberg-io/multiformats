"""
    Implementation of the `unsigned-varint spec <https://github.com/multiformats/unsigned-varint>`_.

    Suggested usage:

    >>> from multiformats import varint
"""

from __future__ import annotations

from io import BufferedIOBase
from typing import BinaryIO, cast, List, Optional, overload, Tuple, Union, TypeVar
from typing_extensions import Final
from typing_validation import validate

_max_num_bytes: int = 9

BytesLike = Union[bytes, bytearray, memoryview]
""" Type alias for bytes-like objects. """

byteslike: Final = (bytes, bytearray, memoryview)
""" Tuple of bytes-like objects types (for use with :obj:`isinstance` checks). """

def encode(x: int) -> bytes:
    """
        Encodes a non-negative integer as an unsigned varint, returning the encoded bytes.

        Example usage:

        >>> from multiformats import varint
        >>> varint.encode(128)
        b'\\x80\\x01'

        :param x: the non-negative integer to encode
        :type x: :obj:`int`

        :raises ValueError: if `x < 0` (varints encode unsigned integers)
        :raises ValueError: if `x >= 2**63` (from specs, varints are limited to 9 bytes)
    """
    validate(x, int)
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


def decode(b: Union[BytesLike, BufferedIOBase, BinaryIO]) -> int:
    """
        Decodes an unsigned varint from a bytes-like object or a buffered binary stream.

        - if a stream is passed, only the bytes encoding the varint are read from it
        - if a `bytes`-like object is passed, the varint encoding must use all bytes

        Example usage with bytes:

        >>> from multiformats import varint
        >>> varint.decode(b'\\x80\\x01')
        128

        Example usage with streams, for the (typical) situation where the varint is only part of the data:

        >>> from io import BytesIO
        >>> stream = BytesIO(b"\\x80\\x01\\x12\\xff\\x01")
        >>> varint.decode(stream)
        128
        >>> stream.read() # what's left in the stream
        b'\\x12\\xff\\x01'

        :param b: the bytes-like object or stream from which to decode a varint
        :type b: :obj:`~multiformats.varint.BytesLike`, :obj:`~io.BufferedIOBase` or :obj:`~typing.BinaryIO`

        :raises ValueError: if the input contains no bytes (from specs, the number 0 is encoded as ``0b00000000``)
        :raises ValueError: if the 9th byte of the input is a continuation byte (from specs, no number >= 2**63 is allowed)
        :raises ValueError: if the last byte of the input is a continuation byte (invalid format)
        :raises ValueError: if the decoded integer could be encoded in fewer bytes than were read (from specs, encoding must be minimal)
        :raises ValueError: if the input is a bytes-like object and the number of bytes used by the encoding is fewer than its length

        The last point is a designed choice aimed to reduce errors when decoding fixed-length bytestrings (rather than streams).
        If this behaviour is undesirable, consider using `decode_head` instead.

    """
    x, num_bytes_read, _ = decode_raw(b)
    if isinstance(b, byteslike) and len(b) > num_bytes_read:
        raise ValueError("A bytes-like object was passed, but not all bytes were used by the encoding.")
    return x

def _no_next_byte_error(num_bytes_read: int) -> ValueError:
    if num_bytes_read == 0:
        return ValueError("Varints must be at least 1 byte long.")
    return ValueError(f"Byte #{num_bytes_read-1} was a continuation byte, but byte #{num_bytes_read} not available.")

_BufferedIOT = TypeVar("_BufferedIOT", bound=BufferedIOBase)
_BinaryIOT = TypeVar("_BinaryIOT", bound=BinaryIO)

@overload
def decode_raw(b: BytesLike) -> Tuple[int, int, memoryview]:
    ...

@overload
def decode_raw(b: _BufferedIOT) -> Tuple[int, int, _BufferedIOT]:
    ...

@overload
def decode_raw(b: _BinaryIOT) -> Tuple[int, int, _BinaryIOT]:
    ...

def decode_raw(b: Union[BytesLike, BufferedIOBase, BinaryIO]) -> Tuple[int, int, Union[memoryview, BufferedIOBase, BinaryIO]]:
    """
        Specialised version of :func:`~multiformats.varint.decode` for partial decoding, returning a pair ``(x, n)`` of
        the decoded varint ``x`` and the number ``n`` of bytes read from the start and/or consumed from the stream.
        Unlike :func:`~multiformats.varint.decode`, this function doesn't raise `ValueError` in case not all bytes are read in the process.

        Example usage with bytes:

        >>> bs = b"\\x80\\x01\\x12\\xff\\x01"
        >>> x, n, m = varint.decode_raw(bs)
        >>> x
        128
        >>> n
        2
        # read first 2 bytes: b"\\x80\\x01"
        >>> m
        <memory at 0x000001A6E55DDA00>
        >>> bytes(m)
        b'\\x12\\xff\\x01'
        # memoryview on remaining bytes
        # note: bytes(m) did not consume the bytes

        Example usage with streams, for the (typical) situation where the varint is only part of the data:

        >>> from io import BytesIO
        >>> stream = BytesIO(b"\\x80\\x01\\x12\\xff\\x01")
        >>> x, n = varint.decode_head(stream)
        >>> x
        128
        >>> n
        2
        # read first 2 bytes: b"\\x80\\x01"
        >>> m
        <_io.BytesIO object at 0x000001A6E554BBD0>
        >>> m == stream
        True
        # original stream returned, containing remaining bytes
        >>> stream.read()
        b'\\x12\\xff\\x01'
        # 2 bytes were consumed decoding the varint, so 3 bytes were left in the stream
        # note: stream.read() consumed the bytes

        :param b: the bytes-like object or stream from which to decode a varint
        :type b: :obj:`~multiformats.varint.BytesLike`, :obj:`~io.BufferedIOBase` or :obj:`~typing.BinaryIO`

        :raises ValueError: same reasons as :func:`~multiformats.varint.decode`, except for the last (where no error is raised)

    """
    stream_mode: Optional[type]
    if isinstance(b, BufferedIOBase):
        stream_mode = BufferedIOBase
        validate(b, BufferedIOBase)
    elif isinstance(b, BinaryIO):
        stream_mode = BinaryIO
        validate(b, BinaryIO)
    else:
        stream_mode = None
        validate(b, BytesLike)
    expect_next = True
    num_bytes_read = 0
    x = 0
    while expect_next:
        if stream_mode is not None:
            _next_byte: bytes = cast(Union[BufferedIOBase, BinaryIO], b).read(1)
            if len(_next_byte) == 0:
                raise _no_next_byte_error(num_bytes_read)
            next_byte: int = _next_byte[0]
        else:
            if num_bytes_read >= len(cast(BytesLike, b)):
                raise _no_next_byte_error(num_bytes_read)
            next_byte = cast(BytesLike, b)[num_bytes_read]
        x += (next_byte & 0b0111_1111) << (7 * num_bytes_read)
        expect_next = (next_byte >> 7) == 0b1
        num_bytes_read += 1
        if expect_next and num_bytes_read >= _max_num_bytes:
            raise ValueError(f"Varints must be at most {_max_num_bytes} bytes long.")
    if num_bytes_read > 1 and x < 2**(7*(num_bytes_read-1)):
        raise ValueError(f"Number {x} was not minimally encoded (as a {num_bytes_read} bytes varint).")
    if stream_mode is not None:
        return x, num_bytes_read, cast(Union[BufferedIOBase, BinaryIO], b)
    return x, num_bytes_read, memoryview(cast(BytesLike, b))[num_bytes_read:]
