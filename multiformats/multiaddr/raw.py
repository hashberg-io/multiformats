"""
    Implementation of raw encodings used by multiaddr protocols.

    For expected address bytestring sizes, see the `multiaddr table <https://github.com/multiformats/multiaddr/blob/master/protocols.csv>`_.
"""

from __future__ import annotations

from ipaddress import IPv4Address, IPv6Address, AddressValueError
from typing import Callable, Dict, Optional, Tuple
from typing_validation import validate

from multiformats.varint import BytesLike
from .err import MultiaddrKeyError, MultiaddrValueError

RawEncoder = Callable[[str], bytes]
""" Type alias for raw address value encoders. """

RawDecoder = Callable[[BytesLike], str]
""" Type alias for raw address value decoders. """

ProtoImpl = Tuple[Optional[RawEncoder], Optional[RawDecoder], Optional[int]]
""" Type alias for raw protocol implementation, as a triple ``(raw_encoder, raw_decoder, addr_size)``. """

_proto_impl: Dict[str, ProtoImpl] = {}

def get(name: str) -> ProtoImpl:
    """
        Gets the implementation ``(raw_encoder, raw_decoder, addr_size)`` for a protocol with given name.

        The ``addr_size`` component is the size in bytes for the binary representation of protocol addresses:

        - for protocols with no address, ``addr_size`` is 0
        - for protocols with addresses of variable binary size, ``addr_size`` is :obj:`None`
        - for all other protocols, ``addr_size`` is a positive :obj:`int`

        Example usage:

        >>> multiaddr.raw.get("ip4")
        (
         <function ip4_encoder at 0x000002DDE1655550>,
         <function ip4_decoder at 0x000002DDE16555E0>,
         4
        )

        :param name: the protocol implementation name
        :type name: :obj:`str`

        :raises KeyError: if no such protocol implementation exists
    """
    validate(name, str)
    if name not in _proto_impl:
        raise MultiaddrKeyError(f"No implementation for protocol {repr(name)}.")
    return _proto_impl[name]


def exists(name: str) -> bool:
    """
        Checks whether the protocol with given name has an implementation.

        Example usage:

        >>> multiaddr.raw.exists("ip4")
        True

        :param name: the protocol implementation name
        :type name: :obj:`str`
    """
    validate(name, str)
    return name in _proto_impl


def register(name: str, raw_encoder: Optional[RawEncoder], raw_decoder: Optional[RawDecoder], addr_size: Optional[int], *,
             overwrite: bool = False) -> None:
    """
        Registers an implementation for the protocol by given name.

        If ``addr_size`` is 0, ``raw_encoder`` and ``raw_decoder`` should both be :obj:`None` (because the protocol admits no address).

        It is expected that ``raw_encoder`` raises :class:`~multiformats.multiaddr.err.MultiaddrValueError`
        if the string passed to it is not a valid string representatio for an address of this protocol.
        It is expected that ``raw_decoder`` raises :class:`~multiformats.multiaddr.err.MultiaddrValueError`
        if the bytestring passed to it is not a valid binary representation for an address of this protocol.

        Example usage for protocol requiring address value:

        .. code-block:: python

            def ip4_encoder(s: str) -> bytes:
                validate(s, str)
                return IPv4Address(s).packed

            def ip4_decoder(b: BytesLike) -> str:
                validate(b, BytesLike)
                _validate_size('ip4', b, 4)
                return str(IPv4Address(b))

            multiformats.raw.register("ip4", ip4_encoder, ip4_decoder, 4)


        Example usage for protocol not requiring address value:

        .. code-block:: python

            multiformats.raw.register("quic", None, None, 0)

        :param name: the protocol implementation name
        :type name: :obj:`str`
        :param raw_encoder: the raw encoder
        :type raw_encoder: :obj:`RawEncoder` or :obj:`None`
        :param raw_decoder: the raw decoder
        :type raw_decoder: :obj:`RawDecoder` or :obj:`None`
        :param addr_size: the expected address size for protocol addresses, in bytes (0 if no address is expected, :obj:`None` if address size is variable)
        :type addr_size: :obj:`int` or :obj:`None`
        :param overwrite: whether to overwrite an existing implementation with the same name
        :type overwrite: :obj:`bool`

        :raises ValueError: if ``addr_size`` is a negative integer
        :raises ValueError: if ``addr_size`` is 0 and either one of ``raw_encoder`` or ``raw_decoder`` is not :obj:`None`
        :raises ValueError: if ``overwrite`` is :obj:`False` and an implementation with the same name already exists
    """
    validate(name, str)
    # validate(raw_encoder, Optional[RawEncoder]) # TODO: typing-validation does not yet support this
    # validate(raw_decoder, Optional[RawDecoder]) # TODO: typing-validation does not yet support this
    validate(addr_size, Optional[int])
    validate(overwrite, bool)
    if addr_size is not None and addr_size < 0:
        raise MultiaddrValueError("Size must be None or non-negative integer.")
    if addr_size == 0 and (raw_encoder is not None or raw_decoder is not None):
        raise MultiaddrValueError("Protocol admits no address (addr_size=0), set raw encoder and decoder to None.")
    if not overwrite and name in _proto_impl:
        raise MultiaddrValueError(f"Implementation for protocol {repr(name)} already exists.")
    _proto_impl[name] = (raw_encoder, raw_decoder, addr_size)


def unregister(name: str) -> None:
    """
        Unregisters the implementatio for the protocol by given name.

        Example usage:

        >>> multiformats.raw.unregister("ip4")
        >>> multiformats.raw.exists("ip4")
        False

        :param name: the protocol implementation name
        :type name: :obj:`str`

        :raises KeyError: if no such protocol implementation exists
    """
    validate(name, str)
    if name not in _proto_impl:
        raise MultiaddrKeyError(f"Implementation for protocol {repr(name)} does not exist.")
    del _proto_impl[name]

def _validate_size(name: str, b: BytesLike, size: int) -> None:
    if len(b) != size:
        raise MultiaddrValueError(f"Incorrect length for {repr(name)} bytes: found {len(b)}, expected {size}.")

def ip4_encoder(s: str) -> bytes:
    """ Encoder for 'ip4' protocol. """
    validate(s, str)
    try:
        return IPv4Address(s).packed
    except AddressValueError as e:
        raise MultiaddrValueError(str(e)) from e

def ip4_decoder(b: BytesLike) -> str:
    """ Decoder for 'ip4' protocol. """
    validate(b, BytesLike)
    _validate_size('ip4', b, 4)
    try:
        return str(IPv4Address(b))
    except AddressValueError as e:
        raise MultiaddrValueError(str(e)) from e

register("ip4", ip4_encoder, ip4_decoder, 4)

def ip6_encoder(s: str) -> bytes:
    """ Encoder for 'ip6' protocol. """
    validate(s, str)
    try:
        return IPv6Address(s).packed
    except AddressValueError as e:
        raise MultiaddrValueError(str(e)) from e

def ip6_decoder(b: BytesLike) -> str:
    """ Decoder for 'ip6' protocol. """
    validate(b, BytesLike)
    _validate_size('ip6', b, 16)
    try:
        return str(IPv6Address(b))
    except AddressValueError as e:
        raise MultiaddrValueError(str(e)) from e

register("ip6", ip6_encoder, ip6_decoder, 16)

def tcp_udp_encoder(s: str) -> bytes:
    """ Encoder for 'tcp' and 'udp' protocols. """
    validate(s, str)
    if not s.isdigit():
        raise MultiaddrValueError(f"Invalid UDP port {repr(s)}.")
    x = int(s)
    if not 0 <= x < 65536:
        raise MultiaddrValueError(f"UDP port {repr(s)} out of range.")
    return x.to_bytes(2, byteorder="big")

def tcp_udp_decoder(b: BytesLike) -> str:
    """ Decoder for 'tcp' and 'udp' protocol. """
    validate(b, BytesLike)
    _validate_size('udp', b, 2)
    return str(int.from_bytes(b, byteorder="big"))

register("tcp", tcp_udp_encoder, tcp_udp_decoder, 2)
register("udp", tcp_udp_encoder, tcp_udp_decoder, 2)

# TODO: dccp, 2 bytes
# TODO: ip6zone, variable, rfc4007 IPv6 zone
# TODO: dns, variable
# TODO: dns4, variable
# TODO: dns6, variable
# TODO: dnsaddr, variable
# TODO: sctp, 2 bytes
# TODO: unix, variable
# TODO: p2p, variable
# TODO: ipfs, variable, backwards compatibility; equivalent to /p2p
# TODO: onion, 12 bytes
# TODO: onion3, 37 bytes
# TODO: garlic64, variable
# TODO: garlic32, variable
# TODO: memory, variable, in memory transport for self-dialing and testing; arbitrary

# Protocols without address value:
register("udt", None, None, 0)
register("utp", None, None, 0)
register("tls", None, None, 0)
register("noise", None, None, 0)
register("quic", None, None, 0)
register("http", None, None, 0)
register("https", None, None, 0) # deprecated alias for /tls/http
register("ws", None, None, 0) # WebSockets
register("wss", None, None, 0) # deprecated alias for /tls/ws
register("p2p-websocket-star", None, None, 0)
register("p2p-stardust", None, None, 0)
register("p2p-webrtc-star", None, None, 0)
register("p2p-webrtc-direct", None, None, 0)
register("p2p-circuit", None, None, 0)
