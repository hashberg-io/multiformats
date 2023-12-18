"""
    Implementation of the `multihash spec <https://github.com/multiformats/multihash>`_.

    Suggested usage:

    >>> from multiformats import multihash
"""

from __future__ import annotations

from io import BytesIO, BufferedIOBase
from typing import AbstractSet, Any, cast, ClassVar, Dict, Iterator, Mapping, Optional, overload, Union, Sequence, Tuple, Type, TypeVar
from weakref import WeakValueDictionary
import sys
from typing_extensions import Literal
from typing_validation import validate

from multiformats import multicodec, varint
from multiformats.multicodec import Multicodec, _hexcode
from multiformats.varint import BytesLike

from . import raw
from .raw import Hashfun, MultihashImpl
from .err import MultihashKeyError, MultihashValueError

class Multihash:
    """
        Container class for a multibase encoding.

        Example usage:

        >>> sha2_256 = multihash.get("sha2-256")
        >>> sha2_256
        Multihash(codec='sha2-256')

        :param codec: the multicodec defining this multihash
        :type codec: :obj:`str`, :obj:`int` or :class:`~multiformats.multicodec.Multicodec`
    """

    # WeakValueDictionary[str, Multihash]
    _cache: ClassVar[WeakValueDictionary] = WeakValueDictionary() # type: ignore

    _codec: Multicodec
    _implementation: Optional[MultihashImpl]

    __slots__ = ("__weakref__", "_codec", "_implementation")

    def __new__(cls, codec: Union[str, int, Multicodec]) -> "Multihash":
        # check that the codec exists:
        if isinstance(codec, str):
            codec = multicodec.get(codec)
        elif isinstance(codec, int):
            codec = multicodec.get(code=codec)
        else:
            validate(codec, Multicodec)
            existing_codec = multicodec.get(codec.name)
            if existing_codec != codec:
                raise MultihashValueError(f"Multicodec named {repr(codec.name)} exists, but is not the one given.")
            codec = existing_codec
        # check that the codec is a multihash multicodec:
        if codec.tag not in ("multihash", "hash"):
            raise MultihashValueError(f"Multicodec named {repr(codec.name)} exists, but is not a hash or multihash.")
        if not raw.exists(codec.name):
            raise MultihashKeyError(f"No implementation for multihash multicodec {repr(codec.name)}.")
        _cache = Multihash._cache
        if codec.name in _cache:
            # if a multihash instance with this name is already registered
            instance: Multihash = _cache[codec.name]
            if instance.codec == codec:
                # same codec, check same implementation:
                if instance._implementation is None:
                    # implementation not loaded yet, can use the existing instance
                    return instance
                if codec.name in raw._hashfun and instance._implementation == raw._hashfun[codec.name]:
                    # nothing changed, can use the existing instance
                    return instance
            # otherwise remove the existing instance
            del _cache[codec.name]
        # create a fresh instance, register it and return it
        instance = super().__new__(cls)
        instance._codec = codec
        instance._implementation = None
        _cache[codec.name] = instance
        return instance

    def __getnewargs__(self) -> tuple[Multicodec]:
        return (self.codec,)

    @property
    def name(self) -> str:
        """
            Multihash multicodec name.

            Example usage:

            >>> sha2_256.name
            'sha2-256'

        """
        return self.codec.name

    @property
    def code(self) -> int:
        """
            Multihash multicodec code.

            Example usage:

            >>> sha2_256.code
            18
            # 18 = 0x12

        """
        return self.codec.code

    @property
    def codec(self) -> Multicodec:
        """
            The multicodec for this multihash.

            Example usage:

            >>> sha2_256.codec
            Multicodec(name='sha2-256', tag='multihash', code='0x12',
                       status='permanent', description='')

        """
        return self._codec

    @property
    def is_cryptographic(self) -> bool:
        """
            Whether this is a cryptographic hash or not, based on whether
            the codec is tagged as ``'multihash'`` or just ``'hash'``.
        """
        return self.codec.tag=="multihash"

    @property
    def max_digest_size(self) -> Optional[int]:
        """
            The maximum size (in bytes) for raw digests of this multihash, or :obj:`None` if there is no maximum size.
            Used to sense-check the wrapped/unwrapped raw digests.

            Example usage:

            >>> sha2_256.max_digest_size
            32
            # 32 bytes = 256 bits

        """
        _, max_digest_size = self.implementation
        return max_digest_size

    @property
    def implementation(self) -> MultihashImpl:
        """
            Returns the implementation of a multihash multicodec, as a pair:

            .. code-block:: python

                hash_function, max_digest_size = multihash.implementation("sha2-256")

            Above, ``codec`` is the :class:`~multiformats.multicodec.Multicodec` object carrying information about the
            multihash multicodec, ``hash_function`` is the function `bytes->bytes` computing the raw hashes,
            and ``max_digest_size`` is the max size of the digests produced by ``hash_function`` (or :obj:`None` if
            there is no max size, such as in the case of the ``'identity'`` multihash multicodec).

            Example usage:

            >>> sha2_256.implementation
            (<function _hashlib_sha.<locals>.hashfun at 0x0000029396E22280>, 32)

            :rtype: :obj:`~multiformats.multihash.raw.MultihashImpl`

        """
        implementation = self._implementation
        if implementation is None:
            implementation = raw.get(self.name)
            self._implementation = implementation
        return implementation

    def wrap(self, raw_digest: BytesLike) -> bytes:
        """
            Wraps a raw digest into a multihash digest:

            .. code-block::

                <raw digest> --> <code><size><raw digest>

            Example usage:

            >>> sha2_256 = multihash.get("sha2-256")
            >>> raw_digest = bytes.fromhex(
            ... "c0535e4be2b79ffd93291305436bf889314e4a3f")
            >>> sha2_256.wrap(raw_digest).hex()
            "1214c0535e4be2b79ffd93291305436bf889314e4a3f"

            :param raw_digest: the raw digest
            :type raw_digest: :obj:`~multiformats.varint.BytesLike`

            See :func:`wrap` for more information.
        """
        validate(raw_digest, BytesLike)
        _, max_digest_size = self.implementation
        size = len(raw_digest)
        if max_digest_size is not None and size > max_digest_size:
            raise MultihashValueError(f"Digest size {max_digest_size} is listed for {self.name}, "
                             f"but a digest of larger size {size} was given to be wrapped.")
        return self.codec.wrap(varint.encode(size)+raw_digest)

    def digest(self, data: BytesLike, *, size: Optional[int] = None) -> bytes:
        """
            Computes the raw digest of the given data and wraps it into a multihash digest.

            Example usage:

            >>> sha2_256 = multihash.get("sha2-256")
            >>> data = b"Hello world!"
            >>> data.hex()
            "48656c6c6f20776f726c6421"
            >>> sha2_256.digest(data).hex() # full 32-bytes hash
            '1220c0535e4be2b79ffd93291305436bf889314e4a3faec05ecffcbb7df31ad9e51a'
            >>> sha2_256.digest(data, size=20).hex() # truncated hash
            '1214c0535e4be2b79ffd93291305436bf889314e4a3f'

            :param data: the raw digest
            :type data: :obj:`~multiformats.varint.BytesLike`
            :param size: size for the raw digest, in bytes. If not :obj:`None`, raw digest is truncated to fit the given size.
            :type size: :obj:`int` or :obj:`None`, *optional*

            :raises ValueError: if size parameter is not :obj:`None` and negative.
            :raises ValueError: if size parameter is not :obj:`None`, max digest size is not :obj:`None` and given size exceeds max digest size.
            :raises ValueError: if size parameter is :obj:`None` but a size is required for the hash function (e.g. for the KangarooTwelve XOF).

            See :func:`digest` for more information.
        """
        hf, _ = self.implementation
        raw_digest = hf(data, size)
        # if size is not None:
        #     raw_digest = raw_digest[:size] # truncate digest
        if size is None:
            size = len(raw_digest)
        else:
            assert size == len(raw_digest), f"Expected {size}B digest, found {len(raw_digest)}B digest."
        return self.codec.wrap(varint.encode(size)+raw_digest)

    def unwrap(self, digest: Union[BytesLike, BufferedIOBase]) -> bytes:
        """
            Unwraps a multihash digest into a hash digest:

            .. code-block::

                <code><size><raw digest> --> <raw digest>

            If `digest` is one or :obj:`bytes`, :obj:`bytearray` or :obj:`memoryview`, the method also checks
            that the actual hash digest size matches the size listed by the multihash digest.

            Example usage:

            >>> sha2_256 = multihash.get("sha2-256")
            >>> digest = bytes.fromhex(
            ... "1214c0535e4be2b79ffd93291305436bf889314e4a3f")
            >>> sha2_256.unwrap(digest).hex()
            'c0535e4be2b79ffd93291305436bf889314e4a3f'

            :param digest: the multihash digest to be unwrapped
            :type digest: :obj:`~multiformats.varint.BytesLike` or :obj:`~io.BufferedIOBase`

            See :func:`unwrap` for more information.

        """
        code, raw_digest = unwrap_raw(digest)
        if code != self.code:
            raise MultihashValueError(f"Decoded code {code} differs from multihash code {self.code}.")
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

        Example usage:

        >>> multihash.get("sha1")
        Multihash(codec='sha1')
        >>> multihash.get(code=0x11)
        Multihash(codec='sha1')

        :param name: the multihash name
        :type name: :obj:`str` or :obj:`None`, *optional*
        :param code: the multihash code
        :type code: :obj:`int` or :obj:`None`, *optional*

        :raises KeyError: if the multihash does not exist or is not implemented
        :raises ValueError: unless exactly one of ``name`` and ``code`` is specified

    """
    if name is not None and code is not None:
        raise MultihashValueError("Must specify at most one between 'name' and 'code'.")
    if name is not None:
        return Multihash(codec=name)
    if code is not None:
        return Multihash(codec=code)
    raise MultihashValueError("Must specify at least one between 'name' and 'code'.")


def exists(name: Optional[str] = None, *, code: Optional[int] = None) -> bool:
    """
        Checks whether a multihash multicodec with the given name or code exists.
        This function returns `False` if a multicodec by given name or code exists, but is not tagged ``'multihash'``.

        Example usage:

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

        :param name: the multihash name
        :type name: :obj:`str` or :obj:`None`, *optional*
        :param code: the multihash code
        :type code: :obj:`int` or :obj:`None`, *optional*

        :raises ValueError: unless exactly one of ``name`` and ``code`` is specified

    """
    if not multicodec.exists(name, code=code):
        return False
    codec = multicodec.get(name, code=code)
    return codec.tag == "multihash"


def is_implemented(name: Optional[str] = None, *, code: Optional[int] = None) -> bool:
    """
        Checks whether a multihash with the given name or code exists and is implemented.

        Example usage:

        >>> multihash.is_implemented("sha1")
        True
        >>> multihash.is_implemented(code=0x11)
        True

        :param name: the multihash name
        :type name: :obj:`str` or :obj:`None`, *optional*
        :param code: the multihash code
        :type code: :obj:`int` or :obj:`None`, *optional*

        :raises ValueError: unless exactly one of ``name`` and ``code`` is specified
    """
    if not exists(name, code=code):
        return False
    codec = multicodec.get(name, code=code)
    return raw.exists(codec.name)


def from_digest(digest: BytesLike) -> Multihash:
    """
        Returns the multihash multicodec for the given digest,
        according to the code specified by its prefix.

        Example usage:

        >>> digest = bytes.fromhex("140a9a7a8207a57d03e9c524")
        >>> multihash.from_digest(digest)
        Multihash(codec='sha3-512')

        :param digest: the multihash digest
        :type digest: :obj:`~multiformats.varint.BytesLike`

        :raises KeyError: if no multihash exists with that code
    """
    code, _, _ = multicodec.unwrap_raw(digest)
    return get(code=code)


def wrap(raw_digest: BytesLike, hashfun: Union[str, int, Multihash]) -> bytes:
    """
        Wraps a raw digest into a multihash digest using the given multihash:

        .. code-block::

            <raw digest> --> <code><size><raw digest>

        If the multihash is passed by name or code, the :func:`get` function is used to retrieve it.

        Example usage:

        >>> multihash.get("sha2-256").codec
        Multicodec(name='sha2-256', tag='multihash', code='0x12',
                   status='permanent', description='')
        >>> raw_digest = bytes.fromhex("c0535e4be2b79ffd93291305436bf889314e4a3f")
        >>> len(raw_digest)
        20
        >>> multihash.wrap(raw_digest, "sha2-256").hex()
        "1214c0535e4be2b79ffd93291305436bf889314e4a3f"
        #^^   code 0x12 for multihash multicodec "sha2-256"
        #  ^^ truncated hash length 0x14 = 20 bytes

        Note that all digests above are :obj:`bytes` objects, represented here as hex strings for clarity:

        >>> hash_digest
        b'\\xc0S^K\\xe2\\xb7\\x9f\\xfd\\x93)\\x13\\x05Ck\\xf8\\x891NJ?'
        >>> multihash.wrap(raw_digest, "sha2-256")
        b'\\x12\\x14\\xc0S^K\\xe2\\xb7\\x9f\\xfd\\x93)\\x13\\x05Ck\\xf8\\x891NJ?'
        # ^^^^     0x12 -> multihash multicodec "sha2-256"
        #     ^^^^ 0x14 -> truncated hash length of 20 bytes

        :param raw_digest: the raw hash digest
        :type raw_digest: :obj:`~multiformats.varint.BytesLike`
        :param hashfun: the multihash function name, code or object
        :type hashfun: :obj:`str`, :obj:`int` or :class:`Multihash`

    """
    if not isinstance(hashfun, Multihash):
        hashfun = Multihash(codec=hashfun)
    return hashfun.wrap(raw_digest)


def digest(data: BytesLike, hashfun: Union[str, int, Multihash], *, size: Optional[int] = None) -> bytes:
    """
        Computes the raw digest of the given data and wraps it into a multihash digest.

        Example usage:

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

        Note both multihash code and digest length are wrapped as varints
        (see the `multiformats.varint` module) and can span multiple bytes:

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

        :param data: the data to be digested
        :type data: :obj:`~multiformats.varint.BytesLike`
        :param hashfun: the multihash function name, code or object
        :type hashfun: :obj:`str`, :obj:`int` or :class:`Multihash`
        :param size: size for the raw digest, in bytes. If not :obj:`None`, raw digest is truncated to fit the given size.
        :type size: :obj:`int` or :obj:`None`, *optional*

        :raises ValueError: if size parameter is not :obj:`None` and negative.
        :raises ValueError: if size parameter is not :obj:`None`, max digest size is not :obj:`None` and given size exceeds max digest size.
        :raises ValueError: if size parameter is :obj:`None` but a size is required for the hash function (e.g. for the KangarooTwelve XOF).

    """
    if not isinstance(hashfun, Multihash):
        hashfun = Multihash(codec=hashfun)
    return hashfun.digest(data, size=size)


def _validate_raw_digest_size(name: str, raw_digest: bytes, max_digest_size: Optional[int]) -> None:
    if max_digest_size is not None and len(raw_digest) > max_digest_size:
        raise MultihashValueError(f"Multihash {name} has max digest size {max_digest_size}, "
                         f"but a digest of larger size {len(raw_digest)} was unwrapped instead.")


def unwrap(digest: Union[BytesLike, BufferedIOBase],
           hashfun: Union[None, str, int, Multihash]=None) -> bytes:
    """
        Unwraps a multihash digest into a raw digest:

        .. code-block::

            <code><size><raw digest> --> <raw digest>

        If ``digest`` is one of :obj:`bytes`, :obj:`bytearray` or :obj:`memoryview`, the method also checks
        that the actual raw digest size matches the size listed in the multihash digest.
        If ``digest`` is a stream (an instance of :obj:`~io.BufferedIOBase`, specifically), then the
        number of bytes consumed to produce the raw digest matches the size lised in the multihash digest,
        and no further bytes are consumed from the stream.

        If the optional ``hashfun`` is not ``None``, the function additionally enforces that the code from the
        multihash digest matches the code of the multihash (calls :func:`Multihash.unwrap`
        under the hood to do so). Regardless, the function checks that the multihash with code specified by the
        multihash digest exists and is implemented.

        Example usage:

        >>> digest = bytes.fromhex(
        ... "1214c0535e4be2b79ffd93291305436bf889314e4a3f")
        >>> multihash.unwrap(digest, "sha2-256").hex()
        'c0535e4be2b79ffd93291305436bf889314e4a3f'

        :param digest: the multihash digest
        :type digest: :obj:`~multiformats.varint.BytesLike` or :obj:`~io.BufferedIOBase`
        :param hashfun: the multihash function name, code or object
        :type hashfun: :obj:`str`, :obj:`int` or :class:`Multihash`, *optional*

        :raises ValueError: if the unwrapped raw digest exceeds the stated maximum digest size for the multihash function

    """
    if hashfun is not None:
        if not isinstance(hashfun, Multihash):
            hashfun = Multihash(codec=hashfun)
        return hashfun.unwrap(digest)
    code, raw_digest = unwrap_raw(digest)
    hashfun = Multihash(codec=code)
    _validate_raw_digest_size(hashfun.name, raw_digest, hashfun.max_digest_size)
    return raw_digest


_BufferedIOT = TypeVar("_BufferedIOT", bound=BufferedIOBase)

@overload
def unwrap_raw(digest: BufferedIOBase) -> Tuple[int, bytes]:
    ...

@overload
def unwrap_raw(digest: BytesLike) -> Tuple[int, memoryview]:
    ...

def unwrap_raw(digest: Union[BytesLike, BufferedIOBase]) -> Tuple[int, Union[bytes, memoryview]]:
    """
        Unwraps a multihash digest into a code and raw digest pair:

        .. code-block::

            <code><size><raw digest> --> (<code>, <raw digest>)

        The function checks that the multihash codec with code specified by the multihash digest exists,
        but does not check whether it is implemented or not.

        Example usage:

        >>> digest = bytes.fromhex(
        ... "1214c0535e4be2b79ffd93291305436bf889314e4a3f")
        >>> code, digest = multihash.unwrap_raw(digest, "sha2-256")
        >>> code
        18 # the code 0x12 of 'sha2-256'
        >>> digest.hex()
        'c0535e4be2b79ffd93291305436bf889314e4a3f'

        :param digest: the multihash digest
        :type digest: :obj:`~multiformats.varint.BytesLike` or :obj:`~io.BufferedIOBase`

    """
    # switch between memoryview mode and stream mode
    if isinstance(digest, BufferedIOBase):
        stream_mode = True
        validate(digest, BufferedIOBase)
        stream: Union[memoryview, BufferedIOBase] = digest
    else:
        stream_mode = False
        stream = memoryview(digest)
    # extract multihash code
    code, n, stream = multicodec.unwrap_raw(digest)
    if not exists(code=code):
        n_bytes_read = f" ({n} bytes read)" if stream_mode else ""
        raise MultihashKeyError(f"Multicodec {_hexcode(code)} is not a multihash{n_bytes_read}.")
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
        raise MultihashValueError(f"Multihash digest lists size {digest_size}, but the hash digest has size {len(hash_digest)} instead.")
    return code, hash_digest
