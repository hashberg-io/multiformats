Multicodec
==========

The :mod:`~multiformats.multicodec` module implements the `multicodec spec <https://github.com/multiformats/multicodec>`_.

>>> from multiformats import multicodec


Multicodec
----------

The :class:`~multiformats.multicodec.Multicodec` class provides a container for multicodec data:

>>> from multiformats import multicodec
>>> from multiformats.multicodec import Multicodec
>>> Multicodec("identity", "multihash", 0x00, "permanent", "raw binary")
Multicodec(name='identity', tag='multihash', code=0,
           status='permanent', description='raw binary')

get, exists
-----------

The :func:`~multiformats.multicodec.get` and :func:`~multiformats.multicodec.exists` functions can be used to check whether a multicodec with given name or code is known, and if so to get the corresponding object:

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

wrap, unwrap
------------

The :func:`~multiformats.multicodec.wrap` and :func:`~multiformats.multicodec.unwrap` functions can be use to wrap raw binary data into multicodec data (prepending the varint-encoded multicodec code) and to unwrap multicodec data into a pair of multicodec and raw binary data:

>>> raw_data = bytes([192, 168, 0, 254])
>>> multicodec_data = multicodec.wrap("ip4", raw_data)
>>> raw_data.hex()
  'c0a800fe'
>>> multicodec_data.hex()
'04c0a800fe'
>>> varint.encode(0x04).hex()
'04' #       0x04 ^^^^ is the multicodec code for 'ip4'
>>> codec, raw_data = multicodec.unwrap(multicodec_data)
>>> raw_data.hex()
  'c0a800fe'
>>> codec
Multicodec(name='ip4', tag='multiaddr', code='0x04',
           status='permanent', description='')


The :meth:`~multiformats.multicodec.Multicodec.wrap` and :meth:`~multiformats.multicodec.Multicodec.unwrap` methods perform analogous functionality with an object-oriented API, additionally enforcing that the multicodec is being used to unwrap the data is the multicodec that the data itself specifies:

>>> ip4 = multicodec.get("ip4")
>>> ip4
Multicodec(name='ip4', tag='multiaddr', code='0x04',
           status='permanent', description='')
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
multiformats.multicodec.err.ValueError:
    Found code 0x00 when unwrapping data, expected code 0x04.

table
-----

The :func:`~multiformats.multicodec.table` function can be used to iterate through known multicodecs, optionally restricting to one or more tags and/or statuses:

>>> len(list(multicodec.table())) # multicodec.table() returns an iterator
482
>>> tags = ["cid", "ipld", "multiaddr"]
>>> selected = multicodec.table(tag=tags, status="permanent")
>>> [m.code for m in selected]
[1, 4, 6, 41, 53, 54, 55, 56, 81, 85, 112, 113, 114, 120,
 144, 145, 146, 147, 148, 149, 150, 151, 152, 176, 177,
 178, 192, 193, 290, 297, 400, 421, 460, 477, 478, 479, 512]
