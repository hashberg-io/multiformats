"""
    Implementation of raw hash functions used by multihash multicodecs.

    Hash functions are implemented using the following modules:

    - `hashlib <https://docs.python.org/3/library/hashlib.html>`_, for the ``sha``/``shake`` hash functions and the ``blake2`` hash functions.
    - `pysha3 <https://github.com/tiran/pysha3>`_, for the ``keccak`` hash functions.
    - `blake3 <https://github.com/oconnor663/blake3-py>`_, for the ``blake3`` hash function.
    - `pyskein <https://pythonhosted.org/pyskein/>`_, for the ``skein`` hash functions.
    - `mmh3 <https://github.com/hajimes/mmh3>`_, for the ``murmur3`` hash functions.
    - `pycryptodomex <https://github.com/Legrandin/pycryptodome/>`_, for the ``ripemd-160`` hash function, \
      the ``kangarootwelve`` hash function and the ``sha2-512-224``/``sha2-512-256`` hash functions.

    All modules other than `hashlib <https://docs.python.org/3/library/hashlib.html>`_ are optional dependencies.
    The :func:`get` function attempts to dynamically import any optional dependencies required by desired multihash
    implementation, raising :py:obj:`ImportError` if the dependency is not installed.

    Core functionality is provided by the :func:`exists` and :func:`get` functions,
    which can be used to check whether an implementatino with given name is known, and if so to get the corresponding pair
    of hash function and max digest size:

    >>> multihash.hashfun.exists("sha2-256")
    True
    >>> multihash.hashfun.get("sha2-256")
    (<function _hashlib_sha.<locals>.hashfun at 0x0000013F4A3C6160>, 32)

    The hash functions take a single :obj:`bytes` input (the data) and return a :obj:`bytes` output (the hash digest).
    The max digest sizes (if not :obj:`None`) are used to sense-check hash digests passed to :func:`~multiformats.multihash.wrap`
    and/or obtained from :func:`~multiformats.multihash.unwrap`: telling whether a digest has been generated by a hash function
    is deemed to be computationally unfeasible in general,
    but hash digests of length greater than the max digest size can always be discounted as invalid.
"""

from __future__ import annotations

import re
from typing import Dict, Optional, Tuple
from typing_validation import validate

from multiformats import multicodec
from multiformats.varint import BytesLike
from .err import MultihashKeyError, MultihashValueError
from ._hashfuns import Hashfun, validate_hashfun_args, repeat_hashfun

__all__ = ["Hashfun"]

_hashfun: Dict[str, Tuple[Hashfun, Optional[int]]] = {}

MultihashImpl = Tuple[Hashfun, Optional[int]]
"""Type alias for multihash implementations."""

def get(name: str) -> MultihashImpl:
    """
        Given a multihash multicodec name, returns its implementation as a pair of a hash function
        and a max digest size (possibly :obj:`None`).

        >>> multihash.hashfun.get("sha2-256")
        (<function _hashlib_sha.<locals>.hashfun at 0x0000013F4A3C6160>, 32)

        :param name: the name of the multihash
        :type name: :obj:`str`

        :raises KeyError: if no implementation is available for this name

        :rtype: :obj:`MultihashImpl`
    """
    validate(name, str)
    if name not in _hashfun:
        if not _jit_register_hashfun(name):
            raise MultihashKeyError(f"No implementation for multihash multicodec {repr(name)}.")
    return _hashfun[name]


def exists(name: str) -> bool:
    """
        Checks whether the multihash multicodec with given name has an implementation.

        >>> multihash.hashfun.exists("sha2-256")
        True

        :param name: the name of the multihash
        :type name: :obj:`str`

    """
    validate(name, str)
    if name in _hashfun:
        return True
    return _jit_register_hashfun(name, check_only=True)


def register(name: str, hashfun: Hashfun, digest_size: Optional[int], *, overwrite: bool = False) -> None:
    """
        Registers a hash function and hash digest size implementing the multihash multicodec with given name,
        which must already exist.

        Example usage (from the source code of this module):

        .. code-block:: python

            register("sha1", _hashlib_sha(1), 20) # max digest size is 20 bytes, i.e. 160 bits
            register(f"sha2-256", _hashlib_sha(2, 256), 256//8)

        :param name: the name of the multihash
        :type name: :obj:`str`
        :param hashfun: the raw hash function
        :type hashfun: :obj:`Hashfun`
        :param digest_size: the max size for digests, or :obj:`None` if not max size
        :type digest_size: :obj:`int` or :obj:`None`
        :param overwrite: whether an existing implementation with the same name should be overwritten
        :type overwrite: :obj:`bool`, *optional*

        :raises ValueError: if ``overwrite`` is :obj:`False` and an implementation the same name already exists
    """
    validate(name, str)
    # validate(hashfun, Hashfun) # TODO: not yet supported by typing-validation
    validate(digest_size, Optional[int])
    validate(overwrite, bool)
    if digest_size is not None and digest_size <= 0:
        raise MultihashValueError("Digest size must be positive or None.")
    if not overwrite and name in _hashfun:
        raise MultihashValueError(f"An implementation for the multihash multicodec named {repr(name)} already exists.")
    if name not in _hashfun:
        multihash = multicodec.get(name)
        if multihash.tag != "multihash":
            raise MultihashValueError(f"Multicodec '{multihash.name}' exists, but it is not a multihash multicodec.")
    _hashfun[name] = (hashfun, digest_size)


def unregister(name: str) -> None:
    """
        Unregisters a raw encoding by multihash name.

        :param name: the name of the multihash
        :type name: :obj:`str`

        :raises KeyError: if no such raw encoding exists
    """
    validate(name, str)
    if name not in _hashfun:
        raise MultihashKeyError(f"There is no implementation for multihash multicodec with name {repr(name)}.")
    del _hashfun[name]

# identity has function is always registered

def _identity(data: BytesLike, size: Optional[int] = None) -> bytes:
    validate_hashfun_args(data, size, None)
    d = bytes(data)
    if size is None:
        return d
    if len(d) < size:
        raise MultihashValueError("With 'identity' hash, size must be at most data lenght in bytes.")
    return d[:size]

register("identity", _identity, None)

# just-in-time hash implementation registration functions

_sha1_regex = re.compile(r"sha1")
_sha23_regex = re.compile(r"sha(2|3)-(224|256|384|512)")
_shake_regex = re.compile(r"sha(ke)-(128|256)")
_sha2_512_regex = re.compile(r"sha2-512-(224|256)")
_sha2_256_trunc254_padded_regex = re.compile(r"sha2-256-trunc254-padded")

def _jit_register_hashfun_sha(name: str, check_only: bool = False) -> bool:
    # 'sha' hash functions
    m = re.fullmatch(_sha1_regex, name)
    if m is not None:
        from ._hashfuns.sha import _jit_register_sha1 # pylint: disable = import-outside-toplevel
        return _jit_register_sha1(m, None if check_only else register)
    m = re.fullmatch(_sha23_regex, name)
    if m is None:
        m = re.fullmatch(_shake_regex, name)
    if m is not None:
        from ._hashfuns.sha import _jit_register_sha23ke # pylint: disable = import-outside-toplevel
        return _jit_register_sha23ke(m, None if check_only else register)
    m = re.fullmatch(_sha2_512_regex, name)
    if m is not None:
        from ._hashfuns.sha import _jit_register_sha2_512 # pylint: disable = import-outside-toplevel
        return _jit_register_sha2_512(m, None if check_only else register)
    m = re.fullmatch(_sha2_256_trunc254_padded_regex, name)
    if m is not None:
        from ._hashfuns.filecoin import _jit_register_sha_256_trunc254_padded # pylint: disable = import-outside-toplevel
        return _jit_register_sha_256_trunc254_padded(m, None if check_only else register)
    return False

_blake2_regex = re.compile(r"blake2([bs])-([89]|[1-9][0-9]|[1-5][0-9][0-9])")
_blake3_regex = re.compile(r"blake3")

def _jit_register_hashfun_bla(name: str, check_only: bool = False) -> bool:
    # 'blake' hash functions
    m = re.fullmatch(_blake2_regex, name)
    if m is not None:
        from ._hashfuns.blake import _jit_register_blake2 # pylint: disable = import-outside-toplevel
        return _jit_register_blake2(m, None if check_only else register)
    m = re.fullmatch(_blake3_regex, name)
    if m is not None:
        from ._hashfuns.blake import _jit_register_blake3 # pylint: disable = import-outside-toplevel
        return _jit_register_blake3(m, None if check_only else register)
    return False

_keccak_regex = re.compile(r"keccak-(224|256|384|512)")

def _jit_register_hashfun_kec(name: str, check_only: bool = False) -> bool:
    # 'keccak' hash function
    m = re.fullmatch(_keccak_regex, name)
    if m is not None:
        from ._hashfuns.keccak import _jit_register_keccak # pylint: disable = import-outside-toplevel
        return _jit_register_keccak(m, None if check_only else register)
    return False

_skein_regex = re.compile(r"skein(256|512|1024)-([89]|[1-9][0-9]|[1-9][0-9][0-9]|10[0-2][0-9])")

def _jit_register_hashfun_ske(name: str, check_only: bool = False) -> bool:
    # 'skein' hash function
    m = re.fullmatch(_skein_regex, name)
    if m is not None:
        from ._hashfuns.skein import _jit_register_skein # pylint: disable = import-outside-toplevel
        return _jit_register_skein(m, None if check_only else register)
    return False

_murmur3_regex = re.compile(r"murmur3-(32)|murmur3-(x64)-(64|128)")

def _jit_register_hashfun_mur(name: str, check_only: bool = False) -> bool:
    # 'murmur3' hash function
    m = re.fullmatch(_murmur3_regex, name)
    if m is not None:
        from ._hashfuns.murmur3 import _jit_register_murmur3 # pylint: disable = import-outside-toplevel
        return _jit_register_murmur3(m, None if check_only else register)
    return False

_md5_regex = re.compile("md5")

def _jit_register_hashfun_md5(name: str, check_only: bool = False) -> bool:
    # 'md5' hash function
    m = re.fullmatch(_md5_regex, name)
    if m is not None:
        from ._hashfuns.md import _jit_register_md5 # pylint: disable = import-outside-toplevel
        return _jit_register_md5(m, None if check_only else register)
    return False

_ripemd_regex = re.compile(r"ripemd-(160)")

def _jit_register_hashfun_rip(name: str, check_only: bool = False) -> bool:
    # 'ripemd' hash functions
    m = re.fullmatch(_ripemd_regex, name)
    if m is not None:
        from ._hashfuns.md import _jit_register_ripemd # pylint: disable = import-outside-toplevel
        return _jit_register_ripemd(m, None if check_only else register)
    return False

_kangarootwelve_regex = re.compile("kangarootwelve")

def _jit_register_hashfun_kan(name: str, check_only: bool = False) -> bool:
    # 'kangarootwelve' hash function
    m = re.fullmatch(_kangarootwelve_regex, name)
    if m is not None:
        from ._hashfuns.kangarootwelve import _jit_register_kangarootwelve # pylint: disable = import-outside-toplevel
        return _jit_register_kangarootwelve(m, None if check_only else register)
    return False

_dbl_sha2_regex = re.compile(r"dbl-sha2-(256)")

def _jit_register_hashfun_dbl(name: str, check_only: bool = False) -> bool:
    # 'dbl-sha2-256' hash function
    m = re.fullmatch(_dbl_sha2_regex, name)
    if m is not None:
        sha2_256, _ = get("sha2-256")
        assert sha2_256 is not None
        dbl_sha2_256 = repeat_hashfun(sha2_256, repeat=2, truncate="end")
        register("dbl-sha2-256", dbl_sha2_256, 32)
        return True
    return False

# directory of just-in-time hash implementation registration functions

_jit_register_hashfun_dir = {
    "sha": _jit_register_hashfun_sha,
    "bla": _jit_register_hashfun_bla,
    # "kec": _jit_register_hashfun_kec, # kec is currently unavailable
    "ske": _jit_register_hashfun_ske,
    "mur": _jit_register_hashfun_mur,
    "md5": _jit_register_hashfun_md5,
    "rip": _jit_register_hashfun_rip,
    "kan": _jit_register_hashfun_kan,
    "dbl": _jit_register_hashfun_dbl,
}

def _jit_register_hashfun(name: str, check_only: bool = False) -> bool:
    # pylint: disable = too-many-return-statements
    if len(name) < 3:
        return False
    jit_reg_fun = _jit_register_hashfun_dir.get(name[:3], None)
    if jit_reg_fun is None:
        return False
    return jit_reg_fun(name, check_only)
