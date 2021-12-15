"""
    Implementation of the [unsigned-varint spec](https://github.com/multiformats/unsigned-varint).

    Functionality is provided by the `encode` and `decode` functions, converting between non-negative
    `int` values and the corresponding varint `bytes`:

    ```py
    >>> from multiformats import varint
    >>> varint.encode(128)
    b'\\x80\\x01'
    >>> varint.decode(b'\\x80\\x01')
    128
    ```
"""

from io import BufferedIOBase
from typing import cast, List, overload, Tuple, Union, TypeVar
from typing_extensions import Final
from typing_validation import validate

_max_num_bytes: int = 9

BytesLike = Union[bytes, bytearray, memoryview]
byteslike: Final = (bytes, bytearray, memoryview)

def encode(x: int) -> bytes:
    """
        Encodes a non-negative integer as an unsigned varint, returning the encoded bytes.

        Raises `ValueError` if:
        - `x < 0` (varints encode unsigned integers)
        - `x >= 2**63` (from specs, varints are limited to 9 bytes)

        Example usage:

        ```py
        >>> from multiformats import varint
        >>> varint.encode(128)
        b'\\x80\\x01'
        ```
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

def decode(varint: Union[BytesLike, BufferedIOBase]) -> int:
    """
        Decodes an unsigned varint from a `bytes` object or a buffered binary stream.
        If a stream is passed, only the bytes encoding the varint are read from it.
        If a `bytes`-like object is passed, the varint encoding must use all bytes.

        Raises `ValueError` if:

        - `varint` contains no bytes (from specs, the number 0 is encoded as 0b0000_0000)
        - the 9th byte of `varint` is a continuation byte (from specs, no number >= 2**63 is allowed)
        - the last byte of `varint` is a continuation byte (invalid format)
        - the decoded integer could be encoded in fewer bytes than were read (from specs, encoding must be minimal)
        - `varint` is a `bytes`-like object and the number of bytes used by the encoding is fewer than its length

        The last point is a designed choice aimed to reduce errors when decoding fixed-length bytestrings (rather than streams).
        If this behaviour is undesirable, consider using `decode_head` instead.

        Example usage with bytes:

        ```py
        >>> from multiformats import varint
        >>> varint.decode(b'\\x80\\x01')
        128
        ```

        Example usage with streams, for the (typical) situation where the varint is only part of the data:

        ```py
        >>> from io import BytesIO
        >>> stream = BytesIO(b"\\x80\\x01\\x12\\xff\\x01")
        >>> varint.decode(stream)
        128
        >>> stream.read() # what's left in the stream
        b'\\x12\\xff\\x01'
        ```

    """
    x, num_bytes_read, _ = decode_raw(varint)
    if isinstance(varint, byteslike) and len(varint) > num_bytes_read:
        raise ValueError("A bytes-like object was passed, but not all bytes were used by the encoding.")
    return x

def _no_next_byte_error(num_bytes_read: int) -> ValueError:
    if num_bytes_read == 0:
        return ValueError("Varints must be at least 1 byte long.")
    return ValueError(f"Byte #{num_bytes_read-1} was a continuation byte, but byte #{num_bytes_read} not available.")

_BufferedIOT = TypeVar("_BufferedIOT", bound=BufferedIOBase)

@overload
def decode_raw(varint: BytesLike) -> Tuple[int, int, memoryview]:
    ...

@overload
def decode_raw(varint: _BufferedIOT) -> Tuple[int, int, _BufferedIOT]:
    ...

def decode_raw(varint: Union[BytesLike, BufferedIOBase]) -> Tuple[int, int, Union[memoryview, BufferedIOBase]]:
    """
        Specialised version of `decode` for partial decoding, returning a pair `(x, n)` of
        the decoded varint `x` and the number `n` of bytes read from the start and/or consumed from the stream.
        Unlike `decode`, doesn't raise `ValueError` if not all bytes were read in the process.

        Example usage with bytes:

        ```py
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
        ```

        Example usage with streams, for the (typical) situation where the varint is only part of the data:

        ```py
        >>> from io import BytesIO
        >>> stream = BytesIO(b"\\x80\\x01\\x12\\xff\\x01")
        >>> x, n = varint.decode_head(stream) # same as decode, but additionally returns number of bytes read
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
        ```

    """
    if isinstance(varint, BufferedIOBase):
        stream_mode = True
        validate(varint, BufferedIOBase)
    else:
        stream_mode = False
        validate(varint, BytesLike)
    expect_next = True
    num_bytes_read = 0
    x = 0
    while expect_next:
        if stream_mode:
            _next_byte: bytes = cast(BufferedIOBase, varint).read(1)
            if len(_next_byte) == 0:
                raise _no_next_byte_error(num_bytes_read)
            next_byte: int = _next_byte[0]
        else:
            if num_bytes_read >= len(cast(BytesLike, varint)):
                raise _no_next_byte_error(num_bytes_read)
            next_byte = cast(BytesLike, varint)[num_bytes_read]
        x += (next_byte & 0b0111_1111) << (7 * num_bytes_read)
        expect_next = (next_byte >> 7) == 0b1
        num_bytes_read += 1
        if expect_next and num_bytes_read >= _max_num_bytes:
            raise ValueError(f"Varints must be at most {_max_num_bytes} bytes long.")
    if num_bytes_read > 1 and x < 2**(7*(num_bytes_read-1)):
        raise ValueError(f"Number {x} was not minimally encoded (as a {num_bytes_read} bytes varint).")
    if stream_mode:
        return x, num_bytes_read, cast(BufferedIOBase, varint)
    return x, num_bytes_read, memoryview(cast(BytesLike, varint))[num_bytes_read:]
