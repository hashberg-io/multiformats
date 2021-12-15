"""
    Implementation of the [multihash spec](https://github.com/multiformats/multihash).

    Core functionality is provided by the `digest`, `encode`, `decode` functions.
    The `digest` function can be used to create a multihash digest directly from data:

    ```py
    >>> data = b"Hello world!"
    >>> multihash_digest = multihash.digest(data, "sha2-256")
    >>> multihash_digest.hex()
    '1220c0535e4be2b79ffd93291305436bf889314e4a3faec05ecffcbb7df31ad9e51a'
    ```
    By default, the full digest produced by the hash function is used.
    Optionally, a smaller digest size can be specified to produce truncated hashes:

    ```py
    >>> multihash_digest = multihash.digest(data, "sha2-256", size=20)
    #                  optional truncated hash size, in bytes ^^^^^^^
    >>> multihash_digest.hex()
    '1214c0535e4be2b79ffd93291305436bf889314e4a3f' # 20-bytes truncated hash
    ```

    The `decode` function can be used to extract the raw hash digest from a multihash digest:

    ```py
    >>> multihash_digest.hex()
    '1214c0535e4be2b79ffd93291305436bf889314e4a3f'
    >>> hash_digest = multihash.decode(multihash_digest)
    >>> hash_digest.hex()
        'c0535e4be2b79ffd93291305436bf889314e4a3f'
    ```

    The `encode` function can be used to encode a raw hash digest into a multihash digest:

    ```py
    >>> hash_digest.hex()
        'c0535e4be2b79ffd93291305436bf889314e4a3f'
    >>> multihash.encode(hash_digest, "sha2-256").hex()
    '1214c0535e4be2b79ffd93291305436bf889314e4a3f'
    ```

    Note the both multihash code and digest length are encoded as varints
    (see the `multiformats.varint` module) and can span multiple bytes:

    ```py
    >>> multihash.get("skein1024-1024")
    Multicodec(name='skein1024-1024', tag='multihash', code='0xb3e0',
               status='draft', description='')
    >>> multihash.digest(data, "skein1024-1024").hex()
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
    >>> hash_digest
              b'\\xc0S^K\\xe2\\xb7\\x9f\\xfd\\x93)\\x13\\x05Ck\\xf8\\x891NJ?'
    >>> multihash_digest
    b'\\x12\\x14\\xc0S^K\\xe2\\xb7\\x9f\\xfd\\x93)\\x13\\x05Ck\\xf8\\x891NJ?'
    # ^^^^^      0x12 -> multihash multicodec "sha2-256"
    #      ^^^^^ 0x14 -> truncated hash length of 20 bytes
    ```

    The multihash multicodec specified by a given multihash digest is accessible using the `from_digest` function:

    ```py
    >>> multihash.from_digest(multihash_digest)
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
    Multicodec(name='sha1', tag='multihash', code='0x11',
               status='permanent', description='')
    >>> multihash.exists(code=0x11)
    True
    >>> multihash.get(code=0x11)
    Multicodec(name='sha1', tag='multihash', code='0x11',
               status='permanent', description='')
    ```

    The `table` function can be used to iterate through known multihash multicodecs:

    ```py
    >>> [x.name for x in multihash.table() if x.name.startswith("sha")]
    ['sha1', 'sha2-256', 'sha2-512', 'sha3-512', 'sha3-384', 'sha3-256',
     'sha3-224', 'shake-128', 'shake-256', 'sha2-384', 'sha2-256-trunc254-padded',
     'sha2-224', 'sha2-512-224', 'sha2-512-256']
    ```

    The `is_implemented` and `implementation` functions expose whether a multihash multicodec
    has a registered implementation and return it, respectively:

    ```py
    >>> multihash.is_implemented("sha2-256")
    True
    >>> codec, hash_fun, max_digest_size = multihash.implementation("sha2-256")
    >>> codec # the multihash multicodec
    Multicodec(name='sha2-256', tag='multihash', code='0x12',
               status='permanent', description='')
    >>> hash_fun # computes the raw hash
    <function _hashlib_sha.<locals>.hashfun at 0x000002D0690DEF70>
    >>> max_digest_size # in bytes (can be None)
    32
    ```
"""

from io import BytesIO, BufferedIOBase
from typing import AbstractSet, Any, cast, Dict, Iterator, Mapping, Optional, overload, Union, Sequence, Tuple, TypeVar
from typing_validation import validate

from multiformats import multicodec, varint
from multiformats.multicodec import Multicodec
from multiformats.varint import BytesLike

from . import hashfun
from .hashfun import Hashfun



def get(name: Optional[str] = None, *, code: Optional[int] = None) -> Multicodec:
    """
        Gets the multihash multicodec with given name or code.
        Raises `KeyError` if no such multihash exists.
        Exactly one of `name` and `code` must be specified.

        Example usage:

        ```py
        >>> multihash.get("sha1")
        Multicodec(name='sha1', tag='multihash', code='0x11',
                   status='permanent', description='')
        >>> multihash.get(code=0x11)
        Multicodec(name='sha1', tag='multihash', code='0x11',
                   status='permanent', description='')
        ```

    """
    multihash = multicodec.get(name, code=code)
    if multihash.tag != "multihash":
        raise ValueError(f"Multicodec named {repr(name)} exists, but is not a multihash.")
    return multihash


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


def validate_multihash(multihash: Multicodec) -> None:
    """
        Validates a multihash:

        - raises `KeyError` if no multihash with the given name is registered
        - raises `ValueError` if a multihash with the given name is registered, but is different from the one given
        - raises no error if the given multihash is registered
    """
    validate(multihash, Multicodec)
    mc = get(multihash.name)
    if mc != multihash:
        raise ValueError(f"Multihash multicodec named {multihash.name} exists, but is not the one given.")


def from_digest(multihash_digest: Union[BytesLike, memoryview]) -> Multicodec:
    """
        Returns the multihash multicodec for the given digest,
        according to the code specified by its prefix.
        Raises `KeyError` if no multihash exists with that code.

        Example usage:

        ```py
        >>> multihash_digest = bytes.fromhex("140a9a7a8207a57d03e9c524")
        >>> multihash.from_digest(multihash_digest)
        Multicodec(name='sha3-512', tag='multihash', code='0x14',
                   status='permanent', description='')
        ```
    """
    code, _, _ = varint.decode_raw(multihash_digest)
    return get(code=code)


def table() -> Iterator[Multicodec]:
    """
        Iterates through the registered multihash multicodecs, in order of ascending code.

        Example usage:

        ```py
        >>> [x.name for x in multihash.table() if x.name.startswith("sha")]
        ['sha1', 'sha2-256', 'sha2-512', 'sha3-512', 'sha3-384', 'sha3-256',
         'sha3-224', 'shake-128', 'shake-256', 'sha2-384', 'sha2-256-trunc254-padded',
         'sha2-224', 'sha2-512-224', 'sha2-512-256']
        ```
    """
    return multicodec.table(tag="multihash")


def is_implemented(multihash: Union[str, int, Multicodec]) -> bool:
    """
        Whether the given multihash has an implementation.
    """
    try:
        implementation(multihash)
        return True
    except KeyError:
        return False


def implementation(multihash: Union[str, int, Multicodec]) -> Tuple[Multicodec, Hashfun, Optional[int]]:
    """
        Returns the implementation of a multihash multicodec, as a triple:

        ```py
        codec, hash_function, max_digest_size = multihash.implementation("sha2-256")
        ```

        Above, `codec` is the `multiformats.multicodec.Multicodec` object carrying information about the
        multihash multicodec, `hash_function` is the function `bytes->bytes` computing the raw hashes,
        and `max_digest_size` is the max size of the digests produced by `hash_function` (or `None` if
        there is no max size, such as in the case of the 'identity' multihash multicodec).
    """
    validate(multihash, Union[str, int, Multicodec])
    if isinstance(multihash, str):
        multihash = get(multihash)
    elif isinstance(multihash, int):
        multihash = get(code=multihash)
    elif multihash != get(multihash.name):
        raise ValueError(f"A multihash multicodec named {repr(multihash.name)} exists, "
                         f"but it is different from the one passed to this function.")
    if multihash.tag != "multihash":
        raise ValueError(f"Multicodec '{multihash.name}' exists, but it is not a multihash multicodec.")
    hash_function, digest_size = hashfun.get(multihash.name)
    return multihash, hash_function, digest_size


def encode(hash_digest: BytesLike, multihash: Union[str, int, Multicodec]) -> bytes:
    """
        Encodes the given bytes into a multihash digest using the given multihash:

        ```
        <hash digest> -> <code><size><hash digest>
        ```

        If the multihash is passed by name or code, the `get` function is used to retrieve it.

        Example usage:

        ```py
        >>> multihash.get("sha2-256")
        Multicodec(name='sha2-256', tag='multihash', code='0x12',
                   status='permanent', description='')
        >>> hash_digest = bytes.fromhex("c0535e4be2b79ffd93291305436bf889314e4a3f")
        >>> len(hash_digest)
        20
        >>> multihash.encode(hash_digest, "sha2-256").hex()
        "1214c0535e4be2b79ffd93291305436bf889314e4a3f"
        #^^   code 0x12 for multihash multicodec "sha2-256"
        #  ^^ truncated hash length 0x14 = 20 bytes
        ```

        Note that all digests are `bytes` objects, represented here as hex strings for clarity:

        ```py
        >>> hash_digest
        b'\\xc0S^K\\xe2\\xb7\\x9f\\xfd\\x93)\\x13\\x05Ck\\xf8\\x891NJ?'
        >>> multihash.encode(hash_digest, "sha2-256")
        b'\\x12\\x14\\xc0S^K\\xe2\\xb7\\x9f\\xfd\\x93)\\x13\\x05Ck\\xf8\\x891NJ?'
        # ^^^^^      0x12 -> multihash multicodec "sha2-256"
        #      ^^^^^ 0x14 -> truncated hash length of 20 bytes
        ```

    """
    validate(hash_digest, BytesLike)
    multihash, _, digest_size = implementation(multihash)
    size = len(hash_digest)
    if digest_size is not None and size > digest_size:
        raise ValueError(f"Digest size {digest_size} is listed for {multihash.name}, "
                         f"but a digest of larger size {size} was given to be encoded.")
    return varint.encode(multihash.code)+varint.encode(size)+hash_digest


def digest(data: BytesLike, multihash: Union[str, int, Multicodec], *, size: Optional[int] = None) -> bytes:
    """
        Computes and returns the multihash digest of the given data.

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
    multihash, hf, digest_size = implementation(multihash)
    hash_digest = hf(data)
    if digest_size is not None:
        if len(hash_digest) != digest_size:
            raise ValueError(f"Digest size {digest_size} is listed for {multihash.name}, "
                             f"but a digest of different size {len(hash_digest)} was produced by the hash function.")
        if size is not None:
            if size > digest_size:
                raise ValueError(f"Digest size {digest_size} is listed for {multihash.name}, "
                                 f"but a larger digest size {size} was requested.")
            hash_digest = hash_digest[:size] # truncate digest
    return varint.encode(multihash.code)+varint.encode(len(hash_digest))+hash_digest


def decode(multihash_digest: Union[BytesLike, BufferedIOBase],
           multihash: Union[None, str, int, Multicodec]=None) -> bytes:
    """
        Decodes a multihash digest into a hash digest:

        ```
        <code><size><hash digest> -> <hash digest>
        ```

        If `multihash_digest` is one of bytes, bytearray or memoryview, the method also checks
        that the actual hash digest size matches the size listed by the multihash digest.
        If `multihash` is not `None`, the function additionally enforces that the code from the
        multihash digest matches the code of the multihash codec.
        Regardless, the function checks that the multihash with code specified by the digest exists.

        Example usage:

        ```py
        >>> multihash_digest = bytes.fromhex("1214c0535e4be2b79ffd93291305436bf889314e4a3f")
        >>> multihash.decode(multihash_digest, "sha2-256").hex()
        'c0535e4be2b79ffd93291305436bf889314e4a3f'
        ```

    """
    # if multihash multicodec is specified, obtain max ditest size
    if multihash is not None:
        multihash, _, max_digest_size = implementation(multihash)
    code, digest = decode_raw(multihash_digest)
    decoded_multihash = get(code=code)
    if multihash is None:
        multihash, _, max_digest_size = implementation(decoded_multihash)
    elif decoded_multihash != multihash:
        raise ValueError(f"A multihash multicodec with code {multihash.code} exists, but is not the one given.")
    if max_digest_size is not None and len(digest) > max_digest_size:
        raise ValueError(f"Multihash {multihash.name} has max digest size {max_digest_size}, "
                         f"but a digest of larger size {len(digest)} was decoded instead.")
    return digest

_BufferedIOT = TypeVar("_BufferedIOT", bound=BufferedIOBase)

@overload
def decode_raw(multihash_digest: BufferedIOBase) -> Tuple[int, bytes]:
    ...

@overload
def decode_raw(multihash_digest: BytesLike) -> Tuple[int, memoryview]:
    ...

def decode_raw(multihash_digest: Union[BytesLike, BufferedIOBase]) -> Tuple[int, Union[bytes, memoryview]]:
    """
        Decodes a multihash digest into a hash digest and code:

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
