# pylint: disable = missing-docstring

import csv
import hashlib
import importlib.resources as importlib_resources
from typing import Dict

import pytest
import skein  # type: ignore

from multiformats import multihash
from multiformats.multihash import encode, digest, decode

def id_digest(data: bytes) -> bytes:
    return data

def sha1_digest(data: bytes) -> bytes:
    m = hashlib.sha1()
    m.update(data)
    return m.digest()

def sha2_digest(data: bytes, digest_bits: int) -> bytes:
    m: hashlib._Hash = getattr(hashlib, f"sha{digest_bits}")()
    m.update(data)
    return m.digest()

def sha3_digest(data: bytes, digest_bits: int) -> bytes:
    m: hashlib._Hash = getattr(hashlib, f"sha3_{digest_bits}")()
    m.update(data)
    return m.digest()

def shake_digest(data: bytes, digest_bits: int) -> bytes:
    m: hashlib._Hash = getattr(hashlib, f'shake_{digest_bits//2}')()
    m.update(data)
    return m.digest(digest_bits//8) # type: ignore

def blake2_digest(data: bytes, variant: str, digest_bits: int) -> bytes:
    assert variant in ('b', 's')
    m: hashlib._Hash = getattr(hashlib, 'blake2{}'.format(variant))(digest_size=digest_bits//8)
    m.update(data)
    return m.digest()

def skein_digest(data: bytes, variant: int, digest_bits: int) -> bytes:
    assert variant in (256, 512, 1024)
    m: hashlib._Hash = getattr(skein, 'skein{}'.format(variant))(digest_bits=digest_bits)
    m.update(data)
    return m.digest()

def _test(hash_fn: str, data: bytes, hash_digest: bytes) -> None:
    multihash_digest = digest(data, hash_fn)
    assert multihash.exists(hash_fn)
    codec = multihash.get(hash_fn)
    assert hash_fn == codec.name
    assert codec == multihash.from_digest(multihash_digest)
    assert encode(hash_digest, hash_fn) == multihash_digest
    assert hash_digest == decode(multihash_digest)
    assert hash_digest == decode(multihash_digest, hash_fn)
    trunc_hash_digest = hash_digest[:len(hash_digest)//2]
    trunc_multihash_digest = encode(trunc_hash_digest, hash_fn)
    assert trunc_hash_digest == decode(trunc_multihash_digest)
    assert trunc_hash_digest == decode(trunc_multihash_digest, hash_fn)
    multihash_digest = digest(bytearray(data), hash_fn)
    assert encode(bytearray(hash_digest), hash_fn) == multihash_digest
    assert hash_digest == decode(bytearray(multihash_digest))
    multihash_digest = digest(memoryview(data), hash_fn)
    assert encode(memoryview(hash_digest), hash_fn) == multihash_digest
    assert hash_digest == decode(memoryview(multihash_digest))

data = b"Test data to be encoded."

def test_id() -> None:
    hash_fn = 'identity'
    _test(hash_fn, data, id_digest(data))

def test_sha1() -> None:
    hash_fn = 'sha1'
    _test(hash_fn, data, sha1_digest(data))

@pytest.mark.parametrize("digest_bits", (256, 512))
def test_sha2(digest_bits: int) -> None:
    hash_fn = f"sha2-{digest_bits}"
    _test(hash_fn, data, sha2_digest(data, digest_bits))

@pytest.mark.parametrize("digest_bits", (224, 256, 384, 512))
def test_sha3(digest_bits: int) -> None:
    hash_fn = f"sha3-{digest_bits}"
    _test(hash_fn, data, sha3_digest(data, digest_bits))

@pytest.mark.parametrize("digest_bits", (256, 512))
def test_shake(digest_bits: int) -> None:
    hash_fn = f"shake-{digest_bits//2}"
    _test(hash_fn, data, shake_digest(data, digest_bits))

@pytest.mark.parametrize("version", ("b", "s"))
def test_blake2(version: str) -> None:
    for digest_bits in range(8, (512 if version == "b" else 256)+1, 8):
        hash_fn = f"blake2{version}-{digest_bits}"
        _test(hash_fn, data, blake2_digest(data, version, digest_bits))

@pytest.mark.parametrize("version", (256, 512, 1024))
def test_skein(version: int) -> None:
    for digest_bits in range(8, version+1, 8):
        hash_fn = f"skein{version}-{digest_bits}"
        _test(hash_fn, data, skein_digest(data, version, digest_bits))

with importlib_resources.open_text("test", "multihash-test-vectors.csv") as csv_table:
    multihash_test_vectors = list(csv.DictReader(csv_table))

# with open("multihash_test_vectors.csv") as f:
#     multihash_test_vectors = list(csv.DictReader(f))

def test_vectors() -> None:
    for test_vector in multihash_test_vectors:
        hash_fn = test_vector["algorithm"]
        digest_size = int(test_vector["bits"])//8
        data = test_vector["input"].encode("utf-8")
        multihash_digest = bytes.fromhex(test_vector["multihash"])
        assert hash_fn == multihash.from_digest(multihash_digest).name
        assert digest(data, hash_fn, size=digest_size) == multihash_digest
