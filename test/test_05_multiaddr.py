# pylint: disable = missing-docstring

from random import Random
import sys
from typing import List, Union

import pytest

from multiformats import multicodec, multiaddr
from multiformats.multicodec import Multicodec
from multiformats.multicodec.err import MulticodecKeyError
from multiformats.multiaddr import Proto, Addr, Multiaddr
from multiformats.multiaddr.err import MultiaddrKeyError, MultiaddrValueError


implemented_protocols: List[Proto] = []

@pytest.mark.parametrize("multicodec", multicodec.table(tag="multiaddr"))
def test_implemented_protos(multicodec: Multicodec) -> None:
    name = multicodec.name
    if multiaddr.raw.exists(name):
        implemented_protocols.append(Proto(name))

invalid_multiaddr_strings = [
    "/ip4",
    "/ip4/::1",
    "/ip4/fdpsofodsajfdoisa",
    "/ip6",
    "/ip6zone",
    "/ip6zone/",
    "/ip6zone//ip6/fe80::1",
    "/udp",
    "/tcp",
    "/sctp",
    "/udp/65536",
    "/tcp/65536",
    "/onion/9imaq4ygg2iegci7:80",
    "/onion/aaimaq4ygg2iegci7:80",
    "/onion/timaq4ygg2iegci7:0",
    "/onion/timaq4ygg2iegci7:-1",
    "/onion/timaq4ygg2iegci7",
    "/onion/timaq4ygg2iegci@:666",
    "/onion3/9ww6ybal4bd7szmgncyruucpgfkqahzddi37ktceo3ah7ngmcopnpyyd:80",
    "/onion3/vww6ybal4bd7szmgncyruucpgfkqahzddi37ktceo3ah7ngmcopnpyyd7:80",
    "/onion3/vww6ybal4bd7szmgncyruucpgfkqahzddi37ktceo3ah7ngmcopnpyyd:0",
    "/onion3/vww6ybal4bd7szmgncyruucpgfkqahzddi37ktceo3ah7ngmcopnpyyd:a",
    "/onion3/vww6ybal4bd7szmgncyruucpgfkqahzddi37ktceo3ah7ngmcopnpyyd:-1",
    "/onion3/vww6ybal4bd7szmgncyruucpgfkqahzddi37ktceo3ah7ngmcopnpyyd",
    "/onion3/vww6ybal4bd7szmgncyruucpgfkqahzddi37ktceo3ah7ngmcopnpyy@:666",
    "/udp/1234/sctp",
    "/udp/1234/udt/1234",
    "/udp/1234/utp/1234",
    "/ip4/127.0.0.1/udp/jfodsajfidosajfoidsa",
    "/ip4/127.0.0.1/udp",
    "/ip4/127.0.0.1/tcp/jfodsajfidosajfoidsa",
    "/ip4/127.0.0.1/tcp",
    "/ip4/127.0.0.1/p2p",
    "/ip4/127.0.0.1/p2p/tcp",
    "/unix",
    "/ip4/1.2.3.4/tcp/80/unix",
    "/ip4/127.0.0.1/tcp/9090/http/p2p-webcrt-direct",
    "/dns",
    "/dns4",
    "/dns6"
]

@pytest.mark.parametrize("multiaddr_str", invalid_multiaddr_strings)
def test_invalid_parse(multiaddr_str: str) -> None:
    try:
        multiaddr.parse(multiaddr_str)
        assert False
    except MultiaddrValueError: # invalid string
        pass
    except MultiaddrKeyError: # protocol not implemented
        pass
    except MulticodecKeyError: # protocol does not exist
        pass

valid_multiaddr_strings = [
    "/ip4/1.2.3.4",
    "/ip4/0.0.0.0",
    "/ip6/::1",
    "/ip6/2601:9:4f81:9700:803e:ca65:66e8:c21",
    "/ip6zone/x/ip6/fe80::1",
    "/ip6zone/x%y/ip6/fe80::1",
    "/ip6zone/x%y/ip6/::",
    "/onion/timaq4ygg2iegci7:1234",
    "/onion/timaq4ygg2iegci7:80/http",
    "/onion3/vww6ybal4bd7szmgncyruucpgfkqahzddi37ktceo3ah7ngmcopnpyyd:1234",
    "/onion3/vww6ybal4bd7szmgncyruucpgfkqahzddi37ktceo3ah7ngmcopnpyyd:80/http",
    "/udp/0",
    "/tcp/0",
    "/sctp/0",
    "/udp/1234",
    "/tcp/1234",
    "/sctp/1234",
    "/utp",
    "/udp/65535",
    "/tcp/65535",
    "/p2p/QmcgpsyWgH8Y8ajJz1Cu72KnS5uo2Aa2LpzU7kinSupNKC",
    "/udp/1234/sctp/1234",
    "/udp/1234/udt",
    "/udp/1234/utp",
    "/tcp/1234/http",
    "/tcp/1234/https",
    "/p2p/QmcgpsyWgH8Y8ajJz1Cu72KnS5uo2Aa2LpzU7kinSupNKC/tcp/1234",
    "/ip4/127.0.0.1/udp/1234",
    "/ip4/127.0.0.1/p2p/QmcgpsyWgH8Y8ajJz1Cu72KnS5uo2Aa2LpzU7kinSupNKC/tcp/1234",
    "/unix/a/b/c/d/e",
    "/unix/Überrschung!/大柱",
    "/unix/stdio",
    "/ip4/1.2.3.4/tcp/80/unix/a/b/c/d/e/f",
    "/ip4/127.0.0.1/p2p/QmcgpsyWgH8Y8ajJz1Cu72KnS5uo2Aa2LpzU7kinSupNKC"
    "/tcp/1234/unix/stdio",
    "/ip4/127.0.0.1/tcp/9090/http/p2p-webrtc-direct",
    "/dns/example.com",
    "/dns4/موقع.وزارة-الاتصالات.مصر"
]

@pytest.mark.parametrize("multiaddr_str", valid_multiaddr_strings)
def test_valid_parse(multiaddr_str: str) -> None:
    try:
        multiaddr.parse(multiaddr_str)
    except multiaddr.err.MultiaddrKeyError: # protocol not implemented
        pass

@pytest.mark.parametrize("multiaddr_str", valid_multiaddr_strings)
def test_parse_str(multiaddr_str: str) -> None:
    try:
        ma = multiaddr.parse(multiaddr_str)
        str(ma)
        assert str(ma) == multiaddr_str
    except multiaddr.err.MultiaddrKeyError: # protocol not implemented
        pass

@pytest.mark.parametrize("multiaddr_str", valid_multiaddr_strings)
def test_bytes_decode(multiaddr_str: str) -> None:
    try:
        ma = multiaddr.parse(multiaddr_str)
        bytes(ma)
        assert ma == multiaddr.decode(bytes(ma))
    except multiaddr.err.MultiaddrKeyError: # protocol not implemented
        pass

rand = Random(0)
num_attempts = 10

def random_addr(proto: Proto) -> Union[Proto, Addr]:
    addr_size = proto.addr_size
    if addr_size == 0:
        return proto
    for _ in range(num_attempts):
        if addr_size is None:
            addr_size = rand.randint(1, 8)
        if sys.version_info[1] >= 9:
            addr_bytes = rand.randbytes(addr_size)
        else:
            addr_bytes = rand.getrandbits(addr_size*8).to_bytes(addr_size, byteorder="big")
        if not proto.is_addr_valid(addr_bytes):
            with pytest.raises(multiaddr.err.MultiaddrValueError):
                proto/addr_bytes # pylint: disable = pointless-statement
            continue
        return proto/addr_bytes
    raise RuntimeError(f"Could not generate a valid random address for protocol {repr(proto.name)}")

def random_multiaddr(use_slash: bool = False, maxlen: int = 4) -> Multiaddr:
    assert maxlen >= 1
    l = rand.randint(1, maxlen)
    protos = rand.sample(implemented_protocols, l)
    addrs = []
    for idx in range(l):
        addrs.append(random_addr(protos[idx]))
    if not use_slash:
        return Multiaddr(*addrs)
    a = Multiaddr(addrs[0])
    for idx in range(1, l):
        a = a/addrs[idx]
    return a

@pytest.mark.parametrize("sample", range(40))
@pytest.mark.parametrize("use_slash", [False, True])
def test_random(sample: int, use_slash: bool) -> None:
    ma = random_multiaddr(use_slash=use_slash)
    str(ma)
    assert ma == multiaddr.parse(str(ma))
    bytes(ma)
    assert ma == multiaddr.decode(bytes(ma))
