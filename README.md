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

The `varint` module implements the [unsigned-varint spec](https://github.com/multiformats/unsigned-varint). Functionality is provided by the `encode` and `decode` functions, converting between non-negative `int` values and the corresponding varint `bytes`: 

```py
>>> from multiformats import varint
>>> varint.encode(128)
b'\x80\x01'
>>> varint.decode(b'\x80\x01')
128
```

For advanced usage, see the [API documentation](https://hashberg-io.github.io/multiformats/multiformats/varint.html). 


### Multicodec

The `multicodec` module implements the [multicodec spec](https://github.com/multiformats/multicodec). The `Multicodec` class provides a container for multicodec data:

```py
>>> Multicodec("identity", "multihash", 0x00, "permanent", "raw binary")
Multicodec(name='identity', tag='multihash', code=0,
           status='permanent', description='raw binary')
```

The `exists` and `get` functions can be used to check whether a multicodec with given name or code is known, and if so to get the corresponding object:

```py
>>> from multiformats import multicodec
>>> multicodec.exists("identity")
True
>>> multicodec.exists(0x01)
True
>>> multicodec.get("identity")
Multicodec(name='identity', tag='multihash', code=0,
           status='permanent', description='raw binary')
>>> multicodec.get(0x01)
Multicodec(name='cidv1', tag='ipld', code=1,
           status='permanent', description='CIDv1')
```

The `table` function can be used to iterate through known multicodecs, optionally restrictiong to one or more tags and/or statuses:

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

The `multibase` module implements the [multibase spec](https://github.com/multiformats/multibase). The `Multibase` class provides a container for multibase data:

```py
>>> Multibase(name="base16", code="f",
              status="default", description="hexadecimal")
    Multibase(name='base16', code='f', status='default', description='hexadecimal')
```

Core functionality is provided by the `encode` and `decode` functions, which can be used to
encode a bytestring into a string using a chosen multibase encoding and to decode a string
into a bytestring using the multibase encoding specified by its first character:

```py
>>> multibase.encode(b"Hello World!", "base32")
'bjbswy3dpeblw64tmmqqq'
>>> multibase.decode('bjbswy3dpeblw64tmmqqq')
b'Hello World!'
```

The multibase encoding specified by a given string is accessible using the `from_str` function:
```py
>>> multibase.from_str('bjbswy3dpeblw64tmmqqq')
Multibase(encoding='base32', code='b',
          status='default',
          description='rfc4648 case-insensitive - no padding')
```

The `exists` and `get` functions can be used to check whether a multibase with given name or code is known, and if so to get the corresponding object:

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

The `multihash` module implements the [multihash spec](https://github.com/multiformats/multihash).
The `exists` and `get` functions can be used to check whether a multihash multicodec with given name or code is known, and if so to get the corresponding object:


Core functionality is provided by the `digest`, `encode`, `decode` functions.
The `digest` function can be used to create a multihash digest directly from data:

```py
>>> data = b"Hello world!"
>>> multihash_digest = multihash.digest(data, "sha2-256")
>>> multihash_digest.hex()
'1220c0535e4be2b79ffd93291305436bf889314e4a3faec05ecffcbb7df31ad9e51a'
```
By default, the full digest produced by the hash function is used.
Optionally, a smaller digest size can be specified to produce truncated hashes:

```py
>>> multihash_digest = multihash.digest(data, "sha2-256", size=20)
#                  optional truncated hash size, in bytes ^^^^^^^
>>> multihash_digest.hex()
'1214c0535e4be2b79ffd93291305436bf889314e4a3f' # 20-bytes truncated hash
```

The `decode` function can be used to extract the raw hash digest from a multihash digest:

```py
>>> multihash_digest.hex()
'1214c0535e4be2b79ffd93291305436bf889314e4a3f'
>>> hash_digest = multihash.decode(multihash_digest)
>>> hash_digest.hex()
    'c0535e4be2b79ffd93291305436bf889314e4a3f'
```

The `encode` function can be used to encode a raw hash digest into a multihash digest:

```py
>>> hash_digest.hex()
    'c0535e4be2b79ffd93291305436bf889314e4a3f'
>>> multihash.encode(hash_digest, "sha2-256").hex()
'1214c0535e4be2b79ffd93291305436bf889314e4a3f'
```

The multihash multicodec specified by a given multihash digest is accessible using the `from_digest` function:

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

Also note that data and digests are all `bytes` objects, represented here as hex strings for clarity:

```py
>>> hash_digest
        b'\xc0S^K\xe2\xb7\x9f\xfd\x93)\x13\x05Ck\xf8\x891NJ?'
>>> multihash_digest
b'\x12\x14\xc0S^K\xe2\xb7\x9f\xfd\x93)\x13\x05Ck\xf8\x891NJ?'
# ^^^^     0x12 -> multihash multicodec "sha2-256"
#     ^^^^ 0x14 -> truncated hash length of 20 bytes
```

For advanced usage, see the [API documentation](https://hashberg-io.github.io/multiformats/multiformats/multihash.html).


## API

The [API documentation](https://hashberg-io.github.io/multiformats/multiformats/index.html) for this package is automatically generated by [pdoc](https://pdoc3.github.io/pdoc/).


## Contributing

Please see [the contributing file](./CONTRIBUTING.md).


## License

[MIT © Hashberg Ltd.](LICENSE)
