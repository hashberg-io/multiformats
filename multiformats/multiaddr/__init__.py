"""
    Implementation of the `multiaddr spec <https://github.com/multiformats/multiaddr>`_.

    Suggested usage:

    >>> from multiformats import multiaddr
"""

from __future__ import annotations

from itertools import islice, chain
from typing import Any, cast, ClassVar, Dict, Iterator, List, Optional, overload, Sequence, Tuple, Type, Union
from weakref import WeakValueDictionary
import sys
from typing_validation import validate

from multiformats import varint, multicodec
from multiformats.multicodec import Multicodec
from multiformats.varint import BytesLike, byteslike

from . import raw
from .err import MultiaddrKeyError, MultiaddrValueError
from .raw import RawEncoder, RawDecoder, ProtoImpl, _validate_size

class Proto:
    """
        Container class for a single protocol segment of a `multiaddr <https://multiformats.io/multiaddr/>`_.

        >>> ip4 = Proto("ip4")
        >>> ip4
        Proto("ip4")
        >>> str(ip4)
        '/ip4'

        For protocols that don't require an address value, bytes are computed as the varint encoding of protocol code:

        >>> quic = Proto('quic')
        >>> quic.code
        460
        >>> varint.encode(quic.code).hex()
        'cc03'
        >>> bytes(quic).hex()
        'cc03'

        :param codec: the multicodec for this protocol (by name, code, or as object)
        :type codec: :obj:`str`, :obj:`int` or :class:`~multiformats.multicodec.Multicodec`
    """

    # WeakValueDictionary[str, "Proto"]
    _cache: ClassVar[WeakValueDictionary] = WeakValueDictionary() # type: ignore

    _codec: Multicodec
    _implementation: ProtoImpl

    __slots__ = ("__weakref__", "_codec", "_implementation")

    def __new__(cls, codec: Union[str, int, Multicodec]) -> "Proto":
        # check that the codec exists:
        if isinstance(codec, str):
            codec = multicodec.get(codec)
        elif isinstance(codec, int):
            codec = multicodec.get(code=codec)
        else:
            validate(codec, Multicodec)
            existing_codec = multicodec.get(codec.name)
            if existing_codec != codec:
                raise MultiaddrValueError(f"Multicodec named {repr(codec.name)} exists, but is not the one given.")
            codec = existing_codec
        # check that the codec is a multiaddr multicodec:
        if codec.tag != "multiaddr":
            raise MultiaddrValueError(f"Multicodec named {repr(codec.name)} exists, but is not a multiaddr.")
        implementation: ProtoImpl = raw.get(codec.name)
        _cache = Proto._cache
        if codec.name in _cache:
            # if a proto instance with this name is already registered
            instance: Proto = _cache[codec.name]
            if instance._codec == codec and instance._implementation == implementation:
                # nothing changed, can use the existing instance
                return instance
            # otherwise remove the existing instance
            del _cache[codec.name]
        # create a fresh instance, register it and return it
        instance = super().__new__(cls)
        instance._codec = codec
        instance._implementation = implementation
        _cache[codec.name] = instance
        return instance

    def __getnewargs__(self) -> tuple[Multicodec]:
        return (self.codec,)

    @property
    def name(self) -> str:
        """
            Protocol name.

            Example usage:

            >>> ip4.name
            'ip4'

        """
        return self.codec.name

    @property
    def code(self) -> int:
        """
            Protocol code.

            Example usage:

            >>> ip4.code
            4
            # 4 = 0x04

        """
        return self.codec.code

    @property
    def codec(self) -> Multicodec:
        """
            The multicodec for this protocol.

            Example usage:

            >>> ip4.codec
            Multicodec(name='ip4', tag='multiaddr', code='0x04',
                       status='permanent', description='')

        """
        return self._codec

    @property
    def implementation(self) -> ProtoImpl:
        """
            The implementation for this protocol, as a triple of
            raw encoder, raw decoder and address size.

            Example usage:

            >>> ip4.implementation
            (
             <function ip4_encoder at 0x000002B4C9956310>,
             <function ip4_decoder at 0x000002B4C99563A0>,
             4
            )

            :rtype: :obj:`~multiformats.multiaddr.raw.ProtoImpl`
        """
        return self._implementation

    @property
    def raw_encoder(self) -> Optional[RawEncoder]:
        """
            The raw encoder for this protocol.

            Example usage:

            >>> ip4.raw_encoder
            <function ip4_encoder at 0x000002B4C9956310>

            :rtype: :obj:`~multiformats.multiaddr.raw.RawEncoder` or :obj:`None`
        """
        return self.implementation[0]

    @property
    def raw_decoder(self) -> Optional[RawDecoder]:
        """
            The raw decoder for this protocol.

            Example usage:

            >>> ip4.raw_decoder
            <function ip4_decoder at 0x000002B4C99563A0>

            :rtype: :obj:`~multiformats.multiaddr.raw.RawDecoder` or :obj:`None`
        """
        return self.implementation[1]

    @property
    def addr_size(self) -> Optional[int]:
        """
            The address size (in bytes) for this protocol:

            - for protocols with no address, ``addr_size`` is 0
            - for protocols with addresses of variable binary size, ``addr_size`` is :obj:`None`
            - for all other protocols, ``addr_size`` is a positive :obj:`int`

            Example usage:

            >>> ip4.addr_size
            4

        """
        return self.implementation[2]

    @property
    def admits_addr(self) -> bool:
        """
            Whether this protocol admits an address.

            >>> ip4.admits_addr
            True

        """
        return self.addr_size != 0

    def is_addr_valid(self, addr_value: Union[str, BytesLike]) -> bool:
        """
            Validates an address value.

            Example usage:

            >>> ip4.is_addr_valid("192.168.1.1")
            True
            >>> ip4.is_addr_valid(bytes([192, 168, 1, 1]))
            True

            The same result can be obtained with container syntax:

            >>> "192.168.1.1" in ip4
            True
            >>> bytes([192, 168, 1, 1]) in ip4
            True

        """
        try:
            self.validate(addr_value)
            return True
        except MultiaddrValueError:
            return False

    def validate(self, addr_value: Union[str, BytesLike]) -> Tuple[str, bytes]:
        """
            If successful, returns a pair of the string and bytes representations of the address value.

            Example usage:

            >>> ip4.validate("192.168.1.1")
            ('192.168.1.1', b'\\xc0\\xa8\\x01\\x01')
            >>> ip4.validate("192.168")
            MultiaddrValueError: Expected 4 octets in '192.168'

            :raises ValueError: if ``not self.is_valid(addr_value)``
        """
        raw_encoder, raw_decoder, addr_size = self.implementation
        if addr_size == 0:
            raise MultiaddrValueError(f"Protocol admits no address value, but {repr(addr_value)} was passed.")
        if isinstance(addr_value, byteslike):
            assert raw_decoder is not None
            addr_value_str = raw_decoder(addr_value) # raises MultiaddrValueError if addr_value is invalid
            if not isinstance(addr_value, bytes):
                addr_value = bytes(addr_value)
            return addr_value_str, addr_value
        validate(addr_value, str)
        assert raw_encoder is not None
        addr_value_bytes = raw_encoder(addr_value) # raises MultiaddrValueError if addr_value is invalid
        return addr_value, addr_value_bytes

    def addr(self, value: Union[str, BytesLike]) -> "Addr":
        """
            Returns an address for this protocol.

            Example usage:

            >>> ip4.addr("192.168.1.1")
            Addr('ip4', '192.168.1.1')
            >>> ip4.addr(bytes([192, 168, 1, 1]))
            Addr('ip4', '192.168.1.1')

            The same address can be obtained with slash syntax:

            >>> ip4/"192.168.1.256"
            Addr('ip4', '192.168.1.256')
            >>> ip4/b'\\xc0\\xa8\\x01\\x01'
            Addr('ip4', '192.168.1.1')

        """
        return Addr(self, value)

    def __contains__(self, value: Union[str, BytesLike]) -> bool:
        return self.is_addr_valid(value)

    @overload
    def __truediv__(self, value: Union["Proto", "Addr", "Multiaddr"]) -> "Multiaddr":
        ...

    @overload
    def __truediv__(self, value: Union[int, str, BytesLike]) -> "Addr":
        ...

    def __truediv__(self, value: Union[int, str, BytesLike, "Proto", "Addr", "Multiaddr"]) -> Union["Addr", "Multiaddr"]:
        if isinstance(value, int):
            value = str(value)
        if isinstance(value, (str,)+byteslike):
            return self.addr(value)
        if isinstance(value, (Addr, Proto)):
            return Multiaddr(self, value)
        if isinstance(value, Multiaddr):
            return Multiaddr(self, *value)
        return NotImplemented

    def __str__(self) -> str:
        return f"/{self.name}"

    def __bytes__(self) -> bytes:
        if self.addr_size != 0:
            raise MultiaddrValueError("Missing address value for protocol, cannot compute bytes.")
        return varint.encode(self.code)

    def __repr__(self) -> str:
        return f"Proto({repr(self.name)})"

    @property
    def _as_tuple(self) -> Tuple[Type["Proto"], Multicodec]:
        return (Proto, self.codec)

    def __hash__(self) -> int:
        return hash(self._as_tuple)

    def __eq__(self, other: Any) -> bool:
        if self is other:
            return True
        if not isinstance(other, Proto):
            return NotImplemented
        return self._as_tuple == other._as_tuple

class Addr:
    """
        Container class for a single protocol address in a `multiaddr <https://multiformats.io/multiaddr/>`_.

        >>> a = Addr('ip4', '192.168.1.1')
        >>> a
        Addr('ip4', '192.168.1.1')
        >>> str(a)
        '/ip4/192.168.1.1'

        The slash notation provides a more literate way to construct protocol addresses:

        >>> a = ip4/"192.168.1.1"
        >>> a
        Addr('ip4', '192.168.1.1')

        Bytes for protocol addresses are computed according to the `TLV multiaddr format <https://multiformats.io/multiaddr/>`_:

        >>> bytes(ip4/"127.0.0.1").hex()
        '047f000001'
        >>> varint.encode(ip4.code).hex()
        '04'
        >>> bytes([127, 0, 0, 1]).hex()
          '7f000001'

        :param proto: the protocol for this address (by name, code, multicodec or protocol object)
        :type proto: :obj:`str`, :obj:`int`, :class:`~multiformats.multicodec.Multicodec` or :class:`Proto`
        :param value: the address value (as a human-readable string or in its binary form)
        :type value: :obj:`str` or :obj:`~multiformats.varint.BytesLike`
    """

    _proto: Proto
    _value: str
    _value_bytes: bytes

    __slots__ = ("__weakref__", "_proto", "_value", "_value_bytes")

    def __new__(cls, proto: Union[str, int, Multicodec, Proto], value: Union[str, BytesLike]) -> "Addr":
        if not isinstance(proto, Proto):
            proto = Proto(proto)
        value, value_bytes = proto.validate(value)
        instance: Addr = super().__new__(cls)
        instance._proto = proto
        instance._value = value
        instance._value_bytes = value_bytes
        return instance

    @property
    def proto(self) -> Proto:
        """
            The address protocol.

            Example usage:

            >>> a = Addr('ip4', '192.168.1.1')
            >>> a.proto
            Proto('ip4')

        """
        return self._proto

    @property
    def value(self) -> str:
        """
            The address value, as a string.

            Example usage:

            >>> a = Addr('ip4', '192.168.1.1')
            >>> a.value
            '192.168.1.1'

        """
        return self._value

    @property
    def value_bytes(self) -> bytes:
        """
            The address value, as bytes.

            Example usage:

            >>> a = Addr('ip4', '192.168.1.1')
            >>> a.value_bytes
            b'\\xc0\\xa8\\x01\\x01'
            >>> list(a.value_bytes)
            [192, 168, 1, 1]

        """
        return self._value_bytes

    def __truediv__(self, other: Union[Proto, "Addr", "Multiaddr"]) -> "Multiaddr":
        if isinstance(other, (Addr, Proto)):
            return Multiaddr(self, other)
        if isinstance(other, Multiaddr):
            return Multiaddr(self, *other)
        return NotImplemented

    def __str__(self) -> str:
        return f"{str(self.proto)}/{self.value}"

    def __bytes__(self) -> bytes:
        proto = self.proto
        value_bytes = self.value_bytes
        if proto.addr_size is None:
            assert value_bytes is not None
            l = varint.encode(len(value_bytes))
            return proto.codec.wrap(l+value_bytes)
        return proto.codec.wrap(value_bytes)

    def __repr__(self) -> str:
        return f"Addr({repr(self.proto.name)}, {repr(self.value)})"

    @property
    def _as_tuple(self) -> Tuple[Type["Addr"], Proto, Optional[str]]:
        return (Addr, self.proto, self.value)

    def __hash__(self) -> int:
        return hash(self._as_tuple)

    def __eq__(self, other: Any) -> bool:
        if self is other:
            return True
        if not isinstance(other, Addr):
            return NotImplemented
        return self._as_tuple == other._as_tuple


class Multiaddr(Sequence[Union[Addr, Proto]]):
    """
        Container class for a `multiaddr <https://multiformats.io/multiaddr/>`_.

        Example usage:

        >>> ip4 = multiaddr.proto("ip4")
        >>> udp = multiaddr.proto("udp")
        >>> quic = multiaddr.proto("quic")
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

        :param addrs: a sequence of protocols (not requiring address) and protocol addresses
        :type addrs: sequence of :class:`Proto` or :class:`Addr`

        :raises ValueError: if a :class:`Proto` instance appears at a place other than the last for a protocol requiring an address
        :raises ValueError: if a procool name appears more than once
    """

    _addrs: Tuple[Union[Addr, Proto], ...]
    _proto_map: Dict[Proto, int]
    _is_incomplete: bool

    __slots__ = ("__weakref__", "_addrs", "_proto_map", "_is_incomplete")

    def __new__(cls, *addrs: Union[Addr, Proto]) -> "Multiaddr":
        l = len(addrs)
        is_incomplete = False
        proto_map: Dict[Proto, int] = {}
        for idx, addr in enumerate(addrs):
            if isinstance(addr, Proto):
                proto = addr
                if proto.addr_size != 0:
                    if idx == l-1:
                        is_incomplete = True
                    else:
                        raise MultiaddrValueError(f"Protocol {repr(proto.name)} expects an address, but is followed by another protocol instead.")
            else:
                validate(addr, Addr)
                proto = addr.proto
            if proto in proto_map:
                raise MultiaddrValueError(f"Protocol {repr(proto.name)} appears twice in multiaddr.")
            proto_map[proto] = idx
        instance: Multiaddr = super().__new__(cls)
        instance._addrs = addrs
        instance._proto_map = proto_map
        instance._is_incomplete = is_incomplete
        return instance

    @property
    def is_incomplete(self) -> bool:
        """
            Whether this multiaddress is incomplete, i.e. it still requires an address for
            the last protocol in the sequence.

            >>> ma = ip4/"127.0.0.1"/udp
            >>> ma.is_incomplete
            True
            >>> str(ma)
            '/ip4/127.0.0.1/udp'
            >>> ma2 = ma/9090
            >>> str(ma2)
            '/ip4/127.0.0.1/udp/9090'
            >>> ma2.is_incomplete
            False

            Incomplete multiaddrs don't admit a byte representation:

            >>> bytes(ma)
            MultiaddrValueError: Missing address value for last protocol, cannot compute bytes.
            >>> bytes(ma2).hex()
            '047f00000191022382'

        """
        return self._is_incomplete

    def index(self, value: Union[Addr, Proto], start: int = 0, stop: Optional[int] = None) -> int:
        """
            Returns the unique index at which a protocol/address appears in the multiaddress:

            >>> ma = ip4/"127.0.0.1"/udp/9090/quic
            >>> str(ma)
            '/ip4/127.0.0.1/udp/9090/quic'
            >>> udp in ma
            True
            >>> ma.index(udp)
            1
            >>> ma[ma.index(udp)]
            Addr('udp', '9090')
            >>> ip4/"127.0.0.1" in ma
            True
            >>> ma.index(ip4/"127.0.0.1" in ma)
            0

            :param value: the protocol or protocol address being looked for
            :type value: :class:`Proto` or :class:`Addr`
            :param start: the optional starting index (include) for the search range
            :type start: :obj:`int`, *optional*
            :param stop: the optional stoppping index (excluded) for the search range
            :type stop: :obj:`int` or :obj:`None`, *optional*

            >>> ip4/"127.0.0.1" in ma
            True
            >>> ma.index(ip4/"127.0.0.1")
            0
            >>> ma.index(ip4/"127.0.0.1", start=1)
            MultiaddrValueError: Address Addr('ip4', '127.0.0.1') does not appear in sub-multiaddr /udp/9090/quic of multiaddr /ip4/127.0.0.1/udp/9090/quic

            :raises ValueError: if the protocol/address does not appear:

            >>> ip6 = Proto("ip6")
            >>> ip6 in ma
            False
            >>> ma.index(ip6)
            MultiaddrValueError: Protocol 'ip6' does not appear in multiaddr /ip4/127.0.0.1/udp/9090/quic
            >>> ip4/"127.0.0.2" in ma
            False
            >>> ma.index(ip4/"127.0.0.2")
            MultiaddrValueError: Address Addr('ip4', '127.0.0.2') does not appear in multiaddr /ip4/127.0.0.1/udp/9090/quic

        """
        validate(start, int)
        if stop is None:
            stop = len(self)
        validate(stop, int)
        if isinstance(value, Proto):
            proto = value
        else:
            validate(value, Addr)
            proto = value.proto
        if proto not in self._proto_map:
            raise MultiaddrValueError(f"Protocol {repr(proto.name)} does not appear in multiaddr {str(self)}")
        idx = self._proto_map[proto]
        if isinstance(value, Addr):
            if self[idx] != value:
                raise MultiaddrValueError(f"Address {repr(value)} does not appear in multiaddr {str(self)}")
            if not start <= idx < stop:
                raise MultiaddrValueError(f"Address {repr(value)} does not appear in sub-multiaddr {str(self[start:stop])} "
                                 f"of multiaddr {str(self)}")
        return idx

    def __contains__(self, value: Any) -> bool:
        if isinstance(value, (Addr, Proto)):
            try:
                self.index(value)
                return True
            except MultiaddrValueError:
                return False
        return False

    def __len__(self) -> int:
        return len(self._addrs)

    def __iter__(self) -> Iterator[Union[Addr, Proto]]:
        return iter(self._addrs)

    @overload
    def __getitem__(self, idx: int) -> Union[Addr, Proto]:
        ...

    @overload
    def __getitem__(self, idx: slice) -> "Multiaddr":
        ...

    def __getitem__(self, idx: Union[int, slice]) -> Union[Addr, Proto, "Multiaddr"]:
        if isinstance(idx, int):
            return self._addrs[idx]
        validate(idx, slice)
        return Multiaddr(*self._addrs[idx])

    def __truediv__(self, other: Union[int, str, BytesLike, Addr, Proto, "Multiaddr"]) -> "Multiaddr":
        if isinstance(other, (int, str,)+byteslike):
            if not self.is_incomplete:
                raise MultiaddrValueError("Unexpected address value. Expected Proto, Addr or Multiaddr.")
            addrs = list(self)
            tail_proto = addrs[-1]
            assert isinstance(tail_proto, Proto)
            return Multiaddr(*islice(addrs, 0, len(addrs)-1), tail_proto/other)
        if isinstance(other, (Addr, Proto)):
            if self.is_incomplete:
                raise MultiaddrValueError("Expected address value (string or binary).")
            return Multiaddr(*self, other)
        if isinstance(other, Multiaddr):
            if self.is_incomplete:
                raise MultiaddrValueError("Expected address value (string or binary).")
            return Multiaddr(*self, *other)
        return NotImplemented

    def __str__(self) -> str:
        return "".join(str(a) for a in self)

    def __bytes__(self) -> bytes:
        if self.is_incomplete:
            raise MultiaddrValueError("Missing address value for last protocol, cannot compute bytes.")
        return bytes(chain.from_iterable(bytes(addr) for addr in self))

    def __repr__(self) -> str:
        return f"Multiaddr({', '.join(repr(a) for a in self)})"

    @property
    def _as_tuple(self) -> Tuple[Type["Multiaddr"], Tuple[Union[Addr, Proto], ...]]:
        return (Multiaddr, self._addrs)

    def __hash__(self) -> int:
        return hash(self._as_tuple)

    def __eq__(self, other: Any) -> bool:
        if self is other:
            return True
        if not isinstance(other, Multiaddr):
            return NotImplemented
        return self._as_tuple == other._as_tuple


def proto(name: Union[str, int, Multicodec]) -> Proto:
    """
        Convenience function to construct a :class:`Proto` instance.

        Example usage:

        >>> ip4 = multiaddr.proto("ip4")
        >>> ip4
        Proto("ip4")

        :param name: the protocol name, multicodec code or multicodec object
        :type name: :obj:`str`, :obj:`int` or :class:`~multiformats.multicodec.Multicodec`

    """
    return Proto(name)

def parse(s: str, allow_incomplete: bool = False) -> Multiaddr:
    """
        Parses a multiaddr from its human-readable string representation.

        Example usage:

        >>> s = '/ip4/127.0.0.1/udp/9090/quic'
        >>> multiaddr.parse(s)
        Multiaddr(Addr('ip4', '127.0.0.1'), Addr('udp', '9090'), Proto('quic'))

        Example usage with incomplete multiaddr:

        >>> s = '/ip4/127.0.0.1/udp'
        >>> multiaddr.parse(s)
        MultiaddrValueError: Decoded multiaddr is incomplete: /ip4/127.0.0.1/udp
        >>> multiaddr.parse(s, allow_incomplete=True)
        Multiaddr(Addr('ip4', '127.0.0.1'), Proto('udp'))

        :param s: the multiaddress in human-readable string form
        :type s: :obj:`str`
        :param allow_incomplete: whether to allow incomplete multiaddresses
        :type allow_incomplete: :obj:`bool`

        :raises ValueError: if ``allow_incomplete`` is :obj:`False` and the parsed multiaddress is incomplete
    """
    validate(s, str)
    validate(allow_incomplete, bool)
    tokens = s.split("/")
    protocol: Optional[Proto] = None
    segments: List[Union[Addr, Proto]] = []
    for token in islice(tokens, 1, None):
        if protocol is None:
            protocol = Proto(token)
            if not protocol.admits_addr:
                segments.append(protocol)
                protocol = None
        else:
            segments.append(protocol/token)
            protocol = None
    if protocol is not None:
        segments.append(protocol)
    ma = Multiaddr(*segments)
    if ma.is_incomplete and not allow_incomplete:
        raise MultiaddrValueError(f"Decoded multiaddr is incomplete: {str(ma)}")
    return ma


def decode(b: BytesLike) -> Multiaddr:
    """
        Decodes a multiaddr from its `(TLV)+` binary encoding.

        Example usage:

        >>> b = bytes.fromhex('047f00000191022382cc03')
        >>> multiaddr.decode(b)
        Multiaddr(Addr('ip4', '127.0.0.1'), Addr('udp', '9090'), Proto('quic'))

        :param b: the multiaddress in binary form
        :type b: :obj:`~multiformats.varint.BytesLike`
    """
    validate(b, BytesLike)
    b = memoryview(b)
    segments: List[Union[Addr, Proto]] = []
    while len(b) > 0:
        code, _, b = multicodec.unwrap_raw(b)
        protocol = Proto(code)
        if protocol.admits_addr:
            addr_size = protocol.addr_size
            if addr_size is None:
                addr_size, _, b = varint.decode_raw(b)
            addr_value_bytes = bytes(b[:addr_size])
            b = b[addr_size:]
            segments.append(protocol/addr_value_bytes)
        else:
            segments.append(protocol)
    ma = Multiaddr(*segments)
    assert not ma.is_incomplete
    return ma
