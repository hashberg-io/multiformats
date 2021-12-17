"""
    Implementation of the [multihash spec](https://github.com/multiformats/multihash).

    Core functionality is provided by the `digest`, `encode`, `decode` functions,
    or the correspondingly-named methods of the `Multihash` class.
    The `digest` function and `Multihash.digest` method can be used to create a multihash digest directly from data:

    ```py
    >>> data = b"Hello world!"
    >>> digest = multihash.digest(data, "sha2-256")
    >>> digest.hex()
    '1220c0535e4be2b79ffd93291305436bf889314e4a3faec05ecffcbb7df31ad9e51a'
    ```

    ```py
    >>> sha2_256 = multihash.get("sha2-256")
    >>> digest = sha2_256.digest(data)
    >>> digest.hex()
    '1220c0535e4be2b79ffd93291305436bf889314e4a3faec05ecffcbb7df31ad9e51a'
    ```

    By default, the full digest produced by the hash function is used.
    Optionally, a smaller digest size can be specified to produce truncated hashes:

    ```py
    >>> digest = multihash.digest(data, "sha2-256", size=20)
    #        optional truncated hash size, in bytes ^^^^^^^
    >>> multihash_digest.hex()
    '1214c0535e4be2b79ffd93291305436bf889314e4a3f' # 20-bytes truncated hash
    ```

    The `decode` function can be used to extract the raw digest from a multihash digest:

    ```py
    >>> digest.hex()
    '1214c0535e4be2b79ffd93291305436bf889314e4a3f'
    >>> raw_digest = multihash.decode(digest)
    >>> raw_digest.hex()
        'c0535e4be2b79ffd93291305436bf889314e4a3f'
    ```

    The `Multihash.digest` performs the same functionality, but additionally checks
    that the multihash digest is valid for the multihash:

    ```py
    >>> raw_digest = sha2_256.decode(digest)
    >>> raw_digest.hex()
        'c0535e4be2b79ffd93291305436bf889314e4a3f'
    ```

    ```py
    >>> sha1 = multihash.get("sha1")
    >>> (sha2_256.code, sha1.code)
    (18, 17)
    >>> sha1.decode(digest)
    ValueError: Decoded code 18 differs from multihash code 17.
    ```

    The `encode` function and `Multihash.encode` method can be used to encode a raw digest into a multihash digest:

    ```py
    >>> raw_digest.hex()
        'c0535e4be2b79ffd93291305436bf889314e4a3f'
    >>> multihash.encode(raw_digest, "sha2-256").hex()
    '1214c0535e4be2b79ffd93291305436bf889314e4a3f'
    ```

    ```py
    >>> sha2_256.encode(raw_digest).hex()
    '1214c0535e4be2b79ffd93291305436bf889314e4a3f'
    ```

    Note the both multihash code and digest length are encoded as varints
    (see the `multiformats.varint` module) and can span multiple bytes:

    ```py
    >>> skein1024_1024 = multihash.get("skein1024-1024")
    >>> skein1024_1024.codec
    Multicodec(name='skein1024-1024', tag='multihash', code='0xb3e0',
               status='draft', description='')
    >>> skein1024_1024.digest(data).hex()
    'e0e702800192e08f5143...' # 3+2+128 = 133 bytes in total
    #^^^^^^     3-bytes varint for hash function code 0xb3e0
    #      ^^^^ 2-bytes varint for hash digest length 128
    >>> from multiformats import varint
    >>> hex(varint.decode(bytes.fromhex("e0e702")))
    '0xb3e0'
    >>> varint.decode(bytes.fromhex("8001"))
    128
    ```

    Also note that data and digests are all `bytes` objects, represented here as hex strings for clarity:

    ```py
    >>> raw_digest
            b'\\xc0S^K\\xe2\\xb7\\x9f\\xfd\\x93)\\x13\\x05Ck\\xf8\\x891NJ?'
    >>> digest
    b'\\x12\\x14\\xc0S^K\\xe2\\xb7\\x9f\\xfd\\x93)\\x13\\x05Ck\\xf8\\x891NJ?'
    # ^^^^^      0x12 -> multihash multicodec "sha2-256"
    #      ^^^^^ 0x14 -> truncated hash length of 20 bytes
    ```

    The multihash specified by a given multihash digest is accessible using the `from_digest` function:

    ```py
    >>> multihash.from_digest(digest)
    Multihash(codec='sha2-256')
    >>> multihash.from_digest(digest).codec
    Multicodec(name='sha2-256', tag='multihash', code='0x12',
               status='permanent', description='')
    ```

    Additional multihash management functionality is provided by the `exists` and `get` functions,
    which can be used to check whether a multihash multicodec with given name or code is known,
    and if so to get the corresponding object:

    ```py
    >>> multihash.exists("sha1")
    True
    >>> multihash.get("sha1")
    Multihash(codec='sha1')
    >>> multihash.exists(code=0x11)
    True
    >>> multihash.get(code=0x11)
    Multihash(codec='sha1')
    ```

"""

from io import BytesIO, BufferedIOBase
from typing import AbstractSet, Any, cast, ClassVar, Dict, Iterator, Mapping, Optional, overload, Union, Sequence, Tuple, Type, TypeVar
from weakref import WeakValueDictionary
import sys
from typing_extensions import Literal
from typing_validation import validate

from multiformats import multicodec, varint
from multiformats.multicodec import Multicodec
from multiformats.varint import BytesLike

from . import raw
from .raw import Hashfun

class Multihash:
    """
        Container class for a multibase encoding.

        Example usage:

        ```py
        >>> sha2_256 = multihash.get("sha2-256")
        >>> sha2_256
        Multihash(codec='sha2-256')
        ```
    """

    # WeakValueDictionary[str, Multihash]
    _cache: ClassVar[WeakValueDictionary] = WeakValueDictionary() # type: ignore

    _codec: Multicodec

    __slots__ = ("__weakref__", "_codec")

    def __new__(cls, *, codec: Union[str, int, Multicodec]) -> "Multihash":
        # check that the codec exists:
        if isinstance(codec, str):
            codec = multicodec.get(codec)
        elif isinstance(codec, int):
            codec = multicodec.get(code=codec)
        else:
            validate(codec, Multicodec)
            existing_codec = multicodec.get(codec.name)
            if existing_codec != codec:
                raise ValueError(f"Multicodec named {repr(codec.name)} exists, but is not the one given.")
            codec = existing_codec
        # check that the codec is a multihash multicodec:
        if codec.tag != "multihash":
            raise ValueError(f"Multicodec named {repr(codec.name)} exists, but is not a multihash.")
        _cache = Multihash._cache
        if codec.name in _cache:
            # if a multihash instance with this name is already registered
            instance: Multihash = _cache[codec.name]
            if instance.codec == codec:
                # if the codec did not change, return the existing instance
                return instance
            # otherwise remove the existing instance
            del _cache[codec.name]
        # create a fresh instance, register it and return it
        instance = super().__new__(cls)
        instance._codec = codec
        _cache[codec.name] = instance
        return instance

    @property
    def name(self) -> str:
        """
            Multihash multicodec name.

            Example usage:

            ```py
            >>> sha2_256.name
            'sha2-256'
            ```
        """
        return self.codec.name

    @property
    def code(self) -> int:
        """
            Multihash multicodec code.

            Example usage:

            ```py
            >>> sha2_256.code
            18
            # 18 = 0x12
            ```
        """
        return self.codec.code

    @property
    def codec(self) -> Multicodec:
        """
            The multicodec for this multihash.

            Example usage:

            ```py
            >>> sha2_256.codec
            Multicodec(name='sha2-256', tag='multihash', code='0x12',
                       status='permanent', description='')
            ```
        """
        return self._codec

    @property
    def max_digest_size(self) -> Optional[int]:
        """
            The maximum size (in bytes) for raw digests of this multihash,
            or `None` if there is no maximum size.
            Used to sense-check the encoded/decoded raw digests.

            Example usage:

            ```py
            >>> sha2_256.max_digest_size
            32
            # 32 bytes = 256 bits
            ```
        """
        _, max_digest_size = self.implementation
        return max_digest_size

    @property
    def implementation(self) -> Tuple[Hashfun, Optional[int]]:
        """
            Returns the implementation of a multihash multicodec, as a pair:

            ```py
            hash_function, max_digest_size = multihash.implementation("sha2-256")
            ```

            Above, `codec` is the `multiformats.multicodec.Multicodec` object carrying information about the
            multihash multicodec, `hash_function` is the function `bytes->bytes` computing the raw hashes,
            and `max_digest_size` is the max size of the digests produced by `hash_function` (or `None` if
            there is no max size, such as in the case of the 'identity' multihash multicodec).

            Example usage:

            ```py
            >>> sha2_256.implementation
            (<function _hashlib_sha.<locals>.hashfun at 0x0000029396E22280>, 32)
            ```
        """
        hash_function, max_digest_size = raw.get(self.name)
        return hash_function, max_digest_size

    @property
    def is_implemented(self) -> bool:
        """
            Whether this multihash has an implementation (see `implementation`).

            Example usage:

            ```py
            >>> sha2_256.is_implemented
            True
            ```
        """
        return raw.exists(self.name)

    def encode(self, raw_digest: BytesLike) -> bytes:
        """
            Encodes a raw digest into a multihash digest:

            ```
            <raw digest> -> <code><size><raw digest>
            ```

            Example usage:

            ```py
            >>> sha2_256 = multihash.get("sha2-256")
            >>> raw_digest = bytes.fromhex(
            ... "c0535e4be2b79ffd93291305436bf889314e4a3f")
            >>> sha2_256.encode(raw_digest).hex()
            "1214c0535e4be2b79ffd93291305436bf889314e4a3f"
            ```

            See `encode` for more information.
        """
        validate(raw_digest, BytesLike)
        _, max_digest_size = self.implementation
        size = len(raw_digest)
        if max_digest_size is not None and size > max_digest_size:
            raise ValueError(f"Digest size {max_digest_size} is listed for {self.name}, "
                             f"but a digest of larger size {size} was given to be encoded.")
        return varint.encode(self.code)+varint.encode(size)+raw_digest

    def digest(self, data: BytesLike, *, size: Optional[int] = None) -> bytes:
        """
            Computes the raw digest of the given data and encodes it into a multihash digest.
            The optional keyword argument `size` can be used to truncate the
            raw digest to be of the given size (or less) before encoding.

            Example usage:

            ```py
            >>> sha2_256 = multihash.get("sha2-256")
            >>> data = b"Hello world!"
            >>> data.hex()
            "48656c6c6f20776f726c6421"
            >>> sha2_256.digest(data).hex() # full 32-bytes hash
            '1220c0535e4be2b79ffd93291305436bf889314e4a3faec05ecffcbb7df31ad9e51a'
            >>> sha2_256.digest(data, size=20).hex() # truncated hash
            '1214c0535e4be2b79ffd93291305436bf889314e4a3f'
            ```

            See `digest` for more information.
        """
        hf, _ = self.implementation
        raw_digest = hf(data)
        if size is not None:
            raw_digest = raw_digest[:size] # truncate digest
        return varint.encode(self.code)+varint.encode(len(raw_digest))+raw_digest

    def decode(self, digest: Union[BytesLike, BufferedIOBase]) -> bytes:
        """
            Decodes a multihash digest into a hash digest:

            ```
            <code><size><raw digest> -> <raw digest>
            ```

            If `digest` is one of bytes, bytearray or memoryview, the method also checks
            that the actual hash digest size matches the size listed by the multihash digest.

            Example usage:

            ```py
            >>> sha2_256 = multihash.get("sha2-256")
            >>> digest = bytes.fromhex(
            ... "1214c0535e4be2b79ffd93291305436bf889314e4a3f")
            >>> sha2_256.decode(digest).hex()
            'c0535e4be2b79ffd93291305436bf889314e4a3f'
            ```

        """
        code, raw_digest = decode_raw(digest)
        if code != self.code:
            raise ValueError(f"Decoded code {code} differs from multihash code {self.code}.")
        _validate_raw_digest_size(self.name, raw_digest, self.max_digest_size)
        return raw_digest

    def __str__(self) -> str:
        return f"multihash.get({repr(self.name)})"

    def __repr__(self) -> str:
        return f"Multihash(codec={repr(self.name)})"

    @property
    def _as_tuple(self) -> Tuple[Type["Multihash"], Multicodec]:
        return (Multihash, self.codec)

    def __hash__(self) -> int:
        return hash(self._as_tuple)

    def __eq__(self, other: Any) -> bool:
        if self is other:
            return True
        if not isinstance(other, Multihash):
            return NotImplemented
        return self._as_tuple == other._as_tuple


def get(name: Optional[str] = None, *, code: Optional[int] = None) -> Multihash:
    """
        Gets the multihash multicodec with given name or code.
        Raises `KeyError` if no such multihash exists.
        Exactly one of `name` and `code` must be specified.

        Example usage:

        ```py
        >>> multihash.get("sha1")
        Multihash(codec='sha1')
        >>> multihash.get(code=0x11)
        Multihash(codec='sha1')
        ```

    """
    if name is not None and code is not None:
        raise ValueError("Must specify at most one between 'name' and 'code'.")
    if name is not None:
        return Multihash(codec=name)
    if code is not None:
        return Multihash(codec=code)
    raise ValueError("Must specify at least one between 'name' and 'code'.")


def exists(name: Optional[str] = None, *, code: Optional[int] = None) -> bool:
    """
        Checks whether there is a multihash multicodec with the given name or code.
        Exactly one of `name` and `code` must be specified.
        This function returns `False` if a multicodec by given name or code exists,
        but is not tagged 'multihash'.

        Example usage:

        ```py
        >>> multihash.exists("sha1")
        True
        >>> multihash.exists(code=0x11)
        True
        >>> from multiformats import multicodec
        >>> multicodec.get("cidv1")
        Multicodec(name='cidv1', tag='cid', code='0x01',
                   status='permanent', description='CIDv1')
        >>> multihash.exists("cidv1")
        False
        ```

    """
    if not multicodec.exists(name, code=code):
        return False
    multihash = multicodec.get(name, code=code)
    return multihash.tag == "multihash"


def from_digest(multihash_digest: Union[BytesLike, memoryview]) -> Multihash:
    """
        Returns the multihash multicodec for the given digest,
        according to the code specified by its prefix.
        Raises `KeyError` if no multihash exists with that code.

        Example usage:

        ```py
        >>> multihash_digest = bytes.fromhex("140a9a7a8207a57d03e9c524")
        >>> multihash.from_digest(multihash_digest)
        Multihash(codec='sha3-512')
        ```

    """
    code, _, _ = varint.decode_raw(multihash_digest)
    return get(code=code)


def encode(raw_digest: BytesLike, multihash: Union[str, int, Multihash]) -> bytes:
    """
        Encodes a raw digest into a multihash digest using the given multihash:

        ```
        <raw digest> -> <code><size><raw digest>
        ```

        If the multihash is passed by name or code, the `get` function is used to retrieve it.

        Example usage:

        ```py
        >>> multihash.get("sha2-256").codec
        Multicodec(name='sha2-256', tag='multihash', code='0x12',
                   status='permanent', description='')
        >>> raw_digest = bytes.fromhex("c0535e4be2b79ffd93291305436bf889314e4a3f")
        >>> len(raw_digest)
        20
        >>> multihash.encode(raw_digest, "sha2-256").hex()
        "1214c0535e4be2b79ffd93291305436bf889314e4a3f"
        #^^   code 0x12 for multihash multicodec "sha2-256"
        #  ^^ truncated hash length 0x14 = 20 bytes
        ```

        Note that all digests are `bytes` objects, represented here as hex strings for clarity:

        ```raw_digest
        >>> hash_digest
        b'\\xc0S^K\\xe2\\xb7\\x9f\\xfd\\x93)\\x13\\x05Ck\\xf8\\x891NJ?'
        >>> multihash.encode(raw_digest, "sha2-256")
        b'\\x12\\x14\\xc0S^K\\xe2\\xb7\\x9f\\xfd\\x93)\\x13\\x05Ck\\xf8\\x891NJ?'
        # ^^^^     0x12 -> multihash multicodec "sha2-256"
        #     ^^^^ 0x14 -> truncated hash length of 20 bytes
        ```

    """
    if not isinstance(multihash, Multihash):
        multihash = Multihash(codec=multihash)
    return multihash.encode(raw_digest)


def digest(data: BytesLike, multihash: Union[str, int, Multihash], *, size: Optional[int] = None) -> bytes:
    """
        Computes the raw digest of the given data and encodes it into a multihash digest.
        The optional keyword argument `size` can be used to truncate the
        raw digest to be of the given size (or less) before encoding.

        Example usage:

        ```py
        >>> data = b"Hello world!"
        >>> data.hex()
        "48656c6c6f20776f726c6421"
        >>> multihash.digest(data, "sha2-256").hex() # full 32-bytes hash
        '1220c0535e4be2b79ffd93291305436bf889314e4a3faec05ecffcbb7df31ad9e51a'
        >>> multihash.digest(data, "sha2-256", size=20).hex()
        #         optional truncated hash size ^^^^^^^
        '1214c0535e4be2b79ffd93291305436bf889314e4a3f'
        #^^   code 0x12 for multihash multicodec "sha2-256"
        #  ^^ truncated hash length 0x14 = 20 bytes
        ```

        Note both multihash code and digest length are encoded as varints
        (see the `multiformats.varint` module) and can span multiple bytes:

        ```py
        >>> multihash.get("skein1024-1024")
        Multicodec(name='skein1024-1024', tag='multihash', code='0xb3e0',
                   status='draft', description='')
        >>> multihash.digest(data, "skein1024-1024").hex()
        'e0e702800192e08f5143 ... 3+2+128 = 133 bytes in total
        #^^^^^^     3-bytes varint for hash function code 0xb3e0
        #      ^^^^ 2-bytes varint for hash digest length 128
        >>> from multiformats import varint
        >>> hex(varint.decode(bytes.fromhex("e0e702")))
        '0xb3e0'
        >>> varint.decode(bytes.fromhex("8001"))
        128
        ```

    """
    if not isinstance(multihash, Multihash):
        multihash = Multihash(codec=multihash)
    return multihash.digest(data, size=size)


def _validate_raw_digest_size(name: str, raw_digest: bytes, max_digest_size: Optional[int]) -> None:
    if max_digest_size is not None and len(raw_digest) > max_digest_size:
        raise ValueError(f"Multihash {name} has max digest size {max_digest_size}, "
                         f"but a digest of larger size {len(raw_digest)} was decoded instead.")


def decode(digest: Union[BytesLike, BufferedIOBase],
           multihash: Union[None, str, int, Multihash]=None) -> bytes:
    """
        Decodes a multihash digest into a raw digest:

        ```
        <code><size><raw digest> -> <raw digest>
        ```

        If `digest` is one of `bytes`, `bytearray` or `memoryview`, the method also checks
        that the actual raw digest size matches the size listed in the multihash digest.
        If `digest` is a stream (an instance of `BufferedIOBase`, specifically), then the
        number of bytes consumed to produce the raw digest matches the size lised in the multihash digest,
        and no further bytes are consumed from the stream.

        If `multihash` is not `None`, the function additionally enforces that the code from the
        multihash digest matches the code of the multihash codec (calls `Multihash.decode` under the hood to do so).
        Regardless, the function checks that the multihash codec with code specified by the multihash digest exists.

        Example usage:

        ```py
        >>> digest = bytes.fromhex(
        ... "1214c0535e4be2b79ffd93291305436bf889314e4a3f")
        >>> multihash.decode(digest, "sha2-256").hex()
        'c0535e4be2b79ffd93291305436bf889314e4a3f'
        ```
    """
    if multihash is not None:
        if not isinstance(multihash, Multihash):
            multihash = Multihash(codec=multihash)
        return multihash.decode(digest)
    code, raw_digest = decode_raw(digest)
    multihash = Multihash(codec=code)
    _validate_raw_digest_size(multihash.name, raw_digest, multihash.max_digest_size)
    return raw_digest


_BufferedIOT = TypeVar("_BufferedIOT", bound=BufferedIOBase)

@overload
def decode_raw(multihash_digest: BufferedIOBase) -> Tuple[int, bytes]:
    ...

@overload
def decode_raw(multihash_digest: BytesLike) -> Tuple[int, memoryview]:
    ...

def decode_raw(multihash_digest: Union[BytesLike, BufferedIOBase]) -> Tuple[int, Union[bytes, memoryview]]:
    """
        Decodes a multihash digest into a code and raw digest pair:

        ```
        <code><size><hash digest> -> (<code>, <hash digest>)
        ```

        Unlike `decode`, this function performs no checks involving the multihash code,
        which is simply returned as an integer.

        Example usage:

        ```py
        >>> multihash_digest = bytes.fromhex("1214c0535e4be2b79ffd93291305436bf889314e4a3f")
        >>> code, digest = multihash.decode_raw(multihash_digest, "sha2-256")
        >>> code
        18 # the code 0x12 of 'sha2-256'
        >>> digest.hex()
        'c0535e4be2b79ffd93291305436bf889314e4a3f'
        ```

    """
    # switch between memoryview mode and stream mode
    if isinstance(multihash_digest, BufferedIOBase):
        stream_mode = True
        validate(multihash_digest, BufferedIOBase)
        stream: Union[memoryview, BufferedIOBase] = multihash_digest
    else:
        stream_mode = False
        stream = memoryview(multihash_digest)
    # extract multihash code
    multihash_code, _, stream = varint.decode_raw(multihash_digest)
    # extract hash digest size
    digest_size, _, stream = varint.decode_raw(stream)
    # extract hash digest
    if stream_mode:
        # use only the number of bytes specified by the multihash
        hash_digest = cast(BufferedIOBase, stream).read(digest_size)
    else:
        # use all remaining bytes
        hash_digest = cast(memoryview, stream)
    # check that the hash digest size is valid
    if digest_size != len(hash_digest):
        raise ValueError(f"Multihash digest lists size {digest_size}, but the hash digest has size {len(hash_digest)} instead.")
    return multihash_code, hash_digest
