Multibase
=========

The :mod:`~multiformats.multibase` module implements the `multibase spec <https://github.com/multiformats/multibase>`_.

>>> from multiformats import multibase


Multibase
---------

The :class:`~multiformats.multibase.Multibase` class provides a container for multibase encoding data:

>>> from multiformats.multibase import Multibase
>>> Multibase(name="base16", code="f",
              status="default", description="hexadecimal")
    Multibase(name='base16', code='f',
              status='default', description='hexadecimal')


encode, decode
--------------

The :func:`~multiformats.multibase.encode` and :func:`~multiformats.multibase.decode` functions can be used to encode a bytestring into a string using a chosen multibase encoding and to decode a string into a bytestring using the multibase encoding specified by its first character:

>>> multibase.encode(b"Hello World!", "base32")
'bjbswy3dpeblw64tmmqqq'
>>> multibase.decode('bjbswy3dpeblw64tmmqqq')
b'Hello World!'

:class:`~multiformats.multibase.Multibase` objects have :meth:`~multiformats.multibase.Multibase.encode` and :meth:`~multiformats.multibase.Multibase.decode` methods that perform functionality analogous to the homonymous functions:

>>> base32 = multibase.get("base32")
>>> base32.encode(b"Hello World!")
'bjbswy3dpeblw64tmmqqq'
>>> base32.decode('bjbswy3dpeblw64tmmqqq')
b'Hello World!'

The :meth:`~multiformats.multibase.Multibase.decode` method includes additional encoding validation:

>>> base32.decode('Bjbswy3dpeblw64tmmqqq')
err.ValueError: Expected 'base32' encoding,
                found 'base32upper' encoding instead.

from_str
--------

The multibase encoding specified by a given string is accessible using the :func:`~multiformats.multibase.from_str` function:

>>> multibase.from_str('bjbswy3dpeblw64tmmqqq')
Multibase(encoding='base32', code='b',
          status='default',
          description='rfc4648 case-insensitive - no padding')

get, exists
-----------

Additional encoding management functionality is provided by the :func:`~multiformats.multibase.exists` and :func:`~multiformats.multibase.get` functions,
which can be used to check whether an encoding with given name or code is known, and if so to get the corresponding object:

>>> multibase.exists("base32")
True
>>> multibase.get("base32")
Multibase(encoding='base32', code='b',
          status='default',
          description='rfc4648 case-insensitive - no padding')
>>> multibase.exists(code="f")
True
>>> multibase.get(code="f")
Multibase(encoding="base16", code="f",
          status="default", description="hexadecimal")

table
-----

The :func:`~multiformats.multibase.table` function can be used to iterate through known multibase encodings:

>>> list(enc.name for enc in multibase.table())
['identity', 'base2', 'base8', 'base10', 'base32upper',
 'base32padupper', 'base16upper', 'base36upper', 'base64pad',
 'base32hexpadupper', 'base64urlpad', 'base32hexupper',
 'base58flickr', 'base32', 'base32pad', 'base16', 'base32z',
 'base36', 'base64', 'proquint', 'base32hexpad', 'base64url',
 'base32hex', 'base58btc']
