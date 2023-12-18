r"""
    Implementation of raw data encodings used by multibase encodings.

    The majority of the encodings is provided by the `bases <https://github.com/hashberg-io/bases>`_ library,
    as instances of its :class:`~bases.encoding.base.BaseEncoding` class. The following custom encodings are also implemented:

    - multibase identity
    - multibase proquints

    Core functionality is provided by the :func:`get` and :func:`exists` functions,
    which can be used to check whether a raw encoding with given name is known, and if so to get the corresponding object:

    >>> from multiformats.multibase import raw_encoding
    >>> raw_encoding.exists("base10")
    True
    >>> raw_encoding.get("base10")
    ZeropadBaseEncoding(StringAlphabet('0123456789'))

    The raw encoding objects have :meth:`CustomEncoding.encode` and
    :meth:`CustomEncoding.decode` methods that can be used to convert between
    bytestrings and strings (not including the multibase code):

    >>> base16 = raw_encoding.get("base16")
    >>> base16.encode(bytes([0xAB, 0xCD]))
    'abcd'
    >>> base16.decode('abcd')
    b'\xab\xcd'

"""

from __future__ import annotations

import binascii
from itertools import product
from types import MappingProxyType
from typing import Any, Callable, Dict, List, Tuple, Union
from typing_extensions import Literal
from typing_validation import validate

from bases import (base2, base16, base8, base10, base36, base58btc, base58flickr,
                   base32, base32hex, base32z, base64, base64url,)
from bases.encoding import BaseEncoding

from multiformats.varint import BytesLike
from .err import MultibaseKeyError, MultibaseValueError

RawEncoder = Callable[[BytesLike], str]
""" Type alias for a raw base encoder. """

RawDecoder = Callable[[str], bytes]
""" Type alias for a raw base decoder. """

class CustomEncoding:
    """
        Class for custom raw encodings, implemented by explicitly passing raw encoding and decoding functions.
        The raw encoder and decoder are expected to validate their own arguments.
    """

    _raw_encoder: RawEncoder
    _raw_decoder: RawDecoder

    def __init__(self, raw_encoder: RawEncoder, raw_decoder: RawDecoder):
        # validate(raw_encoder, Callable[[bytes], str]) # TODO: not yet supported by typing-validation
        # validate(raw_decoder, Callable[[str], bytes]) # TODO: not yet supported by typing-validation
        self._raw_encoder = raw_encoder
        self._raw_decoder = raw_decoder

    def encode(self, b: BytesLike) -> str:
        """
            Calls the custom raw encoder.

            :param b: the bytestring to be encoded
            :type b: :obj:`~multiformats.varint.BytesLike`
        """
        raw_encoder: RawEncoder = self._raw_encoder
        return raw_encoder(b)

    def decode(self, s: str) -> bytes:
        """
            Calls the custom raw decoder.

            :param s: the string to be decoded
            :type s: :obj:`str`
        """
        raw_decoder: RawDecoder = self._raw_decoder
        return raw_decoder(s)

    def __repr__(self) -> str:
        _raw_encoder: Callable[[bytes], str] = self._raw_encoder
        _raw_decoder: Callable[[str], bytes] = self._raw_decoder
        return f"CustomEncoding({repr(_raw_encoder)}, {repr(_raw_decoder)})"


RawEncoding = Union[CustomEncoding, BaseEncoding]
_raw_encodings: Dict[str, RawEncoding] = {}

def get(name: str) -> RawEncoding:
    """
        Gets the raw encoding with given name.

        Example usage:

        >>> raw_encoding.get("base16")
        ZeropadBaseEncoding(
            StringAlphabet('0123456789abcdef',
                           case_sensitive=False),
            block_nchars=2)

        :param name: the name for the encoding
        :type name: :obj:`str`

        :raises KeyError: if no such encoding exists

        :rtype: :class:`CustomEncoding` or :class:`~bases.encoding.base.BaseEncoding`
    """
    validate(name, str)
    if name not in _raw_encodings:
        if not _jit_register_encoding(name):
            raise MultibaseKeyError(f"No raw encoding named {repr(name)}.")
    return _raw_encodings[name]


def exists(name: str) -> bool:
    """
        Checks whether a raw encoding with given name exists.

        Example usage:

        >>> raw_encoding.exists("base16")
        True

        :param name: the name for the encoding
        :type name: :obj:`str`

    """
    validate(name, str)
    return name in _raw_encodings or name in _jit_registered_encodings


def register(name: str, enc: RawEncoding, *, overwrite: bool = False) -> None:
    """
        Registers a raw encoding by name.

        Example usage:

        >>> from bases import base45
        >>> raw_encoding.register("base45upper", base45)
        >>> raw_encoding.get("base45upper")
        BlockBaseEncoding(
            StringAlphabet('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:',
                           case_sensitive=False),
            block_size={1: 2, 2: 3}, reverse_blocks=True)

        :param name: the name for the encoding being registered
        :type name: :obj:`str`
        :param enc: the raw encoding being registered
        :type enc: :class:`~bases.encoding.base.BaseEncoding` or :class:`CustomEncoding`
        :param overwrite: whether to overwrite an existing encoding with same name (default :obj:`False`)
        :type overwirte: :obj:`bool`, *optional*

        :raises ValueError: if ``overwrite`` is :obj:`False` and a raw encoding with the same name already exists.
    """
    validate(name, str)
    validate(enc, RawEncoding)
    validate(overwrite, bool)
    if not overwrite and name in _raw_encodings:
        raise MultibaseValueError(f"Raw encoding with name {repr(name)} already exists: {_raw_encodings[name]}")
    _raw_encodings[name] = enc


def unregister(name: str) -> None:
    """
        Unregisters a raw encoding by name.

        Example usage:

        >>> raw_encoding.unregister("base45upper")
        >>> raw_encoding.exists("base45upper")
        False

        :param name: the raw encoding name to unregister
        :type name: :obj:`str`
        :raises KeyError: if no such raw encoding exists
    """
    validate(name, str)
    if name not in _raw_encodings:
        raise MultibaseKeyError(f"Raw encoding with name {repr(name)} does not exist.")
    del _raw_encodings[name]


# register base encodings already instantiated by 'bases' v0.2.1
register("base2", base2)
register("base8", base8)
register("base10", base10)
register("base16upper", base16)
register("base32padupper", base32)
register("base32hexpadupper", base32hex)
register("base32z", base32z)
register("base36upper", base36)
register("base58btc", base58btc)
register("base58flickr", base58flickr)
register("base64pad", base64)
register("base64urlpad", base64url)


def _jit_register_identity_encoding() -> None:
    def identity_raw_encoder(b: BytesLike) -> str:
        """
            Implementation of the raw identity encoder according to the `multibase spec <https://github.com/multiformats/multibase/>`_.
        """
        validate(b, Union[bytes, bytearray, memoryview])
        return str(b, "utf-8")
        # if isinstance(b, (bytes, bytearray)):
        #     return b.decode("utf-8")
        # validate(b, memoryview)
        # return bytes(b).decode("utf-8")
    identity_raw_encoder.__repr__ = lambda: "identity_raw_encoder" # type: ignore
    def identity_raw_decoder(s: str) -> bytes:
        """
            Implementation of the raw identity decoder according to the `multibase spec <https://github.com/multiformats/multibase/>`_.
        """
        validate(s, str)
        return s.encode("utf-8")
    identity_raw_decoder.__repr__ = lambda: "identity_raw_decoder" # type: ignore
    register("identity", CustomEncoding(identity_raw_encoder, identity_raw_decoder))

def _jit_register_proquint_encoding() -> None:
    # pylint: disable = too-many-statements
    _proquint_consonants = "bdfghjklmnprstvz"
    _proquint_consonants_set = frozenset("bdfghjklmnprstvz")
    _proquint_vowels = "aiou"
    _proquint_vowels_set = frozenset("aiou")
    _proquint_consonants_revdir = MappingProxyType({char: idx for idx, char in enumerate(_proquint_consonants)})
    _proquint_vowels_revdir = MappingProxyType({char: idx for idx, char in enumerate(_proquint_vowels)})
    def proquint_raw_encoder(b: BytesLike) -> str:
        """
            Implementation of the proquint encoder according to the `proquint spec <https://arxiv.org/html/0901.4016>`_,
            with additional 'ro-' prefix as prescribed by the `multibase spec <https://github.com/multiformats/multibase/>`_
            and extended to include odd-length bytestrings (adding a final 3-letter block, using two zero pad bits).
        """
        validate(b, BytesLike)
        b = memoryview(b) # makes slicing cheap
        consonants = _proquint_consonants
        vowels = _proquint_vowels
        char_blocks: List[str] = []
        for idx in range(0, len(b), 2):
            byte_block = b[idx: idx+2]
            i = int.from_bytes(byte_block, byteorder="big")
            if len(byte_block) == 2: # ordinary byte pair
                i, c2 = divmod(i, 16) # 4 bits
                i, v1 = divmod(i, 4)  # 2 bits
                i, c1 = divmod(i, 16) # 4 bits
                i, v0 = divmod(i, 4)  # 2 bits
                i, c0 = divmod(i, 16) # 4 bits
                assert i == 0
                char_block = consonants[c0]+vowels[v0]+consonants[c1]+vowels[v1]+consonants[c2]
                char_blocks.append(char_block)
            else: # final byte for odd-length bytestrings
                i <<= 2 # add 2 zero pad bits
                i, c1 = divmod(i, 16) # 4 bits
                i, v0 = divmod(i, 4)  # 2 bits
                i, c0 = divmod(i, 16) # 4 bits
                assert i == 0
                char_block = consonants[c0]+vowels[v0]+consonants[c1]
                char_blocks.append(char_block)
        prefix = "ro-" # follows multibase code "p" to make "pro-", e.g. "pro-lusab-babad"
        return prefix+"-".join(char_blocks)
    proquint_raw_encoder.__repr__ = lambda: "proquint_raw_encoder" # type: ignore
    def proquint_raw_decoder(s: str) -> bytes:
        """
            Implementation of the proquint decoder according to the `proquint spec <https://arxiv.org/html/0901.4016>`_,
            with additional 'ro-' prefix as prescribed by the `multibase spec <https://github.com/multiformats/multibase/>`_
            and extended to include odd-length bytestrings (adding a final 3-letter block, using two zero pad bits).
        """
        # pylint: disable = too-many-branches
        validate(s, str)
        consonants = _proquint_consonants
        vowels = _proquint_vowels
        consonants_set = _proquint_consonants_set
        vowels_set = _proquint_vowels_set
        consonants_revdir = _proquint_consonants_revdir
        vowels_revdir = _proquint_vowels_revdir
        # validate string
        if not s.startswith("ro-"):
            raise binascii.Error("Multibase proquint encoded strings must start with 'ro-'.")
        # remove 'ro-' prefix, return empty bytestring if resultant string is empty
        s = s[3:]
        if len(s) == 0:
            return b""
        # validate length for patterns cvcvc (len 5), cvcvc-...-cvc (len 6k+3) or cvcvc-...-cvcvc (len 6k+5)
        if len(s) % 6 not in (3, 5):
            raise binascii.Error("Proquint encoded string length must give remainder of 3 or 5 when divided by 6.")
        # validate characters and convert encoded string into unsigned integer
        i = 0
        for idx, char in enumerate(s):
            if idx % 6 == 5: # separator
                if char != "-":
                    raise binascii.Error(f"Incorrect char at position {idx}: expected '-', found {repr(char)}.")
            elif idx % 2 == 0: # consonant
                if char not in consonants_set:
                    raise binascii.Error(f"Incorrect char at position {idx}: expected consonant in {repr(consonants)}, "
                                         f"found {repr(char)}.")
                i <<= 4 # make space for 4 bits
                i += consonants_revdir[char] # insert consonant bits
            else: # vowel
                if char not in vowels_set:
                    raise binascii.Error(f"Incorrect char at position {idx}: expected vowel in {repr(vowels)}, "
                                         f"found {repr(char)}.")
                i <<= 2 # make space for 2 bits
                i += vowels_revdir[char] # insert vowel bits
        # set number of bytes to number of quintuplets
        nbytes = 2*((len(s)+1)//6)
        # deal with the case of terminating tripled (odd bytestring length)
        if len(s) % 6 == 3:
            # ensure pad bits are zero
            i, pad_bits = divmod(i, 4)
            if pad_bits != 0:
                raise binascii.Error(f"Expected pad bits to be 00, found {bin(pad_bits)[2:]} instead.")
            # add an extra byte
            nbytes += 1
        # convert unsigned integer to bytes and return
        return i.to_bytes(nbytes, byteorder="big")
    proquint_raw_decoder.__repr__ = lambda: "proquint_raw_decoder" # type: ignore
    register("proquint", CustomEncoding(proquint_raw_encoder, proquint_raw_decoder))

def _jit_register_base_encoding(b: Literal[16, 32, 36, 64],
                       _hex: bool = False,
                       _pad: bool = False,
                       _upper: bool = False,
                       _url: bool = False) -> None:
    if b == 64:
        assert not _hex and not _pad and not _upper
        if _url:
            register("base64url", base64url.nopad())
        else:
            register("base64", base64.nopad())
        return
    assert not _url
    if b in (16, 36):
        assert not _hex and not _pad and not _upper
        if b == 16:
            register("base16", base16.lower())
        else:
            register("base36", base36.lower())
        return
    assert b == 32 and (not _pad or not _upper)
    base = base32hex if _hex else base32
    if not _pad:
        base = base.nopad()
    if not _upper:
        base = base.lower()
    key = f"base32{'hex' if _hex else ''}{'pad' if _pad else ''}{'upper' if _upper else ''}"
    register(key, base)

_jit_registered_encodings: Dict[str, Tuple[Callable[..., Any], Any]] = {
    "identity": (_jit_register_identity_encoding, tuple()),
    "proquint": (_jit_register_proquint_encoding, tuple()),
    **{
        f"base64{'url' if _url else ''}": (
            _jit_register_base_encoding,
            (64, False, False, False, _url)
        )
        for _url in (False, True)
    },
    **{
        f"base{b}": (
            _jit_register_base_encoding,
            (b,)
        )
        for b in (16, 36)
    },
    **{
        f"base32{'hex' if _hex else ''}{'pad' if _pad else ''}{'upper' if _upper else ''}": (
            _jit_register_base_encoding,
            (32, _hex, _pad, _upper)
        )
        for _hex, _pad, _upper in product((False, True), repeat=3)
    }
}

def _jit_register_encoding(name: str) -> bool:
    if name not in _jit_registered_encodings:
        return False
    f, args = _jit_registered_encodings[name]
    f(*args)
    return True
