multiformats: Python implementation of `multiformat protocols <https://multiformats.io/>`_
============================================================================================

.. image:: https://img.shields.io/badge/python-3.7+-green.svg
    :target: https://docs.python.org/3.7/
    :alt: Python versions

.. image:: https://img.shields.io/pypi/v/multiformats.svg
    :target: https://pypi.python.org/pypi/multiformats/
    :alt: PyPI version

.. image:: https://img.shields.io/pypi/status/multiformats.svg
    :target: https://pypi.python.org/pypi/multiformats/
    :alt: PyPI status

.. image:: http://www.mypy-lang.org/static/mypy_badge.svg
    :target: https://github.com/python/mypy
    :alt: Checked with Mypy
    
.. image:: https://readthedocs.org/projects/multiformats/badge/?version=latest
    :target: https://multiformats.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. image:: https://github.com/hashberg-io/multiformats/actions/workflows/python-pytest.yml/badge.svg
    :target: https://github.com/hashberg-io/multiformats/actions/workflows/python-pytest.yml
    :alt: Python package status

.. image:: https://img.shields.io/badge/readme%20style-standard-brightgreen.svg?style=flat-square
    :target: https://github.com/RichardLitt/standard-readme
    :alt: standard-readme compliant


Multiformats is a compliant implementation of `multiformat protocols <https://multiformats.io/>`_:

.. contents::


Install
-------

You can install the latest release from `PyPI <https://pypi.org/project/multiformats/>`_ as follows:

.. code-block:: console

    $ pip install --upgrade multiformats


Usage
-----

You can import multiformat protocols directly from top level:

>>> from multiformats import *

The above will import the following names:

.. code-block:: python

    varint, multicodec, multibase, multihash, multiaddr, CID

The first five are modules implementing the homonymous specifications, while ``CID`` is a class for Content IDentifiers.
Below are some basic usage examples, to get you started: for detailed documentation, see https://multiformats.readthedocs.io/


Varint encode/decode
^^^^^^^^^^^^^^^^^^^^

>>> varint.encode(128)
b'\x80\x01'
>>> varint.decode(b'\x80\x01')
128


Multicodec wrap/unwrap
^^^^^^^^^^^^^^^^^^^^^^

Procedural style:

>>> raw_data = bytes([192, 168, 0, 254])
>>> multicodec_data = multicodec.wrap("ip4", raw_data)
>>> raw_data.hex()
  'c0a800fe'
>>> multicodec_data.hex()
'04c0a800fe'
>>> codec, _raw_data = multicodec.unwrap(multicodec_data)
>>> _raw_data.hex()
  'c0a800fe'
>>> codec
Multicodec(name='ip4', tag='multiaddr', code='0x04',
           status='permanent', description='')

Object-oriented style:

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
>>> ip4.unwrap(multicodec_data).hex()
  'c0a800fe'


Multibase encode/decode
^^^^^^^^^^^^^^^^^^^^^^^

Procedural style:

>>> multibase.encode(b"Hello World!", "base32")
'bjbswy3dpeblw64tmmqqq'
>>> multibase.decode('bjbswy3dpeblw64tmmqqq')
b'Hello World!'

Object-oriented style:

>>> base32 = multibase.get("base32")
>>> base32.encode(b"Hello World!")
'bjbswy3dpeblw64tmmqqq'
>>> base32.decode('bjbswy3dpeblw64tmmqqq')
b'Hello World!'


Multihash digest
^^^^^^^^^^^^^^^^

Procedural style:

>>> data = b"Hello world!"
>>> digest = multihash.digest(data, "sha2-256")
>>> digest.hex()
'1220c0535e4be2b79ffd93291305436bf889314e4a3faec05ecffcbb7df31ad9e51a'

Object-oriented style:

>>> sha2_256 = multihash.get("sha2-256")
>>> digest = sha2_256.digest(data)
>>> digest.hex()
'1220c0535e4be2b79ffd93291305436bf889314e4a3faec05ecffcbb7df31ad9e51a'

Optional truncated digests:

>>> digest = multihash.digest(data, "sha2-256", size=20)
#        optional truncated hash size, in bytes ^^^^^^^
>>> digest.hex()
'1214c0535e4be2b79ffd93291305436bf889314e4a3f'


Multihash wrap/unwrap
^^^^^^^^^^^^^^^^^^^^^

Procedural style:

>>> digest.hex()
'1214c0535e4be2b79ffd93291305436bf889314e4a3f'
>>> raw_digest = multihash.unwrap(digest)
>>> raw_digest.hex()
    'c0535e4be2b79ffd93291305436bf889314e4a3f'
>>> multihash.wrap(raw_digest, "sha2-256").hex()
'1214c0535e4be2b79ffd93291305436bf889314e4a3f'

Object-oriented style:

>>> sha2_256 = multihash.get("sha2-256")
>>> raw_digest = sha2_256.unwrap(digest)
>>> raw_digest.hex()
    'c0535e4be2b79ffd93291305436bf889314e4a3f'
>>> sha2_256.wrap(raw_digest).hex()
'1214c0535e4be2b79ffd93291305436bf889314e4a3f'


CID encode/decode
^^^^^^^^^^^^^^^^^

Decoding from multibase encoded strings:

>>> cid = CID.decode("zb2rhe5P4gXftAwvA4eXQ5HJwsER2owDyS9sKaQRRVQPn93bA")
>>> cid
CID('base58btc', 1, 'raw',
  '12206e6ff7950a36187a801613426e858dce686cd7d7e3c0fc42ee0330072d245c95')
>>> cid.base
Multibase(name='base58btc', code='z',
          status='default', description='base58 bitcoin')
>>> cid.codec
Multicodec(name='raw', tag='ipld', code='0x55',
           status='permanent', description='raw binary')
>>> cid.digest.hex()
'12206e6ff7950a36187a801613426e858dce686cd7d7e3c0fc42ee0330072d245c95'
>>> cid.hashfun
Multicodec(name='sha2-256', tag='multihash', code='0x12',
           status='permanent', description='')
>>> cid.raw_digest.hex()
    '6e6ff7950a36187a801613426e858dce686cd7d7e3c0fc42ee0330072d245c95'

Multibase encoding:

>>> str(cid) # encode with own multibase 'base58btc'
'zb2rhe5P4gXftAwvA4eXQ5HJwsER2owDyS9sKaQRRVQPn93bA'
>>> cid.encode("base32") # encode with different multibase
'bafkreidon73zkcrwdb5iafqtijxildoonbwnpv7dyd6ef3qdgads2jc4su'


PeerID creation
^^^^^^^^^^^^^^^

Creation of `CIDv1 PeerIDs <https://docs.libp2p.io/concepts/peer-id/>`_:

>>> pk_bytes = bytes.fromhex( # hex-string of 32-byte Ed25519 public key
... "1498b5467a63dffa2dc9d9e069caf075d16fc33fdd4c3b01bfadae6433767d93")
>>> peer_id = CID.peer_id(pk_bytes)
>>> peer_id
CID('base32', 1, 'libp2p-key',
'00201498b5467a63dffa2dc9d9e069caf075d16fc33fdd4c3b01bfadae6433767d93')
#^^   0x00 = 'identity' multihash used (public key length <= 42)
#  ^^ 0x20 = 32-bytes of raw hash digest length
>>> str(peer_id)
'bafzaaiautc2um6td375c3soz4bu4v4dv2fx4gp65jq5qdp5nvzsdg5t5sm'


Multiaddr parse/decode
^^^^^^^^^^^^^^^^^^^^^^

>>> s = '/ip4/127.0.0.1/udp/9090/quic'
>>> multiaddr.parse(s)
Multiaddr(Addr('ip4', '127.0.0.1'), Addr('udp', '9090'), Proto('quic'))
>>> b = bytes.fromhex('047f00000191022382cc03')
>>> multiaddr.decode(b)
Multiaddr(Addr('ip4', '127.0.0.1'), Addr('udp', '9090'), Proto('quic'))


Multiaddr protocols/addresses
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Accessing multiaddr protocols:

>>> ip4 = multiaddr.proto("ip4")
>>> ip4
Proto("ip4")
>>> udp = multiaddr.proto("udp")
>>> quic = multiaddr.proto("quic")

Creating protocol addresses from human-readable strings:

>>> a = ip4/"192.168.1.1"
>>> a
Addr('ip4', '192.168.1.1')
>>> str(a)
'/ip4/192.168.1.1'
>>> a.value
'192.168.1.1'
>>> bytes(a).hex()
'04c0a80101'
>>> a.value_bytes.hex()
  'c0a80101'

Creating protocol addresses from bytestrings:

>>> a = ip4/bytes([192, 168, 1, 1])
>>> a
Addr('ip4', '192.168.1.1')


Multiaddr encapsulation/decapsulation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Creating multiaddresses by protocol encapsulation:

>>> ma = ip4/"127.0.0.1"/udp/9090/quic
>>> ma
Multiaddr(Addr('ip4', '127.0.0.1'), Addr('udp', '9090'), Proto('quic'))
>>> str(ma)
'/ip4/127.0.0.1/udp/9090/quic'

Bytes for multiaddrs are computed according to the `(TLV)+ multiaddr format <https://multiformats.io/multiaddr/>`_:

>>> bytes(ip4/"127.0.0.1").hex()
'047f000001'
>>> bytes(udp/9090).hex()
          '91022382'
>>> bytes(quic).hex()
                  'cc03'
>>> bytes(ma).hex()
'047f00000191022382cc03'

Protocol decapsulation by indexing and slicing:

>>> ma[0]
Addr('ip4', '127.0.0.1')
>>> ma[:2]
Multiaddr(Addr('ip4', '127.0.0.1'), Addr('udp', '9090'))
>>> ma[1:]
Multiaddr(Addr('udp', '9090'), Proto('quic'))


API
---

For the full API documentation, see https://multiformats.readthedocs.io/


Contributing
------------

Please see `<CONTRIBUTING.md>`_.


License
-------

`MIT © Hashberg Ltd. <LICENSE>`_
