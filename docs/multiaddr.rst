Multiaddr
=========

The :mod:`~multiformats.multiaddr` module implements the `multiaddr spec <https://github.com/multiformats/multiaddr>`_.

>>> from multiformats import multiaddr


Proto
-----

Core functionality is provided by the :class:`~multiformats.multiaddr.Proto` class:

>>> from multiformats import Proto
>>> ip4 = Proto("ip4")
>>> ip4
Proto("ip4")
>>> str(ip4)
'/ip4'
>>> ip4.codec
Multicodec(name='ip4', tag='multiaddr', code='0x04',
           status='permanent', description='')

For uniformity of usage style with the other modules, the same functionality as the :func:`~multiformats.multiaddr.Proto` class is provided by the :func:`~multiformats.multiaddr.proto` function:

>>> ip4 = multiaddr.proto("ip4")
>>> ip4
Proto("ip4")


address values
--------------

Slash notation is used to attach address values to protocols:

>>> a = ip4/"192.168.1.1"
>>> a
Addr('ip4', '192.168.1.1')
>>> str(a)
'/ip4/192.168.1.1'
>>> bytes(a)
b'\x04\xc0\xa8\x01\x01'

Address values can be specified as strings, integers, or `bytes`-like objects:

>>> ip4/"192.168.1.1"
Addr('ip4', '192.168.1.1')
>>> ip4/b'\xc0\xa8\x01\x01' # ip4/bytes([192, 168, 1, 1])
Addr('ip4', '192.168.1.1')
>>> udp = multiaddr.proto("udp")
>>> udp/9090 # udp/"9090"
Addr('udp', '9090')


protocol encapsulation
----------------------

Slash notation is also used to encapsulate multiple protocol/address segments into a `multiaddr <https://multiformats.io/multiaddr/>`_:

>>> quic = multiaddr.proto("quic")
>>> ma = ip4/"127.0.0.1"/udp/9090/quic
>>> ma
Multiaddr(Addr('ip4', '127.0.0.1'), Addr('udp', '9090'), Proto('quic'))
>>> str(ma)
'/ip4/127.0.0.1/udp/9090/quic'


bytes
-----

Bytes for multiaddrs are computed according to the `(TLV)+ multiaddr encoding <https://multiformats.io/multiaddr/#multiaddr-format>`_:

>>> bytes(ip4/"127.0.0.1").hex()
'047f000001'
>>> bytes(udp/9090).hex()
          '91022382'
>>> bytes(quic).hex()
                  'cc03'
>>> bytes(ma).hex()
'047f00000191022382cc03'


parse, decode
-------------

The :func:`~multiformats.multiaddr.parse` and :func:`~multiformats.multiaddr.decode` functions create multiaddrs from their human-readable strings and encoded bytes respectively:

>>> s = '/ip4/127.0.0.1/udp/9090/quic'
>>> multiaddr.parse(s)
Multiaddr(Addr('ip4', '127.0.0.1'), Addr('udp', '9090'), Proto('quic'))
>>> b = bytes.fromhex('047f00000191022382cc03')
>>> multiaddr.decode(b)
Multiaddr(Addr('ip4', '127.0.0.1'), Addr('udp', '9090'), Proto('quic'))
