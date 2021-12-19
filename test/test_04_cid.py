# pylint: disable = missing-docstring

import pytest

from multiformats import varint, multibase, multicodec, multihash, CID

test_data = [
    b"",
    b"Hello world!",
    b"Hello world!"*1024
]

bases = ["base58btc", "base32", "base64pad"]
codecs = ["dag-pb", "raw"]
hashfuns = ["sha2-256", "sha3-512", "skein1024-1024"]

test_cases_v1 = [
    (base, 1, codec, hashfun)
    for base in bases
    for codec in codecs
    for hashfun in hashfuns
]
test_cases_v0 = [
    ("base58btc", 0, "dag-pb", "sha2-256")
]

test_cases = test_cases_v1+test_cases_v0

@pytest.mark.parametrize("base, v, codec, hashfun", test_cases)
@pytest.mark.parametrize("data", test_data)
def test_construct(data: bytes, base: str, v: int, codec: str, hashfun: str) -> None:
    mb = multibase.get(base)
    mc = multicodec.get(codec)
    mh = multihash.get(hashfun)
    digest = multihash.digest(data, hashfun)
    raw_digest = multihash.unwrap(digest)
    cids = [
        CID(base, v, codec, digest),
        CID(base, v, codec, (hashfun, raw_digest)),
        CID(mb, v, mc.code, digest),
        CID(mb, v, mc.code, (mh.code, raw_digest)),
        CID(mb, v, mc, digest),
        CID(mb, v, mc, (mh, raw_digest)),
    ]
    for cid in cids:
        assert cid.base == mb
        assert cid.version == v
        assert cid.codec == mc
        assert cid.hashfun == mh
        assert cid.digest == digest
        assert cid.raw_digest == raw_digest

@pytest.mark.parametrize("base, v, codec, hashfun", test_cases_v1)
@pytest.mark.parametrize("data", test_data)
def test_set(data: bytes, base: str, v: int, codec: str, hashfun: str) -> None:
    digest = multihash.digest(data, hashfun)
    cid = CID(base, v, codec, digest)
    for new_base in ["base58btc", "base32", "base32pad", "base64", "base64pad", "proquint"]:
        for new_codec in ["identity", "dag-pb", "dag-cbor", "raw"]:
            new_cid = cid.set(base=new_base, codec=new_codec)
            assert new_cid.base.name == new_base
            assert new_cid.version == v
            assert new_cid.codec.name == new_codec
            assert new_cid.hashfun.name == hashfun
            assert new_cid.digest == digest

@pytest.mark.parametrize("base, v, codec, hashfun", test_cases)
@pytest.mark.parametrize("data", test_data)
def test_encode_decode(data: bytes, base: str, v: int, codec: str, hashfun: str) -> None:
    mc = multicodec.get(codec)
    digest = multihash.digest(data, hashfun)
    cid = CID(base, v, codec, digest)
    s = cid.encode()
    b = bytes(cid)
    assert s == str(cid)
    if v == 1:
        assert b == varint.encode(v)+varint.encode(mc.code)+digest
    else:
        assert b == digest
    assert cid == CID.decode(s)
    assert cid.set(base="base58btc") == CID.decode(b)
    if v == 1:
        for other_base in ["base58btc", "base32", "base32pad", "base64", "base64pad", "proquint"]:
            assert cid.set(base=other_base) == CID.decode(cid.encode(other_base))

peer_id_test_cases = [
    ("30820122300d06092a864886f70d01010105000382010f003082010a02820101"
    "009a56a5c11e2705d0bfe0cd1fa66d5e519095cc741b62ed99ddf129c32e046e"
    "5ba3958bb8a068b05a95a6a0623cc3c889b1581793cd84a34cc2307e0dd74c70"
    "b4f230c74e5063ecd8e906d372be4eba13f47d04427a717ac78cb12b4b9c2ab5"
    "591f36f98021a70f84d782c36c51819054228ff35a45efa3f82b27849ec89036"
    "26b4a4c4b40f9f74b79caf55253687124c79cb10cd3bc73f0c44fbd341e5417d"
    "2e85e900d22849d2bc85ca6bf037f1f5b4f9759b4b6942fccdf1140b30ea7557"
    "87deb5c373c5953c14d64b523959a76a32a599903974a98cf38d4aaac7e359f8"
    "6b00a91dcf424bf794592139e7097d7e65889259227c07155770276b6eda4cec"
    "370203010001", "RSA"),
    ("1498b5467a63dffa2dc9d9e069caf075d16fc33fdd4c3b01bfadae6433767d93", "Ed25519"),
]

@pytest.mark.parametrize("pk_bytes_hex, algorithm", peer_id_test_cases)
def test_peer_id(pk_bytes_hex: str, algorithm: str) -> None:
    pk_bytes = bytes.fromhex(pk_bytes_hex)
    peer_id = CID.peer_id(pk_bytes_hex)
    assert peer_id == CID.peer_id(pk_bytes)
    assert peer_id.base.name == "base32"
    assert peer_id.version == 1
    assert peer_id.codec.name == "libp2p-key"
    if len(pk_bytes) <= 42:
        hashfun = "identity"
    else:
        hashfun = "sha2-256"
    assert peer_id.hashfun.name == hashfun
    assert peer_id.digest == multihash.digest(pk_bytes, hashfun)
