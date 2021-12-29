CID
===

The :mod:`~multiformats.cid` module implements the `Content IDentifier spec <https://github.com/multiformats/cid>`_.

>>> from multiformats import CID

CID
---

Core functionality is provided by the :class:`~multiformats.cid.CID` class.
CIDs can be created programmatically from a choice of multibase, CID version, multicodec and multihash digest:

>>> digest = \
... "12206e6ff7950a36187a801613426e858dce686cd7d7e3c0fc42ee0330072d245c95"
>>> cid = CID("base58btc", 1, "raw", digest)
>>> cid.base
Multibase(name='base58btc', code='z',
          status='default', description='base58 bitcoin')
>>> cid.codec
Multicodec(name='raw', tag='ipld', code='0x55',
           status='permanent', description='raw binary')
>>> cid.digest.hex()
'12206e6ff7950a36187a801613426e858dce686cd7d7e3c0fc42ee0330072d245c95'

Additionally, the :attr:`~multiformats.cid.CID.hashfun` and :attr:`~multiformats.cid.CID.raw_digest` properties can be used to access the multihash multicodec and raw digest that form the multihash digest:

>>> cid.hashfun
Multicodec(name='sha2-256', tag='multihash', code='0x12',
           status='permanent', description='')
>>> cid.raw_digest.hex()
'6e6ff7950a36187a801613426e858dce686cd7d7e3c0fc42ee0330072d245c95'


decode
------

The :meth:`~multiformats.cid.CID.decode` method can be used to decode CIDs from bytestrings or (multi)base encoded strings:

>>> cid = CID.decode("zb2rhe5P4gXftAwvA4eXQ5HJwsER2owDyS9sKaQRRVQPn93bA")
>>> cid
CID('base58btc', 1, 'raw',
  '12206e6ff7950a36187a801613426e858dce686cd7d7e3c0fc42ee0330072d245c95')


str, bytes
----------

CIDs can be converted to bytestrings or (multi)base encoded strings:

>>> bytes(cid).hex()
'015512206e6ff7950a36187a801613426e858dce686cd7d7e3c0fc42ee0330072d245c95'
>>> str(cid) # encode with own multibase 'base58btc'
'zb2rhe5P4gXftAwvA4eXQ5HJwsER2owDyS9sKaQRRVQPn93bA'
>>> cid.encode("base32") # encode with different multibase
'bafkreidon73zkcrwdb5iafqtijxildoonbwnpv7dyd6ef3qdgads2jc4su'

peer_id
-------

The :meth:`~multiformats.cid.CID.peer_id` static method can be used to pack the raw hash of a public key into a CIDv1 `PeerID <https://docs.libp2p.io/concepts/peer-id/>`_, according to the `PeerID spec <https://github.com/libp2p/specs/blob/master/peer-ids/peer-ids.md>`_:

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
