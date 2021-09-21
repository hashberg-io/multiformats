""" Tests for varints. """

from multiformats import varint

def test_encode_decode():
    """ Check that encoding followed by decoding yields the initial integer value. """
    for x in range(256):
        assert varint.decode(varint.encode(x)) == x, f"Error at value {x}"
    for k in range(7, 64, 7):
        for x in [2**k-2**i for i in range(8)]:
            assert varint.decode(varint.encode(x)) == x, f"Error at value {x}"

def test_minimal_encoding():
    """ Check that encoding is minimal in number of bytes. """
    for k in range(1, 10):
        x = 2**(7*k)-1
        assert len(varint.encode(x)) == k, f"Error at {k} bits"

def test_failure_modes():
    """ Checks varint failure modes. """
    try:
        varint.encode(-1)
        assert False, "Cannot encode negative integers."
    except ValueError:
        pass
    try:
        varint.encode(2**63)
        assert False, "Cannot encode integers >= 2**63."
    except ValueError:
        pass
    try:
        varint.decode(bytes())
        assert False, "Cannot decode empty byte-string."
    except ValueError:
        pass
    try:
        varint.decode(bytes([255]*9+[1]))
        assert False, "Cannot encode varints more than 9 bytes long."
    except ValueError:
        pass
    try:
        varint.decode(bytes([255, 255]))
        assert False, "Cannot decode invalid varint (last byte is continuation)."
    except ValueError:
        pass
    try:
        varint.decode(bytes([255, 1, 1]))
        assert False, "Cannot decode invalid varint (non-last byte is not continuation)."
    except ValueError:
        pass
    try:
        varint.decode(bytes([0x81, 0x00]))
        assert False, "Cannot succesfully decode non-minimally encoded varint."
    except ValueError:
        pass
