""" Tests for the `multiformats.varint` module. """


from io import BytesIO
from random import Random

import pytest
from multiformats import varint

random = Random(0)

@pytest.mark.parametrize("x", range(256))
def test_encode_decode_byte(x: int) -> None:
    """ Check that encoding followed by decoding yields the initial integer value. """
    assert varint.decode(varint.encode(x)) == x, f"Error at value {x}"


@pytest.mark.parametrize("k", range(7, 64, 7))
def test_encode_decode_bytes(k: int) -> None:
    """ Check that encoding followed by decoding yields the initial integer value. """
    for _ in range(10):
        x = 2**(k-1)+random.randrange(256)
        x_enc = varint.encode(x)
        assert varint.decode(x_enc) == x, f"Error at value {x}"
        assert varint.decode(bytearray(x_enc)) == x, f"Error at value {x} (bytearray)"


@pytest.mark.parametrize("k", range(1, 10))
def test_minimal_encoding(k: int) -> None:
    """ Check that encoding is minimal in number of bytes. """
    x = 2**(7*k)-1
    assert len(varint.encode(x)) == k, f"Error at {k} bytes"

@pytest.mark.parametrize("k", range(1, 10))
def test_stream_decoding(k: int) -> None:
    """ Check that decoding from stream only reads the varint bytes. """
    num_extra_bytes = 10
    x = 2**(7*k)-1
    stream = BytesIO(varint.encode(x)+bytes(num_extra_bytes))
    varint.decode(stream)
    assert len(stream.read()) == num_extra_bytes, f"Error at {k} bytes"

invalid_encodes = [
    (-1, "Must not encode negative integers."),
    (2**63, "Must not encode integers >= 2**63.")
]

@pytest.mark.parametrize("val, reason", invalid_encodes)
def test_encode_failure(val: int, reason: str) -> None:
    """ Checks varint encode failure modes. """
    try:
        varint.encode(val)
        assert False, reason
    except ValueError:
        pass

invalid_decodes = [
    (bytes(), "Must not decode empty byte-string."),
    (bytes([255]*9+[1]), "Must not encode varints more than 9 bytes long."),
    (bytes([255, 255]), "Must not decode invalid varint (last byte is continuation)."),
    (bytes([255, 1, 1]), "Must not leave unread bytes when decoding from bytes or bytearray objects."),
    (bytearray([255, 1, 1]), "Must not leave unread bytes when decoding from bytes or bytearray objects."),
    (bytes([0x81, 0x00]), "Must not decode non-minimally encoded varint."),
]

@pytest.mark.parametrize("val, reason", invalid_decodes)
def test_decode_failure(val: bytes, reason: str) -> None:
    """ Checks varint decode failure modes. """
    try:
        varint.decode(val)
        assert False, reason
    except ValueError:
        pass
