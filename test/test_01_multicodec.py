"""  Tests for the `multiformats.multicodec` module. """

from multiformats import multicodec
from multiformats.multicodec import Multicodec

def test_exists() -> None:
    """ Tests `multicodec.exists`. """
    assert multicodec.exists("identity")
    assert multicodec.exists(code=0x00)

def test_get() -> None:
    """ Tests `multicodec.get`. """
    m = multicodec.get("identity")
    assert m.name == "identity"
    assert m.code == 0x00
    assert m.hexcode == "0x00"
    assert m.tag == "multihash"
    assert m.status == "permanent"
    assert m.description == "raw binary"

def test_multicodec_contructor() -> None:
    """ Tests `Multicodec.from_json`. """
    m_json = {
        "name": "my-codec",
        "tag": "private",
        "code": "0x300001",
        "status": "draft",
        "description": "my private codec"
    }
    m = Multicodec(**m_json)
    assert m.name == m_json["name"]
    assert m.code == int(m_json["code"], base=16)
    assert m.hexcode == m_json["code"]
    assert m.status == m_json["status"]
    assert m.description == m_json["description"]
    assert str(m) == f"Multicodec({', '.join(f'{k}={repr(v)}' for k, v in m_json.items())})"

def test_multicodec_to_json() -> None:
    """ Tests `Multicodec.to_json`. """
    m_json = {
        "name": "my-codec",
        "tag": "private",
        "code": "0x300001",
        "status": "draft",
        "description": "my private codec"
    }
    assert Multicodec(**m_json).to_json() == m_json

def test_register() -> None:
    """ Tests `multicodec.register`. """
    m_json = {
        "name": "my-codec",
        "tag": "private",
        "code": "0x300001",
        "status": "draft",
        "description": "my private codec"
    }
    m = Multicodec(**m_json)
    assert not multicodec.exists(m.name)
    assert not multicodec.exists(code=m.code)
    multicodec.register(m)
    assert multicodec.exists(m.name)
    assert multicodec.exists(code=m.code)
    assert multicodec.get(m.name) == multicodec.get(code=m.code) == m

def test_unregister() -> None:
    """ Tests `multicodec.get`. """
    m_json = {
        "name": "my-codec",
        "tag": "private",
        "code": "0x300001",
        "status": "draft",
        "description": "my private codec"
    }
    m = Multicodec(**m_json)
    assert multicodec.exists(m.name)
    assert multicodec.exists(code=m.code)
    m2_json = {
        "name": "my-codec-2",
        "tag": "private",
        "code": "0x300002",
        "status": "draft",
        "description": "my second private codec"
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

def test_table() -> None:
    """ Tests `multicodec.table`. """
    try:
        m = next(multicodec.table())
        assert m.name == "identity" and m.code == 0x00
    except StopIteration:
        assert False, "At least one multicodec exists."
    try:
        m = next(multicodec.table(tag="multihash"))
        assert m.name == "identity" and m.code == 0x00
    except StopIteration:
        assert False, "At least one 'multihash' tagged multicodec exists."
    try:
        m = next(multicodec.table(tag=["private", "multiaddr"]))
        assert m.name == "ip4" and m.code == 0x04
    except StopIteration:
        assert False, "At least one 'multiaddr' tagged multicodec exists."
    try:
        m = next(multicodec.table(tag="multiaddr", status="permanent"))
        assert m.name == "ip4" and m.code == 0x04
    except StopIteration:
        assert False, "At least one 'permanent' and 'multiaddr' status multicodec exists."
    try:
        m = next(multicodec.table(tag=["private", "multiaddr"], status=["draft", "permanent"]))
        assert m.name == "ip4" and m.code == 0x04
    except StopIteration:
        assert False, "At least one 'multiaddr' tagged multicodec exists."
    try:
        m = next(multicodec.table(status="draft"))
        assert m.name == "cidv2" and m.code == 0x02
    except StopIteration:
        assert False, "At least one 'draft' status multicodec exists."

def test_table_failure_modes() -> None:
    """ Tests failure modes for codec table building. """
    try:
        multicodecs = [
            Multicodec(name="identity", tag="multihash", code=0x00, status="permanent", description="raw binary"),
            Multicodec(name="my-codec", tag="private", code=0x300001, status="draft", description="my private codec"),
        ]
        multicodec.build_multicodec_tables(multicodecs)
        assert False, "Private use codes not allowed."
    except ValueError:
        pass
    try:
        multicodecs = [
            Multicodec(name="identity", tag="multihash", code=0x00, status="permanent", description="raw binary"),
            Multicodec(name="my-codec", tag="private", code=0x00, status="permanent", description="my private codec"),
        ]
        multicodec.build_multicodec_tables(multicodecs)
        assert False, "Repeated permanent codes not allowed."
    except ValueError:
        pass
    try:
        multicodecs = [
            Multicodec(name="identity", tag="multihash", code=0x00, status="permanent", description="raw binary"),
            Multicodec(name="my-codec", tag="private", code=0x00, status="draft", description="my private codec"),
        ]
        multicodec.build_multicodec_tables(multicodecs)
    except ValueError:
        assert False, "Repeated codes allowed if exactly one is permanent."
    try:
        multicodecs = [
            Multicodec(name="identity", tag="multihash", code=0x00, status="draft", description="raw binary"),
            Multicodec(name="my-codec", tag="private", code=0x00, status="permanent", description="my private codec"),
        ]
        multicodec.build_multicodec_tables(multicodecs)
    except ValueError:
        assert False, "Repeated codes allowed if exactly one is permanent."
    try:
        multicodecs = [
            Multicodec(name="identity", tag="multihash", code=0x00, status="draft", description="raw binary"),
            Multicodec(name="my-codec", tag="private", code=0x00, status="draft", description="my private codec"),
        ]
        multicodec.build_multicodec_tables(multicodecs)
        assert False, "Repeated codes allowed if exactly one is permanent."
    except ValueError:
        pass
    try:
        multicodecs = [
            Multicodec(name="identity", tag="multihash", code=0x00, status="permanent", description="raw binary"),
            Multicodec(name="identity", tag="private", code=0x01, status="draft", description="my private codec"),
        ]
        print(multicodec.build_multicodec_tables(multicodecs))
        assert False, "Repeated names not allowed."
    except ValueError:
        pass

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
