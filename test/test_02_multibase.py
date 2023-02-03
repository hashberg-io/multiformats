"""  Tests for the `multiformats.multibase` module. """
# pylint: disable = missing-docstring

# import pytest
# TODO: make tests parametrised

from random import Random

import multiformats_config
from multiformats import multibase
from multiformats.multibase import Multibase


def test_exists() -> None:
    """ Tests `multibase.exists`. """
    assert multibase.exists("identity")
    assert multibase.exists(code="\x00")

def test_get() -> None:
    """ Tests `multibase.get`. """
    enc = multibase.get("base16")
    assert enc.name == "base16"
    assert enc.code == "f"
    assert enc.status == "default"
    assert enc.description == "hexadecimal"

def test_multibase_contructor() -> None:
    """ Tests `Multibase.from_json`. """
    m_json = {
        "name": "my-codec",
        "code": "W",
        "status": "draft",
        "description": "my private codec"
    }
    enc = Multibase(**m_json)
    assert enc.name == m_json["name"]
    assert enc.code == "W"
    assert enc.status == m_json["status"]
    assert enc.description == m_json["description"]
    assert str(enc) == f"Multibase({', '.join(f'{k}={repr(v)}' for k, v in m_json.items())})"
    m_json = {
        "name": "my-codec",
        "code": "0x02",
        "status": "draft",
        "description": "my private codec"
    }
    enc = Multibase(**m_json)
    assert enc.name == m_json["name"]
    assert enc.code == "\x02"
    assert enc.status == m_json["status"]
    assert enc.description == m_json["description"]
    assert str(enc) == f"Multibase({', '.join(f'{k}={repr(v)}' for k, v in m_json.items())})"


def test_multibase_to_json() -> None:
    """ Tests `Multibase.to_json`. """
    m_json = {
        "name": "my-codec",
        "code": "W",
        "status": "draft",
        "description": "my private codec"
    }
    assert Multibase(**m_json).to_json() == m_json
    m_json = {
        "name": "my-codec",
        "code": "0x02",
        "status": "draft",
        "description": "my private codec"
    }
    assert Multibase(**m_json).to_json() == m_json

def test_register() -> None:
    """ Tests `multibase.register`. """
    m_json = {
        "name": "my-codec",
        "code": "W",
        "status": "draft",
        "description": "my private codec"
    }
    enc = Multibase(**m_json)
    assert not multibase.exists(enc.name)
    assert not multibase.exists(code=enc.code)
    multibase.register(enc)
    assert multibase.exists(enc.name)
    assert multibase.exists(code=enc.code)
    assert multibase.get(enc.name) == multibase.get(code=enc.code) == enc

def test_unregister() -> None:
    """ Tests `multibase.get`. """
    m_json = {
        "name": "my-codec",
        "code": "W",
        "status": "draft",
        "description": "my private codec"
    }
    enc = Multibase(**m_json)
    assert multibase.exists(enc.name)
    assert multibase.exists(code=enc.code)
    m2_json = {
        "name": "my-codec-2",
        "code": "0x02",
        "status": "draft",
        "description": "my second private codec"
    }
    m2 = Multibase(**m2_json)
    assert not multibase.exists(m2.name)
    assert not multibase.exists(code=m2.code)
    multibase.register(m2)
    multibase.unregister(enc.name)
    assert not multibase.exists(enc.name)
    assert not multibase.exists(code=enc.code)
    multibase.unregister(code=m2.code)
    assert not multibase.exists(m2.name)
    assert not multibase.exists(code=m2.code)

def test_table() -> None:
    """ Tests `multibase.table`. """
    try:
        enc = next(multibase.table())
        assert enc.name == "identity" and enc.code_printable == "0x00"
    except StopIteration:
        assert False, "At least one multibase exists."
    try:
        multibases = [
            Multibase(name="identity", code="0x00", status="default", description=""),
            Multibase(name="my-codec", code="0x00", status="draft", description=""),
        ]
        multiformats_config.multibase.build_multibase_tables(multibases)
        assert False, "Repeated codes not allowed."
    except ValueError:
        pass
    try:
        multibases = [
            Multibase(name="identity", code="0x00", status="default", description=""),
            Multibase(name="identity", code="0x01", status="draft", description=""),
        ]
        print(multiformats_config.multibase.build_multibase_tables(multibases))
        assert False, "Repeated names not allowed."
    except ValueError:
        pass

def test_api_failure_modes() -> None:
    """ Tests failure modes for the multicode API. """
    # pylint: disable = too-many-statements
    try:
        Multibase(name="3my-codec", code="0x00")
        assert False, "This name should not be valid."
    except ValueError:
        pass
    try:
        Multibase(name="my-codec", code="0x00", status="other")
        assert False, "Status must be 'draft', 'candidate' or 'default'."
    except ValueError:
        pass
    try:
        Multibase(name="my-codec", code="0x79")
        assert False, "Codes in hex format must be non-printable ASCII characters."
    except ValueError:
        pass
    try:
        Multibase(name="3my-codec", code="0x20")
        assert False, "Codes in hex format must be non-printable ASCII characters."
    except ValueError:
        pass
    try:
        Multibase(name="3my-codec", code="\x00")
        assert False, "Codes in single-character format must be printable ASCII characters."
    except ValueError:
        pass
    try:
        Multibase(name="3my-codec", code="\x80")
        assert False, "Codes in single-character format must be printable ASCII characters."
    except ValueError:
        pass
    try:
        Multibase(name="3my-codec", code="\x7F")
        assert False, "Codes in single-character format must be printable ASCII characters."
    except ValueError:
        pass
    try:
        multibase.get("my-codec")
        assert False, "Multibase 'my-codec' should not exist."
    except KeyError:
        pass
    try:
        multibase.get(code='\x08')
        assert False, "Multibase with code 'W' should not exist."
    except KeyError:
        pass
    try:
        enc = Multibase(name="identity", code="0x01", status="default")
        multibase.register(enc)
        assert False, "Multibase name 'identity' already exists."
    except ValueError:
        pass
    try:
        enc = Multibase(name="my-codec", code="\x00", status="draft")
        multibase.register(enc)
        assert False, "Codec with code 0x00 already exists."
    except ValueError:
        pass

rand = Random(0)
nsamples = 1024

_proquints = {
    bytes([127, 0, 0, 1]): "lusab-babad",
    bytes([63, 84, 220, 193]): "gutih-tugad",
    bytes([63, 118, 7, 35]): "gutuk-bisog",
    bytes([140, 98, 193, 141]): "mudof-sakat",
    bytes([64, 255, 6, 200]): "haguz-biram",
    bytes([128, 30, 52, 45]): "mabiv-gibot",
    bytes([147, 67, 119, 2]): "natag-lisaf",
    bytes([212, 58, 253, 68]): "tibup-zujah",
    bytes([216, 35, 68, 215]): "tobog-higil",
    bytes([216, 68, 232, 21]): "todah-vobij",
    bytes([198, 81, 129, 136]): "sinid-makam",
    bytes([12, 110, 110, 204]): "budov-kuras",
}
for b, s in list(_proquints.items()):
    _proquints[b[:2]] = s[:5]
    _proquints[b[2:]] = s[6:]

def test_proquint() -> None:
    proquint = multibase.get("proquint")
    for b, s in _proquints.items():
        s = 'pro-'+s
        error_msg = f"Proquint encode error at b = {list(b)}, s = {repr(s)}"
        assert proquint.encode(b) == s
        error_msg = f"Proquint decode error at b = {list(b)}, s = {repr(s)}"
        assert proquint.decode(s) == b
    assert proquint.encode(b"") == "pro-"
    assert proquint.decode("pro-") == b""
    for idx in range(nsamples):
        l = rand.randint(1, 5)
        i = rand.randrange(0, 256**l)
        b = i.to_bytes(l, byteorder="big")
        s = proquint.encode(b)
        error_msg = f"Proquint decode-encode error at sample #{idx}: b = {list(b)}, s = {repr(s)}"
        assert proquint.decode(s) == b, error_msg
