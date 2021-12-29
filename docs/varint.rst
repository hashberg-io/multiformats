Varint
======

The :mod:`~multiformats.varint` module implements the `unsigned varint spec <https://github.com/multiformats/unsigned-varint>`_.

Functionality is provided by the :func:`~multiformats.varint.encode` and :func:`~multiformats.varint.decode` functions, converting between non-negative :py:obj:`int` values and the corresponding varint :py:obj:`bytes`: 

>>> from multiformats import varint
>>> varint.encode(128)
b'\x80\x01'
>>> varint.decode(b'\x80\x01')
128
