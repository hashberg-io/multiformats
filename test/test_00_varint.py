""" Tests for varints. """

from io import BytesIO
from random import Random
from multiformats import varint

def test_encode_decode():
    """ Check that encoding followed by decoding yields the initial integer value. """
    random = Random(0)
    for x in range(256):
        assert varint.decode(varint.encode(x)) == x, f"Error at value {x}"
    for k in range(7, 64, 7):
        for _ in range(10):
            x = 2**(k-1)+random.randrange(256)
            x_enc = varint.encode(x)
            assert varint.decode(x_enc) == x, f"Error at value {x}"
            assert varint.decode(bytearray(x_enc)) == x, f"Error at value {x} (bytearray)"

def test_minimal_encoding():
    """ Check that encoding is minimal in number of bytes. """
    for k in range(1, 10):
        x = 2**(7*k)-1
        assert len(varint.encode(x)) == k, f"Error at {k} bytes"

def test_stream_decoding():
    """ Check that decoding from stream only reads the varint bytes. """
    num_extra_bytes = 10
    for k in range(1, 10):
        x = 2**(7*k)-1
        stream = BytesIO(varint.encode(x)+bytes(num_extra_bytes))
        varint.decode(stream)
        assert len(stream.read()) == num_extra_bytes, f"Error at {k} bytes"

def test_failure_modes():
    """ Checks varint failure modes. """
    try:
        varint.encode(-1)
        assert False, "Must not encode negative integers."
    except ValueError:
        pass
    try:
        varint.encode(2**63)
        assert False, "Must not encode integers >= 2**63."
    except ValueError:
        pass
    try:
        varint.decode(bytes())
        assert False, "Must not decode empty byte-string."
    except ValueError:
        pass
    try:
        varint.decode(bytes([255]*9+[1]))
        assert False, "Must not encode varints more than 9 bytes long."
    except ValueError:
        pass
    try:
        varint.decode(bytes([255, 255]))
        assert False, "Must not decode invalid varint (last byte is continuation)."
    except ValueError:
        pass
    try:
        varint.decode(bytes([255, 1, 1]))
        assert False, "Must not leave unread bytes when decoding from bytes or bytearray objects."
    except ValueError:
        pass
    try:
        varint.decode(bytearray([255, 1, 1]))
        assert False, "Must not leave unread bytes when decoding from bytes or bytearray objects."
    except ValueError:
        pass
    try:
        varint.decode(bytes([0x81, 0x00]))
        assert False, "Must not decode non-minimally encoded varint."
    except ValueError:
        pass
