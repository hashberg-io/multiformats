"""
    Implementation of raw data encodings used by multibase encodings.

    The majority of the encodings is provided by the [`bases`](https://github.com/hashberg-io/bases) library,
    as instances of the `BaseEncoding` class. The following custom encodings are also implemented:

    - multibase identity
    - multibase proquints

    Core functionality is provided by the `get` and `exists` functions, which can be used to check
    whether a raw encoding with given name is known, and if so to get the corresponding object:

    ```py
    >>> from multiformats.multibase import raw_encoding
    >>> raw_encoding.exists("base10")
    True
    >>> raw_encoding.get("base10")
    ZeropadBaseEncoding(StringAlphabet('0123456789'))
    ```

    The raw encoding objects have `encode` and `decode` methods that can be used to
    convert between bytestrings and strings (not including the multibase code):

    ```py
    >>> base16 = raw_encoding.get("base16")
    >>> base16.encode(bytes([0xAB, 0xCD]))
    'abcd'
    >>> base16.decode('abcd')
    b'\\xab\\xcd'
    ```
"""

import binascii
from types import MappingProxyType
from typing import Callable, Dict, List, Union
from typing_validation import validate

from bases import (base2, base16, base8, base10, base36, base58btc, base58flickr,
                   base32, base32hex, base32z, base64, base64url,)
from bases.encoding import BaseEncoding

RawEncoder = Callable[[bytes], str]
RawDecoder = Callable[[str], bytes]

class CustomEncoding:
    """
        Class for custom raw encodings, implemented by explicitly passing raw encoding and decoding functions.
        The raw encoder and decoder are expected to validate their own arguments.
    """

    _raw_encoder: Callable[[bytes], str]
    _raw_decoder: Callable[[str], bytes]

    def __init__(self, raw_encoder: Callable[[bytes], str], raw_decoder: Callable[[str], bytes]):
        # validate(raw_encoder, Callable[[bytes], str]) # TODO: not yet supported by typing-validation
        # validate(raw_decoder, Callable[[str], bytes]) # TODO: not yet supported by typing-validation
        self._raw_encoder = raw_encoder # type: ignore
        self._raw_decoder = raw_decoder # type: ignore

    def encode(self, b: bytes) -> str:
        """
            Calls the custom raw encoder.
        """
        raw_encoder: Callable[[bytes], str] = self._raw_encoder # type: ignore
        return raw_encoder(b)

    def decode(self, s: str) -> bytes:
        """
            Calls the custom raw decoder.
        """
        raw_decoder: Callable[[str], bytes] = self._raw_decoder # type: ignore
        return raw_decoder(s)

    def __repr__(self) -> str:
        _raw_encoder: Callable[[bytes], str] = self._raw_encoder # type: ignore
        _raw_decoder: Callable[[str], bytes] = self._raw_decoder # type: ignore
        return f"CustomEncoding({repr(_raw_encoder)}, {repr(_raw_decoder)})"


RawEncoding = Union[CustomEncoding, BaseEncoding]
_raw_encodings: Dict[str, RawEncoding] = {}

def get(name: str) -> RawEncoding:
    """
        Gets the raw encoding with given name. Raises `KeyError` if no such encoding exists.

        Example usage:

        ```py
        >>> raw_encoding.get("base16")
        ZeropadBaseEncoding(
            StringAlphabet('0123456789abcdef',
                           case_sensitive=False),
            block_nchars=2)
        ```
    """
    validate(name, str)
    if name not in _raw_encodings:
        raise KeyError(f"No raw encoding named {repr(name)}.")
    return _raw_encodings[name]


def exists(name: str) -> bool:
    """
        Checks whether a raw encoding with given name exists.

        Example usage:

        ```py
        >>> raw_encoding.exists("base16")
        True
        ```
    """
    validate(name, str)
    return name in _raw_encodings


def register(name: str, enc: RawEncoding, *, overwrite: bool = False) -> None:
    """
        Registers a raw encoding by name. The optional keyword argument `overwrite` (default: `False`)
        can be used to overwrite a multibase encoding with existing name.

        If `overwrite` is `False`, raises `ValueError` if a raw encoding with the same name already exists.

        Example usage:

        ```py
        >>> from bases import base45
        >>> raw_encoding.register("base45upper", base45)
        >>> raw_encoding.get("base45upper")
        BlockBaseEncoding(
            StringAlphabet('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:',
                           case_sensitive=False),
            block_size={1: 2, 2: 3}, reverse_blocks=True)
        ```
    """
    validate(name, str)
    validate(enc, RawEncoding)
    validate(overwrite, bool)
    if not overwrite and name in _raw_encodings:
        raise ValueError(f"Raw encoding with name {repr(name)} already exists: {_raw_encodings[name]}")
    _raw_encodings[name] = enc


def unregister(name: str) -> None:
    """
        Unregisters a raw encoding by name.
        Raises `KeyError` if no such raw encoding exists.

        Example usage:

        ```py
        >>> raw_encoding.unregister("base45upper")
        >>> raw_encoding.exists("base45upper")
        False
        ```
    """
    validate(name, str)
    if name not in _raw_encodings:
        raise KeyError(f"Raw encoding with name {repr(name)} does not exist.")
    del _raw_encodings[name]


def identity_raw_encoder(b: bytes) -> str:
    """
        Implementation of the raw identity encoder according to the [multibase spec](https://github.com/multiformats/multibase/).
    """
    validate(b, bytes)
    return b.decode("utf-8")

identity_raw_encoder.__repr__ = lambda: "identity_raw_encoder" # type: ignore


def identity_raw_decoder(s: str) -> bytes:
    """
        Implementation of the raw identity decoder according to the [multibase spec](https://github.com/multiformats/multibase/).
    """
    validate(s, str)
    return s.encode("utf-8")

identity_raw_decoder.__repr__ = lambda: "identity_raw_decoder" # type: ignore


_proquint_consonants = "bdfghjklmnprstvz"
_proquint_consonants_set = frozenset("bdfghjklmnprstvz")
_proquint_vowels = "aiou"
_proquint_vowels_set = frozenset("aiou")
_proquint_consonants_revdir = MappingProxyType({char: idx for idx, char in enumerate(_proquint_consonants)})
_proquint_vowels_revdir = MappingProxyType({char: idx for idx, char in enumerate(_proquint_vowels)})


def proquint_raw_encoder(b: bytes) -> str:
    """
        Implementation of the proquint encoder according to the [proquint spec](https://arxiv.org/html/0901.4016),
        with additional 'ro-' prefix as prescribed by the [multibase spec](https://github.com/multiformats/multibase/)
        and extended to include odd-length bytestrings (adding a final 3-letter block, using two zero pad bits).
    """
    validate(b, bytes)
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
        Implementation of the proquint decoder according to the [proquint spec](https://arxiv.org/html/0901.4016),
        with additional 'ro-' prefix as prescribed by the [multibase spec](https://github.com/multiformats/multibase/)
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


# custom encodings
register("identity", CustomEncoding(identity_raw_encoder, identity_raw_decoder))
register("proquint", CustomEncoding(proquint_raw_encoder, proquint_raw_decoder))

# base encodings
register("base2", base2)
register("base8", base8)
register("base10", base10)
register("base16", base16.lower())
register("base16upper", base16)
register("base32hex", base32hex.nopad().lower())
register("base32hexupper", base32hex.nopad())
register("base32hexpad", base32hex.lower())
register("base32hexpadupper", base32hex)
register("base32", base32.nopad().lower())
register("base32upper", base32.nopad())
register("base32pad", base32.lower())
register("base32padupper", base32)
register("base32z", base32z)
register("base36", base36.lower())
register("base36upper", base36)
register("base58btc", base58btc)
register("base58flickr", base58flickr)
register("base64", base64.nopad())
register("base64pad", base64)
register("base64url", base64url.nopad())
register("base64urlpad", base64url)


# additional docs info
__pdoc__ = {
    "identity_raw_encoder": False, # exclude from docs
    "identity_raw_decoder": False, # exclude from docs
    "proquint_raw_encoder": False, # exclude from docs
    "proquint_raw_decoder": False, # exclude from docs
}
