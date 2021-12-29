Multihash
=========

The :mod:`~multiformats.multihash` module implements the `multihash spec <https://github.com/multiformats/multihash>`_.

>>> from multiformats import multihash


Multihash
---------

The :class:`~multiformats.multihash.Multihash` class provides a container for multihash multicodec data:

>>> from multiformats.multihash import Multihash
>>> Multihash(codec="sha2-256")
Multihash(codec='sha2-256')


digest
------

The :func:`~multiformats.multihash.digest` function and the method :meth:`~multiformats.multihash.Multihash.digest` of :class:`~multiformats.multihash.Multihash` objects can be used to create a multihash digest directly from data:

>>> data = b"Hello world!"
>>> digest = multihash.digest(data, "sha2-256")
>>> digest.hex()
'1220c0535e4be2b79ffd93291305436bf889314e4a3faec05ecffcbb7df31ad9e51a'

>>> sha2_256 = multihash.get("sha2-256")
>>> digest = sha2_256.digest(data)
>>> digest.hex()
'1220c0535e4be2b79ffd93291305436bf889314e4a3faec05ecffcbb7df31ad9e51a'

By default, the full digest produced by the hash function is used. Optionally, a smaller digest size can be specified to produce truncated hashes:

>>> digest = multihash.digest(data, "sha2-256", size=20)
#        optional truncated hash size, in bytes ^^^^^^^
>>> digest.hex()
'1214c0535e4be2b79ffd93291305436bf889314e4a3f' # 20-bytes truncated hash

unwrap
------

The :func:`~multiformats.multihash.unwrap` function can be used to extract the raw digest from a multihash digest:

>>> digest.hex()
'1214c0535e4be2b79ffd93291305436bf889314e4a3f'
>>> raw_digest = multihash.unwrap(digest)
>>> raw_digest.hex()
    'c0535e4be2b79ffd93291305436bf889314e4a3f'

The method :meth:`~multiformats.multihash.Multihash.unwrap` of :class:`~multiformats.multihash.Multihash` objects performs the same functionality, but additionally checks that the multihash digest is valid for the multihash:

>>> raw_digest = sha2_256.unwrap(digest)
>>> raw_digest.hex()
    'c0535e4be2b79ffd93291305436bf889314e4a3f'

>>> sha1 = multihash.get("sha1")
>>> (sha2_256.code, sha1.code)
(18, 17)
>>> sha1.unwrap(digest)
err.ValueError: Decoded code 18 differs from multihash code 17.

wrap
----

The :func:`~multiformats.multihash.wrap` function and the method :meth:`~multiformats.multihash.Multihash.wrap` of :class:`~multiformats.multihash.Multihash` objects can be used to wrap a raw digest into a multihash digest:

>>> raw_digest.hex()
    'c0535e4be2b79ffd93291305436bf889314e4a3f'
>>> multihash.wrap(raw_digest, "sha2-256").hex()
'1214c0535e4be2b79ffd93291305436bf889314e4a3f'

>>> sha2_256.wrap(raw_digest).hex()
'1214c0535e4be2b79ffd93291305436bf889314e4a3f'

Note the both multihash code and digest length are wrapped as varints (see the :mod:`~multiformats.multihash.multiformats.varint` module) and can span multiple bytes:

>>> skein1024_1024 = multihash.get("skein1024-1024")
>>> skein1024_1024.codec
Multicodec(name='skein1024-1024', tag='multihash', code='0xb3e0',
           status='draft', description='')
>>> skein1024_1024.digest(data).hex()
'e0e702800192e08f5143...' # 3+2+128 = 133 bytes in total
#^^^^^^     3-bytes varint for hash function code 0xb3e0
#      ^^^^ 2-bytes varint for hash digest length 128
>>> from multiformats import varint
>>> hex(varint.decode(bytes.fromhex("e0e702")))
'0xb3e0'
>>> varint.decode(bytes.fromhex("8001"))
128

Also note that data and digests are all :py:obj:`bytes` objects, represented here as hex strings for clarity:

>>> raw_digest
        b'\\xc0S^K\\xe2\\xb7\\x9f\\xfd\\x93)\\x13\\x05Ck\\xf8\\x891NJ?'
>>> digest
b'\\x12\\x14\\xc0S^K\\xe2\\xb7\\x9f\\xfd\\x93)\\x13\\x05Ck\\xf8\\x891NJ?'
# ^^^^^      0x12 -> multihash multicodec "sha2-256"
#      ^^^^^ 0x14 -> truncated hash length of 20 bytes

from_digest
-----------

The multihash specified by a given multihash digest is accessible using the :func:`~multiformats.multihash.from_digest` function:

>>> multihash.from_digest(digest)
Multihash(codec='sha2-256')
>>> multihash.from_digest(digest).codec
Multicodec(name='sha2-256', tag='multihash', code='0x12',
           status='permanent', description='')

get, exists
-----------

Additional multihash management functionality is provided by the :func:`~multiformats.multihash.exists` and :func:`~multiformats.multihash.get` functions, which can be used to check whether a multihash multicodec with given name or code is known, and if so to get the corresponding object:

>>> multihash.exists("sha1")
True
>>> multihash.get("sha1")
Multihash(codec='sha1')
>>> multihash.exists(code=0x11)
True
>>> multihash.get(code=0x11)
Multihash(codec='sha1')
