# pylint: disable = missing-docstring

import csv
import hashlib
import importlib.resources as importlib_resources
from typing import Dict, Optional

import pytest
import skein  # type: ignore
from blake3 import blake3 # type: ignore
import sha3 # type: ignore
import mmh3 # type: ignore
from Cryptodome.Hash import RIPEMD160, KangarooTwelve, SHA512

from multiformats import multihash
from multiformats.multihash import wrap, digest, unwrap

def id_digest(data: bytes, size: Optional[int]) -> bytes:
    return data if size is None else data[:size]

def sha1_digest(data: bytes, size: Optional[int]) -> bytes:
    m = hashlib.sha1()
    m.update(data)
    d = m.digest()
    return d if size is None else d[:size]

def sha2_digest(data: bytes, digest_bits: int, size: Optional[int]) -> bytes:
    m: hashlib._Hash = getattr(hashlib, f"sha{digest_bits}")()
    m.update(data)
    d = m.digest()
    return d if size is None else d[:size]

def dbl_sha2_digest(data: bytes, digest_bits: int, size: Optional[int]) -> bytes:
    m: hashlib._Hash = hashlib.sha256()
    m.update(data)
    n: hashlib._Hash = hashlib.sha256()
    n.update(m.digest())
    d = n.digest()
    return d if size is None else d[:size]

def sha3_digest(data: bytes, digest_bits: int, size: Optional[int]) -> bytes:
    m: hashlib._Hash = getattr(hashlib, f"sha3_{digest_bits}")()
    m.update(data)
    d = m.digest()
    return d if size is None else d[:size]

def sha2_512_digest(data: bytes, digest_bits: int, size: Optional[int]) -> bytes:
    m = SHA512.new(truncate=str(digest_bits))
    m.update(data)
    d = m.digest()
    return d if size is None else d[:size]

def shake_digest(data: bytes, digest_bits: int, size: Optional[int]) -> bytes:
    m: hashlib._Hash = getattr(hashlib, f'shake_{digest_bits//2}')()
    m.update(data)
    d = m.digest(digest_bits//8) # type: ignore
    return d if size is None else d[:size]

def blake2_digest(data: bytes, variant: str, digest_bits: int, size: Optional[int]) -> bytes:
    assert variant in ('b', 's')
    m: hashlib._Hash = getattr(hashlib, 'blake2{}'.format(variant))(digest_size=digest_bits//8)
    m.update(data)
    d = m.digest()
    return d if size is None else d[:size]

def blake3_digest(data: bytes, size: int) -> bytes:
    m = blake3()
    m.update(data)
    d: bytes = m.digest(size)
    return d

def skein_digest(data: bytes, variant: int, digest_bits: int, size: Optional[int]) -> bytes:
    assert variant in (256, 512, 1024)
    m: hashlib._Hash = getattr(skein, 'skein{}'.format(variant))(digest_bits=digest_bits)
    m.update(data)
    d = m.digest()
    return d if size is None else d[:size]

def keccak_digest(data: bytes, digest_bits: int, size: Optional[int]) -> bytes:
    m: hashlib._Hash = getattr(sha3, f"keccak_{digest_bits}")()
    m.update(data)
    d = m.digest()
    return d if size is None else d[:size]

# def murmur3_digest(data: bytes, variant: str, digest_bits: int, size: Optional[int]) -> bytes:
#     assert variant in ("32", "x64")
#     if variant == "32":
#         d: bytes = mmh3.hash(data, signed=False).to_bytes(4, byteorder="big") # pylint: disable = c-extension-no-member
#         return d if size is None else d[:size]
#     d = mmh3.hash128(data, signed=False).to_bytes(16, byteorder="big") # pylint: disable = c-extension-no-member
#     d = d[:(digest_bits//8)]
#     return d if size is None else d[:size]

def md5_digest(data: bytes, size: Optional[int]) -> bytes:
    m = hashlib.md5()
    m.update(data)
    d = m.digest()
    return d if size is None else d[:size]

def ripemd_digest(data: bytes, digest_bits: int, size: Optional[int]) -> bytes:
    assert digest_bits == 160
    m = RIPEMD160.new()
    m.update(data)
    d = m.digest()
    return d if size is None else d[:size]

def kangarootwelve_digest(data: bytes, size: int) -> bytes:
    m = KangarooTwelve.new()
    m.update(data)
    return m.read(size)

def sha2_256_trunc254_padded_digest(data: bytes, size: Optional[int]) -> bytes:
    m: hashlib._Hash = hashlib.sha256()
    m.update(data)
    d = m.digest()
    d = d[:-1]+bytes([d[-1]&0x00111111])
    return d if size is None else d[:size]

def _test(hash_fn: str, data: bytes, hash_digest: bytes, size: Optional[int] = None) -> None:
    if size is not None:
        assert len(hash_digest) == size
    multihash_digest = digest(data, hash_fn, size=size)
    assert multihash.exists(hash_fn)
    codec = multihash.get(hash_fn)
    assert hash_fn == codec.name
    assert codec == multihash.from_digest(multihash_digest)
    assert wrap(hash_digest, hash_fn) == multihash_digest
    assert hash_digest == unwrap(multihash_digest)
    assert hash_digest == unwrap(multihash_digest, hash_fn)
    trunc_hash_digest = hash_digest[:len(hash_digest)//2]
    trunc_multihash_digest = wrap(trunc_hash_digest, hash_fn)
    assert trunc_hash_digest == unwrap(trunc_multihash_digest)
    assert trunc_hash_digest == unwrap(trunc_multihash_digest, hash_fn)
    multihash_digest = digest(bytearray(data), hash_fn, size=size)
    assert wrap(bytearray(hash_digest), hash_fn) == multihash_digest
    assert hash_digest == unwrap(bytearray(multihash_digest))
    multihash_digest = digest(memoryview(data), hash_fn, size=size)
    assert wrap(memoryview(hash_digest), hash_fn) == multihash_digest
    assert hash_digest == unwrap(memoryview(multihash_digest))

data_samples = [
    b"",
    b"Test data to be wrapped.",
    b"Test data to be wrapped."*100,
]

@pytest.mark.parametrize("data", data_samples)
@pytest.mark.parametrize("size", (None, 8, 16))
def test_id(data: bytes, size: Optional[int]) -> None:
    hash_fn = 'identity'
    if size is None or len(data) >= size:
        _test(hash_fn, data, id_digest(data, size), size)

@pytest.mark.parametrize("data", data_samples)
@pytest.mark.parametrize("size", (None, 10, 20))
def test_sha1(data: bytes, size: Optional[int]) -> None:
    hash_fn = 'sha1'
    _test(hash_fn, data, sha1_digest(data, size), size)

@pytest.mark.parametrize("digest_bits", (256, 512))
@pytest.mark.parametrize("data", data_samples)
@pytest.mark.parametrize("size", (None, 16, 32))
def test_sha2(data: bytes, digest_bits: int, size: Optional[int]) -> None:
    hash_fn = f"sha2-{digest_bits}"
    _test(hash_fn, data, sha2_digest(data, digest_bits, size), size)

@pytest.mark.parametrize("digest_bits", (256,))
@pytest.mark.parametrize("data", data_samples)
@pytest.mark.parametrize("size", (None, 16, 32))
def test_dbl_sha2(data: bytes, digest_bits: int, size: Optional[int]) -> None:
    hash_fn = f"dbl-sha2-{digest_bits}"
    _test(hash_fn, data, dbl_sha2_digest(data, digest_bits, size), size)

@pytest.mark.parametrize("digest_bits", (224, 256, 384, 512))
@pytest.mark.parametrize("data", data_samples)
@pytest.mark.parametrize("size", (None, 16, 28))
def test_sha3(data: bytes, digest_bits: int, size: Optional[int]) -> None:
    hash_fn = f"sha3-{digest_bits}"
    _test(hash_fn, data, sha3_digest(data, digest_bits, size), size)

@pytest.mark.parametrize("digest_bits", (224, 256))
@pytest.mark.parametrize("data", data_samples)
@pytest.mark.parametrize("size", (None, 16, 28))
def test_sha2_512(data: bytes, digest_bits: int, size: Optional[int]) -> None:
    hash_fn = f"sha2-512-{digest_bits}"
    _test(hash_fn, data, sha2_512_digest(data, digest_bits, size), size)

@pytest.mark.parametrize("digest_bits", (256, 512))
@pytest.mark.parametrize("data", data_samples)
@pytest.mark.parametrize("size", (None, 16, 32))
def test_shake(data: bytes, digest_bits: int, size: Optional[int]) -> None:
    hash_fn = f"shake-{digest_bits//2}"
    _test(hash_fn, data, shake_digest(data, digest_bits, size), size)

@pytest.mark.parametrize("version", ("b", "s"))
@pytest.mark.parametrize("data", data_samples)
@pytest.mark.parametrize("size", (None, 1))
def test_blake2(data: bytes, version: str, size: Optional[int]) -> None:
    for digest_bits in range(8, (512 if version == "b" else 256)+1, 8):
        hash_fn = f"blake2{version}-{digest_bits}"
        _test(hash_fn, data, blake2_digest(data, version, digest_bits, size), size)

@pytest.mark.parametrize("data", data_samples)
@pytest.mark.parametrize("size", (16, 32, 64))
def test_blake3(data: bytes, size: int) -> None:
    hash_fn = 'blake3'
    _test(hash_fn, data, blake3_digest(data, size), size)

@pytest.mark.parametrize("version", (256, 512, 1024))
@pytest.mark.parametrize("data", data_samples)
@pytest.mark.parametrize("size", (None, 1))
def test_skein(data: bytes, version: int, size: Optional[int]) -> None:
    for digest_bits in range(8, version+1, 8):
        hash_fn = f"skein{version}-{digest_bits}"
        _test(hash_fn, data, skein_digest(data, version, digest_bits, size), size)

@pytest.mark.parametrize("digest_bits", (224, 256, 384, 512))
@pytest.mark.parametrize("data", data_samples)
@pytest.mark.parametrize("size", (None, 16, 28))
def test_keccak(data: bytes, digest_bits: int, size: Optional[int]) -> None:
    hash_fn = f"keccak-{digest_bits}"
    _test(hash_fn, data, keccak_digest(data, digest_bits, size), size)

# @pytest.mark.parametrize("version", ("32", "x64"))
# @pytest.mark.parametrize("data", data_samples)
# @pytest.mark.parametrize("size", (None, 4))
# def test_murmur3(data: bytes, version: str, size: Optional[int]) -> None:
#     if version == "32":
#         hash_fn = f"murmur3-{version}"
#         _test(hash_fn, data, murmur3_digest(data, version, 32, size), size)
#     else:
#         for digest_bits in (64, 128):
#             hash_fn = f"murmur3-{version}-{digest_bits}"
#             _test(hash_fn, data, murmur3_digest(data, version, digest_bits, size), size)

@pytest.mark.parametrize("data", data_samples)
@pytest.mark.parametrize("size", (None, 8, 16))
def test_md5(data: bytes, size: Optional[int]) -> None:
    hash_fn = 'md5'
    _test(hash_fn, data, md5_digest(data, size), size)

@pytest.mark.parametrize("digest_bits", (160, ))
@pytest.mark.parametrize("data", data_samples)
@pytest.mark.parametrize("size", (None, 16, 20))
def test_ripemd(data: bytes, digest_bits: int, size: Optional[int]) -> None:
    hash_fn = f"ripemd-{digest_bits}"
    _test(hash_fn, data, ripemd_digest(data, digest_bits, size), size)

@pytest.mark.parametrize("data", data_samples)
@pytest.mark.parametrize("size", (16, 32, 64))
def test_kangarootwelve(data: bytes, size: int) -> None:
    hash_fn = "kangarootwelve"
    _test(hash_fn, data, kangarootwelve_digest(data, size), size)

@pytest.mark.parametrize("data", data_samples)
@pytest.mark.parametrize("size", (None, 16, 32))
def test_sha_256_trunc254_padded(data: bytes, size: Optional[int]) -> None:
    hash_fn = "sha2-256-trunc254-padded"
    _test(hash_fn, data, sha2_256_trunc254_padded_digest(data, size), size)

# specific test vectors

with importlib_resources.open_text("test", "multihash-test-str-vectors.csv") as csv_table:
    multihash_test_str_vectors = list(csv.DictReader(csv_table))

@pytest.mark.parametrize("test_vector", multihash_test_str_vectors)
def test_str_vectors(test_vector: Dict[str, str]) -> None:
    hash_fn = test_vector["algorithm"]
    digest_size = int(test_vector["bits"])//8
    data = test_vector["input"].encode("utf-8")
    multihash_digest = bytes.fromhex(test_vector["multihash"])
    assert hash_fn == multihash.from_digest(multihash_digest).name
    assert digest(data, hash_fn, size=digest_size) == multihash_digest

with importlib_resources.open_text("test", "multihash-test-hex-vectors.csv") as csv_table:
    multihash_test_hex_vectors = list(csv.DictReader(csv_table))

@pytest.mark.parametrize("test_vector", multihash_test_hex_vectors)
def test_hex_vectors(test_vector: Dict[str, str]) -> None:
    hash_fn = test_vector["algorithm"]
    if hash_fn.startswith("murmur3"):
        return
    digest_size = int(test_vector["bits"])//8
    data = bytes.fromhex(test_vector["input"])
    multihash_digest = bytes.fromhex(test_vector["multihash"])
    assert hash_fn == multihash.from_digest(multihash_digest).name
    assert digest(data, hash_fn, size=digest_size) == multihash_digest
