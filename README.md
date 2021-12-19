# `multiformats`: A Python implementation of [multiformat protocols](https://multiformats.io/)

[![Generic badge](https://img.shields.io/badge/python-3.7+-green.svg)](https://docs.python.org/3.7/)
![PyPI version shields.io](https://img.shields.io/pypi/v/multiformats.svg)
[![PyPI status](https://img.shields.io/pypi/status/multiformats.svg)](https://pypi.python.org/pypi/multiformats/)
[![Checked with Mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](https://github.com/python/mypy)
[![Python package](https://github.com/hashberg-io/multiformats/actions/workflows/python-pytest.yml/badge.svg)](https://github.com/hashberg-io/multiformats/actions/workflows/python-pytest.yml)
[![standard-readme compliant](https://img.shields.io/badge/readme%20style-standard-brightgreen.svg?style=flat-square)](https://github.com/RichardLitt/standard-readme)


This is a fully compliant Python implementation of the [multiformat protocols](https://multiformats.io/).


## Table of Contents

- [Install](#install)
- [Usage](#usage)
    - [Varint](#varint)
    - [Multicodec](#multicodec)
    - [Multibase](#multibase)
    - [Multihash](#multihash)
    - [CID](#cid)
    - [Multiaddr](#multiaddr)
- [API](#api)
- [Contributing](#contributing)
- [License](#license)


## Install

You can install the latest release from PyPI as follows:

```
pip install --upgrade multiformats
```

## Usage

### Varint

The [`varint`](https://hashberg-io.github.io/multiformats/multiformats/varint.html) module implements the [unsigned-varint spec](https://github.com/multiformats/unsigned-varint). Functionality is provided by the [`encode`](https://hashberg-io.github.io/multiformats/multiformats/varint.html#multiformats.varint.encode) and [`decode`](https://hashberg-io.github.io/multiformats/multiformats/varint.html#multiformats.varint.encode) functions, converting between non-negative `int` values and the corresponding varint `bytes`: 

```py
>>> from multiformats import varint
>>> varint.encode(128)
b'\x80\x01'
>>> varint.decode(b'\x80\x01')
128
```

For advanced usage, see the [API documentation](https://hashberg-io.github.io/multiformats/multiformats/varint.html). 


### Multicodec

The [`multicodec`](https://hashberg-io.github.io/multiformats/multiformats/multicodec/index.html) module implements the [multicodec spec](https://github.com/multiformats/multicodec). The [`Multicodec`](https://hashberg-io.github.io/multiformats/multiformats/multicodec/index.html#multiformats.multicodec.Multicodec) class provides a container for multicodec data:

```py
>>> Multicodec("identity", "multihash", 0x00, "permanent", "raw binary")
Multicodec(name='identity', tag='multihash', code=0,
           status='permanent', description='raw binary')
```

Core functionality is provided by the [`get`](https://hashberg-io.github.io/multiformats/multiformats/multicodec/index.html#multiformats.multicodec.get), [`exists`](https://hashberg-io.github.io/multiformats/multiformats/multicodec/index.html#multiformats.multicodec.exists), [`wrap`](https://hashberg-io.github.io/multiformats/multiformats/multicodec/index.html#multiformats.multicodec.wrap) and [`unwrap`](https://hashberg-io.github.io/multiformats/multiformats/multicodec/index.html#multiformats.multicodec.unwrap) functions.
The [`get`](https://hashberg-io.github.io/multiformats/multiformats/multicodec/index.html#multiformats.multicodec.get) and [`exists`](https://hashberg-io.github.io/multiformats/multiformats/multicodec/index.html#multiformats.multicodec.exists) functions can be used to check whether a multicodec with given name or code is known,
and if so to get the corresponding object:

```py
>>> multicodec.exists("identity")
True
>>> multicodec.exists(code=0x01)
True
>>> multicodec.get("identity")
Multicodec(name='identity', tag='multihash', code=0,
           status='permanent', description='raw binary')
>>> multicodec.get(code=0x01)
Multicodec(name='cidv1', tag='cid', code=1,
           status='permanent', description='CIDv1')
```

The [`wrap`](https://hashberg-io.github.io/multiformats/multiformats/multicodec/index.html#multiformats.multicodec.wrap) and [`unwrap`](https://hashberg-io.github.io/multiformats/multiformats/multicodec/index.html#multiformats.multicodec.unwrap) functions can be use to wrap raw binary data into multicodec data
(prepending the varint-encoded multicodec code) and to unwrap multicodec data into a pair
of multicodec code and raw binary data:

```py
>>> raw_data = bytes([192, 168, 0, 254])
>>> multicodec_data = wrap("ip4", raw_data)
>>> raw_data.hex()
  'c0a800fe'
>>> multicodec_data.hex()
'04c0a800fe'
>>> varint.encode(0x04).hex()
'04' #       0x04 ^^^^ is the multicodec code for 'ip4'
>>> codec, raw_data = unwrap(multicodec_data)
>>> raw_data.hex()
  'c0a800fe'
>>> codec
Multicodec(name='ip4', tag='multiaddr', code='0x04', status='permanent', description='')
```

The [`Multicodec.wrap`](https://hashberg-io.github.io/multiformats/multiformats/multicodec/index.html#multiformats.multicodec.Multicodec.wrap) and [`Multicodec.unwrap`](https://hashberg-io.github.io/multiformats/multiformats/multicodec/index.html#multiformats.multicodec.Multicodec.unwrap) methods perform analogous functionality
with an object-oriented API, additionally enforcing that the unwrapped code is actually
the code of the multicodec being used:

```py
>>> ip4 = multicodec.get("ip4")
>>> ip4
Multicodec(name='ip4', tag='multiaddr', code='0x04', status='permanent', description='')
>>> raw_data = bytes([192, 168, 0, 254])
>>> multicodec_data = ip4.wrap(raw_data)
>>> raw_data.hex()
  'c0a800fe'
>>> multicodec_data.hex()
'04c0a800fe'
>>> varint.encode(0x04).hex()
'04' #       0x04 ^^^^ is the multicodec code for 'ip4'
>>> ip4.unwrap(multicodec_data).hex()
  'c0a800fe'
>>> ip4.unwrap(bytes.fromhex('00c0a800fe')) # 'identity' multicodec data
multiformats.multicodec.err.ValueError: Found code 0x00 when unwrapping data, expected code 0x04.
```

The [`table`](https://hashberg-io.github.io/multiformats/multiformats/multicodec/index.html#multiformats.multicodec.table) function can be used to iterate through known multicodecs, optionally restrictiong to one or more tags and/or statuses:

```py
>>> len(list(multicodec.table())) # multicodec.table() returns an iterator
482
>>> selected = multicodec.table(tag=["cid", "ipld", "multiaddr"], status="permanent")
>>> [m.code for m in selected]
[1, 4, 6, 41, 53, 54, 55, 56, 81, 85, 112, 113, 114, 120,
 144, 145, 146, 147, 148, 149, 150, 151, 152, 176, 177,
 178, 192, 193, 290, 297, 400, 421, 460, 477, 478, 479, 512]
```

For advanced usage, see the [API documentation](https://hashberg-io.github.io/multiformats/multiformats/multicodec.html).


### Multibase

The [`multibase`](https://hashberg-io.github.io/multiformats/multiformats/multibase/index.html) module implements the [multibase spec](https://github.com/multiformats/multibase). The [`Multibase`](https://hashberg-io.github.io/multiformats/multiformats/multibase/index.html#multiformats.multibase.Multibase) class provides a container for multibase data:

```py
>>> Multibase(name="base16", code="f",
              status="default", description="hexadecimal")
    Multibase(name='base16', code='f', status='default', description='hexadecimal')
```

Core functionality is provided by the [`encode`](https://hashberg-io.github.io/multiformats/multiformats/multibase/index.html#multiformats.multibase.encode) and [`decode`](https://hashberg-io.github.io/multiformats/multiformats/multibase/index.html#multiformats.multibase.decode) functions, which can be used to
encode a bytestring into a string using a chosen multibase encoding and to decode a string
into a bytestring using the multibase encoding specified by its first character:

```py
>>> multibase.encode(b"Hello World!", "base32")
'bjbswy3dpeblw64tmmqqq'
>>> multibase.decode('bjbswy3dpeblw64tmmqqq')
b'Hello World!'
```

The multibase encoding specified by a given string is accessible using the [`from_str`](https://hashberg-io.github.io/multiformats/multiformats/multibase/index.html#multiformats.multibase.from_str) function:
```py
>>> multibase.from_str('bjbswy3dpeblw64tmmqqq')
Multibase(encoding='base32', code='b',
          status='default',
          description='rfc4648 case-insensitive - no padding')
```

The [`exists`](https://hashberg-io.github.io/multiformats/multiformats/multibase/index.html#multiformats.multibase.exists) and [`get`](https://hashberg-io.github.io/multiformats/multiformats/multibase/index.html#multiformats.multibase.get) functions can be used to check whether a multibase with given name or code is known, and if so to get the corresponding object:

```py
>>> multibase.exists("base32")
True
>>> multibase.get("base32")
Multibase(encoding='base32', code='b',
          status='default',
          description='rfc4648 case-insensitive - no padding')
>>> multibase.exists(code="f")
True
>>> multibase.get(code="f")
Multibase(encoding="base16", code="f",
          status="default", description="hexadecimal")
```

For advanced usage, see the [API documentation](https://hashberg-io.github.io/multiformats/multiformats/multibase.html).


### Multihash

The [`multihash`](https://hashberg-io.github.io/multiformats/multiformats/multihash/index.html) module implements the [multihash spec](https://github.com/multiformats/multihash).

Core functionality is provided by the [`digest`](https://hashberg-io.github.io/multiformats/multiformats/multihash/index.html#multiformats.multihash.digest), [`wrap`](https://hashberg-io.github.io/multiformats/multiformats/multihash/index.html#multiformats.multihash.wrap), [`unwrap`](https://hashberg-io.github.io/multiformats/multiformats/multihash/index.html#multiformats.multihash.unwrap) functions, or the correspondingly-named methods [`Multihash.wrap`](https://hashberg-io.github.io/multiformats/multiformats/multihash/index.html#multiformats.multihash.Multihash.wrap) and [`Multihash.unwrap`](https://hashberg-io.github.io/multiformats/multiformats/multihash/index.html#multiformats.multihash.Multihash.unwrap) of the [`Multihash`](https://hashberg-io.github.io/multiformats/multiformats/multihash/index.html#multiformats.multihash.Multihash) class.
The [`digest`](https://hashberg-io.github.io/multiformats/multiformats/multihash/index.html#multiformats.multihash.digest) function and [`Multihash.digest`](https://hashberg-io.github.io/multiformats/multiformats/multihash/index.html#multiformats.multihash.Multihash.digest) method can be used to create a multihash digest directly from data:

```py
>>> data = b"Hello world!"
>>> digest = multihash.digest(data, "sha2-256")
>>> digest.hex()
'1220c0535e4be2b79ffd93291305436bf889314e4a3faec05ecffcbb7df31ad9e51a'
```

```py
>>> sha2_256 = multihash.get("sha2-256")
>>> digest = sha2_256.digest(data)
>>> digest.hex()
'1220c0535e4be2b79ffd93291305436bf889314e4a3faec05ecffcbb7df31ad9e51a'
```

By default, the full digest produced by the hash function is used.
Optionally, a smaller digest size can be specified to produce truncated hashes:

```py
>>> digest = multihash.digest(data, "sha2-256", size=20)
#        optional truncated hash size, in bytes ^^^^^^^
>>> multihash_digest.hex()
'1214c0535e4be2b79ffd93291305436bf889314e4a3f' # 20-bytes truncated hash
```

The [`unwrap`](https://hashberg-io.github.io/multiformats/multiformats/multihash/index.html#multiformats.multihash.unwrap) function can be used to extract the raw digest from a multihash digest:

```py
>>> digest.hex()
'1214c0535e4be2b79ffd93291305436bf889314e4a3f'
>>> raw_digest = multihash.unwrap(digest)
>>> raw_digest.hex()
    'c0535e4be2b79ffd93291305436bf889314e4a3f'
```

The [`Multihash.unwrap`](https://hashberg-io.github.io/multiformats/multiformats/multihash/index.html#multiformats.multihash.Multihash.unwrap) method performs the same functionality, but additionally checks
that the multihash digest is valid for the multihash:

```py
>>> raw_digest = sha2_256.unwrap(digest)
>>> raw_digest.hex()
    'c0535e4be2b79ffd93291305436bf889314e4a3f'
```

```py
>>> sha1 = multihash.get("sha1")
>>> (sha2_256.code, sha1.code)
(18, 17)
>>> sha1.unwrap(digest)
err.ValueError: Decoded code 18 differs from multihash code 17.
```

The [`wrap`](https://hashberg-io.github.io/multiformats/multiformats/multihash/index.html#multiformats.multihash.wrap) function and [`Multihash.wrap`](https://hashberg-io.github.io/multiformats/multiformats/multihash/index.html#multiformats.multihash.Multihash.wrap) method can be used to wrap a raw digest into a multihash digest:

```py
>>> raw_digest.hex()
    'c0535e4be2b79ffd93291305436bf889314e4a3f'
>>> multihash.wrap(raw_digest, "sha2-256").hex()
'1214c0535e4be2b79ffd93291305436bf889314e4a3f'
```

```py
>>> sha2_256.wrap(raw_digest).hex()
'1214c0535e4be2b79ffd93291305436bf889314e4a3f'
```

The multihash multicodec specified by a given multihash digest is accessible using the [`from_digest`](https://hashberg-io.github.io/multiformats/multiformats/multihash/index.html#multiformats.multihash.from_digest) function:

```py
>>> multihash.from_digest(multihash_digest)
Multicodec(name='sha2-256', tag='multihash', code='0x12',
           status='permanent', description='')
```

Note the both multihash code and digest length are encoded as varints(see [varint](#varint) usage above) and can span multiple bytes:

```py
>>> multihash.get("skein1024-1024")
Multicodec(name='skein1024-1024', tag='multihash', code='0xb3e0',
           status='draft', description='')
>>> multihash.digest(data, "skein1024-1024").hex()
'e0e702800192e08f5143...' # 3+2+128 = 133 bytes in total
#^^^^^^     3-bytes varint for hash function code 0xb3e0
#      ^^^^ 2-bytes varint for hash digest length 128
>>> from multiformats import varint
>>> hex(varint.decode(bytes.fromhex("e0e702")))
'0xb3e0'
>>> varint.decode(bytes.fromhex("8001"))
128
```

Data and digests are all `bytes` objects (above, we represented them as hex strings for clarity):

```py
>>> hash_digest
        b'\xc0S^K\xe2\xb7\x9f\xfd\x93)\x13\x05Ck\xf8\x891NJ?'
>>> multihash_digest
b'\x12\x14\xc0S^K\xe2\xb7\x9f\xfd\x93)\x13\x05Ck\xf8\x891NJ?'
# ^^^^     0x12 -> multihash multicodec "sha2-256"
#     ^^^^ 0x14 -> truncated hash length of 20 bytes
```

If you wish to produce digests for objects of other types, you should encode them into `bytes` first.
For example, the `to_bytes(length, byteorder)` method can be used to obtain a `bytes` representation of an integer
with given number of bytes and byte ordering, while the `encode(encoding)` method can be used to obtain a `bytes`
representation of a string with given encoding: 

```py
>>> (400).to_bytes(4, byteorder="big")
b'\x00\x00\x01\x90'
>>> (400).to_bytes(4, byteorder="little")
b'\x90\x01\x00\x00'
>>> "Hello world!".encode("utf-8")
b'Hello world!'
>>> "Hello world!".encode("utf-16")
b'\xff\xfeH\x00e\x00l\x00l\x00o\x00 \x00w\x00o\x00r\x00l\x00d\x00!\x00'
>>> "Hello world!".encode("utf-16-le")
b'H\x00e\x00l\x00l\x00o\x00 \x00w\x00o\x00r\x00l\x00d\x00!\x00'
>>> "Hello world!".encode("utf-16-be")
b'\x00H\x00e\x00l\x00l\x00o\x00 \x00w\x00o\x00r\x00l\x00d\x00!'
```

For advanced usage, see the [API documentation](https://hashberg-io.github.io/multiformats/multiformats/multihash.html).


### CID

The [`cid`](https://hashberg-io.github.io/multiformats/multiformats/cid.html) module implements the [CID spec](https://github.com/multiformats/cid).

Core functionality is provided by the [`CID`](https://hashberg-io.github.io/multiformats/multiformats/cid.html#multiformats.cid.CID) class, which can be imported directly from `multiformats`:

```py
>>> from multiformats import CID
```

CIDs can be decoded from bytestrings or (multi)base encoded strings:

```py
>>> cid = CID.decode("zb2rhe5P4gXftAwvA4eXQ5HJwsER2owDyS9sKaQRRVQPn93bA")
>>> cid
CID('base58btc', 1, 'raw',
    '12206e6ff7950a36187a801613426e858dce686cd7d7e3c0fc42ee0330072d245c95')
```

CIDs can be created programmatically, and their fields accessed individually:

```py
>>> cid = CID("base58btc", 1, "raw",
... "12206e6ff7950a36187a801613426e858dce686cd7d7e3c0fc42ee0330072d245c95")
>>> cid.base
Multibase(name='base58btc', code='z',
          status='default', description='base58 bitcoin')
>>> cid.codec
Multicodec(name='raw', tag='ipld', code='0x55',
           status='permanent', description='raw binary')
>>> cid.hashfun
Multicodec(name='sha2-256', tag='multihash', code='0x12',
           status='permanent', description='')
>>> cid.digest.hex()
'12206e6ff7950a36187a801613426e858dce686cd7d7e3c0fc42ee0330072d245c95'
>>> cid.raw_digest.hex()
    '6e6ff7950a36187a801613426e858dce686cd7d7e3c0fc42ee0330072d245c95'
```

CIDs can be converted to bytestrings or (multi)base encoded strings:

```py
>>> str(cid)
'zb2rhe5P4gXftAwvA4eXQ5HJwsER2owDyS9sKaQRRVQPn93bA'
>>> bytes(cid).hex()
'015512206e6ff7950a36187a801613426e858dce686cd7d7e3c0fc42ee0330072d245c95'
>>> cid.encode("base32") # encode with different multibase
'bafkreidon73zkcrwdb5iafqtijxildoonbwnpv7dyd6ef3qdgads2jc4su'
```

Additionally, the [`CID.peer_id`](https://hashberg-io.github.io/multiformats/multiformats/cid.html#multiformats.cid.CID.peer_id) static method can be used to pack the raw hash of a public key into
a CIDv1 [PeerID](https://docs.libp2p.io/concepts/peer-id/), according to the [PeerID spec](https://github.com/libp2p/specs/blob/master/peer-ids/peer-ids.md):

```py
>>> pk_bytes = bytes.fromhex(
... "1498b5467a63dffa2dc9d9e069caf075d16fc33fdd4c3b01bfadae6433767d93")
... # a 32-byte Ed25519 public key
>>> peer_id = CID.peer_id(pk_bytes)
>>> peer_id
CID('base32', 1, 'libp2p-key',
'00201498b5467a63dffa2dc9d9e069caf075d16fc33fdd4c3b01bfadae6433767d93')
#^^   0x00 = 'identity' multihash used (public key length <= 42)
#  ^^ 0x20 = 32-bytes of raw hash digestlength
>>> str(peer_id)
'bafzaaiautc2um6td375c3soz4bu4v4dv2fx4gp65jq5qdp5nvzsdg5t5sm'
```

For advanced usage, see the [API documentation](https://hashberg-io.github.io/multiformats/multiformats/cid.html).


### Multiaddr

The [`multiaddr`](https://hashberg-io.github.io/multiformats/multiformats/multiaddr/index.html) module implements the [multiaddr spec](https://github.com/multiformats/multiaddr).

Core functionality is provided by the [`Proto`](https://hashberg-io.github.io/multiformats/multiformats/multiaddr/index.html#multiformats.multiaddr.Proto) class:

```py
>>> from multiformats import Proto
>>> ip4 = Proto("ip4")
>>> ip4
Proto("ip4")
>>> str(ip4)
'/ip4'
>>> ip4.codec
Multicodec(name='ip4', tag='multiaddr', code='0x04',
           status='permanent', description='')
```

Slash notation is used to attach address values to protocols:

```py
>>> a = ip4/"192.168.1.1"
>>> a
Addr('ip4', '192.168.1.1')
>>> str(a)
'/ip4/192.168.1.1'
>>> bytes(a).hex()
'04c0a80101'
```

Address values can be specified as strings, integers, or `bytes`-like objects:

```py
>>> ip4/"192.168.1.1"
Addr('ip4', '192.168.1.1')
>>> ip4/bytes([192, 168, 1, 1])
Addr('ip4', '192.168.1.1')
>>> udp = Proto("udp")
>>> udp/9090 # int 9090 is converted to str "9090"
Addr('udp', '9090')
```

Slash notation is also used to encapsulate multiple protocol/address segments into a [multiaddr](https://multiformats.io/multiaddr/):

```py
>>> quic = Proto("quic") # no addr required
>>> ma = ip4/"127.0.0.1"/udp/9090/quic
>>> ma
Multiaddr(Addr('ip4', '127.0.0.1'), Addr('udp', '9090'), Proto('quic'))
>>> str(ma)
'/ip4/127.0.0.1/udp/9090/quic'
```

Bytes for multiaddrs are computed according to the [`(TLV)+` multiaddr encoding](https://multiformats.io/multiaddr/):

```py
>>> bytes(ip4/"127.0.0.1").hex()
'047f000001'
>>> bytes(udp/9090).hex()
          '91022382'
>>> bytes(quic).hex()
                  'cc03'
>>> bytes(ma).hex()
'047f00000191022382cc03'
```

The [`parse`](https://hashberg-io.github.io/multiformats/multiformats/multiaddr/index.html#multiformats.multiaddr.parse) and [`decode`](https://hashberg-io.github.io/multiformats/multiformats/multiaddr/index.html#multiformats.multiaddr.decode) functions create multiaddrs from their human-readable strings and encoded bytes respectively:

```py
    >>> from multiformats import multiaddr
    >>> s = '/ip4/127.0.0.1/udp/9090/quic'
    >>> multiaddr.parse(s)
    Multiaddr(Addr('ip4', '127.0.0.1'), Addr('udp', '9090'), Proto('quic'))
    >>> b = bytes.fromhex('047f00000191022382cc03')
    >>> multiaddr.decode(b)
    Multiaddr(Addr('ip4', '127.0.0.1'), Addr('udp', '9090'), Proto('quic'))
```

For uniformity of API, the same functionality as the [`Proto`](https://hashberg-io.github.io/multiformats/multiformats/multiaddr/index.html#multiformats.multiaddr.Proto) class is provided by the [`proto`](https://hashberg-io.github.io/multiformats/multiformats/multiaddr/index.html#multiformats.multiaddr.proto) function:

```py
>>> ip4 = multiaddr.proto("ip4")
>>> ip4
Proto("ip4")
```

For advanced usage, see the [API documentation](https://hashberg-io.github.io/multiformats/multiformats/multiaddr.html).


## API

The [API documentation](https://hashberg-io.github.io/multiformats/multiformats/index.html) for this package is automatically generated by [pdoc](https://pdoc3.github.io/pdoc/).


## Contributing

Please see [the contributing file](./CONTRIBUTING.md).


## License

[MIT © Hashberg Ltd.](LICENSE)
