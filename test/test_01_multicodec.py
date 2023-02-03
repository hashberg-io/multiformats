"""  Tests for the `multiformats.multicodec` module. """

from typing import Dict, List, Union

import pytest

import multiformats_config
from multiformats import multicodec
from multiformats.multicodec import Multicodec

exists_cases = [
    "identity",
    0x00
]

@pytest.mark.parametrize("name_or_code", exists_cases)
def test_exists(name_or_code: Union[str, int]) -> None:
    """ Tests `multicodec.exists`. """
    if isinstance(name_or_code, str):
        assert multicodec.exists(name_or_code)
    else:
        assert multicodec.exists(code=name_or_code)

get_cases = {
    "identity": {
        "name": "identity",
        "code": 0x00,
        "hexcode": "0x00",
        "tag": "multihash",
        "status": "permanent",
        "description": "raw binary",
    }
}

@pytest.mark.parametrize("name, info", get_cases.items())
def test_get(name: str, info: Dict[str, Union[str, int]]) -> None:
    """ Tests `multicodec.get`. """
    m = multicodec.get(name)
    for k, v in info.items():
        assert hasattr(m, k)
        assert getattr(m, k) == v

json_cases = [
    {
        "name": "my-codec",
        "tag": "private",
        "code": "0x300001",
        "status": "draft",
        "description": "my private codec"
    }
]

@pytest.mark.parametrize("m_json", json_cases)
def test_multicodec_contructor(m_json: Dict[str, str]) -> None:
    """ Tests `Multicodec.from_json`. """
    m = Multicodec(**m_json)
    assert m.name == m_json["name"]
    assert m.code == int(m_json["code"], base=16)
    assert m.hexcode == m_json["code"]
    assert m.status == m_json["status"]
    assert m.description == m_json["description"]
    assert str(m) == f"Multicodec({', '.join(f'{k}={repr(v)}' for k, v in m_json.items())})"

@pytest.mark.parametrize("m_json", json_cases)
def test_multicodec_to_json(m_json: Dict[str, str]) -> None:
    """ Tests `Multicodec.to_json`. """
    assert Multicodec(**m_json).to_json() == m_json

@pytest.mark.parametrize("m_json", json_cases)
def test_register(m_json: Dict[str, str]) -> None:
    """ Tests `multicodec.register`. """
    m = Multicodec(**m_json)
    assert not multicodec.exists(m.name)
    assert not multicodec.exists(code=m.code)
    multicodec.register(m)
    assert multicodec.exists(m.name)
    assert multicodec.exists(code=m.code)
    assert multicodec.get(m.name) == multicodec.get(code=m.code) == m

@pytest.mark.parametrize("m_json", json_cases)
def test_unregister(m_json: Dict[str, str]) -> None:
    """ Tests `multicodec.get`. """
    m = Multicodec(**m_json)
    assert multicodec.exists(m.name)
    assert multicodec.exists(code=m.code)
    m2_json = {
        **m_json,
        "name": m_json["name"]+"-2",
        "code": hex(int(m_json["code"], base=16)+1)
    }
    m2 = Multicodec(**m2_json)
    assert not multicodec.exists(m2.name)
    assert not multicodec.exists(code=m2.code)
    multicodec.register(m2)
    multicodec.unregister(m.name)
    assert not multicodec.exists(m.name)
    assert not multicodec.exists(code=m.code)
    multicodec.unregister(code=m2.code)
    assert not multicodec.exists(m2.name)
    assert not multicodec.exists(code=m2.code)

table_cases = [
    (None, None, "identity", 0x00),
    ("multihash", None, "identity", 0x00),
    (["private", "multiaddr"], None, "ip4", 0x04),
    ("multiaddr", "permanent", "ip4", 0x04),
    (["private", "multiaddr"], ["draft", "permanent"], "ip4", 0x04),
    (None, "draft", "cidv2", 0x02),
]

@pytest.mark.parametrize("tag, status, name, code", table_cases)
def test_table(tag: Union[None, str, List[str]], status: Union[None, str, List[str]], name: str, code: int) -> None:
    """ Tests `multicodec.table`. """
    m = next(multicodec.table(tag=tag, status=status))
    assert m.name == name and m.code == code

table_failure_cases = [
    [[
        Multicodec(name="identity", tag="multihash", code=0x00, status="permanent", description="raw binary"),
        Multicodec(name="my-codec", tag="private", code=0x300001, status="draft", description="my private codec"),
    ], "Private use codes not allowed.", True],
    [[
            Multicodec(name="identity", tag="multihash", code=0x00, status="permanent", description="raw binary"),
            Multicodec(name="my-codec", tag="private", code=0x00, status="permanent", description="my private codec"),
    ], "Repeated permanent codes not allowed.", True],
    [[
            Multicodec(name="identity", tag="multihash", code=0x00, status="permanent", description="raw binary"),
            Multicodec(name="my-codec", tag="private", code=0x00, status="draft", description="my private codec"),
    ], "Repeated codes allowed if exactly one is permanent.", False],
    [[
            Multicodec(name="identity", tag="multihash", code=0x00, status="draft", description="raw binary"),
            Multicodec(name="my-codec", tag="private", code=0x00, status="permanent", description="my private codec"),
    ], "Repeated codes allowed if exactly one is permanent.", False],
    [[
            Multicodec(name="identity", tag="multihash", code=0x00, status="draft", description="raw binary"),
            Multicodec(name="my-codec", tag="private", code=0x00, status="draft", description="my private codec"),
    ], "Repeated codes allowed if exactly one is permanent.", True],
    [[
            Multicodec(name="identity", tag="multihash", code=0x00, status="permanent", description="raw binary"),
            Multicodec(name="identity", tag="private", code=0x01, status="draft", description="my private codec"),
    ], "Repeated names not allowed.", True],
]

@pytest.mark.parametrize("multicodecs, reason, fails", table_failure_cases)
def test_table_failure_modes(multicodecs: List[Multicodec], reason: str, fails: bool) -> None:
    """ Tests failure modes for codec table building. """
    try:
        multiformats_config.multicodec.build_multicodec_tables(multicodecs)
        assert not fails, reason
    except ValueError:
        assert fails, reason

# TODO: make api test parametrised

def test_api_failure_modes() -> None:
    """ Tests failure modes for the multicode API. """
    try:
        Multicodec(name="3my-codec", tag="private", code=0x00, status="draft", description="my private codec")
        assert False, "This name should not be valid."
    except ValueError:
        pass
    try:
        Multicodec(name="my-codec", tag="private", code=0x00, status="other", description="my private codec")
        assert False, "Status must be 'permanent' or 'draft'."
    except ValueError:
        pass
    try:
        Multicodec(name="my-codec", tag="private", code=-1, status="draft", description="my private codec")
        assert False, "Code must be non-negative."
    except ValueError:
        pass
    try:
        multicodec.get("my-codec")
        assert False, "Codec 'my-codec' should not exist."
    except KeyError:
        pass
    try:
        multicodec.get(code=0x300001)
        assert False, "Codec 0x300001 should not exist."
    except KeyError:
        pass
    try:
        m = Multicodec(name="identity", tag="multihash", code=0x300003, status="permanent", description="")
        multicodec.register(m)
        assert False, "Codec name 'identity' already exists."
    except ValueError:
        pass
    try:
        m = Multicodec(name="my-codec", tag="multihash", code=0x00, status="permanent", description="")
        multicodec.register(m)
        assert False, "Codec with code 0x00 already exists."
    except ValueError:
        pass
