Getting Started
===============

A Python implementation of the `multiformat protocols <https://multiformats.io/>`_:

    - :doc:`varint` implements the `unsigned varint spec <https://github.com/multiformats/unsigned-varint>`_
    - :doc:`multicodec` implements the `multicodec spec <https://github.com/multiformats/multicodec>`_
    - :doc:`multibase` implements the `multibase spec <https://github.com/multiformats/multicodec>`_
    - :doc:`multihash` implements the `multihash spec <https://github.com/multiformats/multihash>`_
    - :doc:`cid` implements the `Content IDentifier spec <https://github.com/multiformats/cid>`_
    - :doc:`multiaddr` implements the `multiaddr spec <https://github.com/multiformats/multiaddr>`_

You can install the latest release from `PyPI <https://pypi.org/project/multiformats/>`_ as follows:

.. code-block:: console

    $ pip install --upgrade multiformats

You can import multiformat protocols directly from top level:

>>> from multiformats import *

The above will import the following names:

.. code-block:: python

    varint, multicodec, multibase, multihash, multiaddr, CID

The first five are modules implementing the homonymous specifications,
while :class:`~multiformats.cid.CID` is a class for Content IDentifiers.

The following are mandatory dependencies for this module:

- `typing-extensions <https://github.com/python/typing_extensions>`_, for backward compatibility of static typing.
- `typing-validation <https://github.com/hashberg-io/typing-validation>`_, for dynamic typechecking
- `bases <https://github.com/hashberg-io/bases>`_, for implementation of base encodings used by Multibase

The following are optional dependencies for this module:

- `pysha3 <https://github.com/tiran/pysha3>`_, for the ``keccak`` hash functions.
- `blake3 <https://github.com/oconnor663/blake3-py>`_, for the ``blake3`` hash function.
- `pyskein <https://pythonhosted.org/pyskein/>`_, for the ``skein`` hash functions.
- `mmh3 <https://github.com/hajimes/mmh3>`_, for the ``murmur3`` hash functions.
- `pycryptodomex <https://github.com/Legrandin/pycryptodome/>`_, for the ``ripemd-160`` hash function, \
  the ``kangarootwelve`` hash function and the ``sha2-512-224``/``sha2-512-256`` hash functions.

You can install the latest release together with all optional dependencies as follows:

.. code-block:: console

    $ pip install --upgrade multiformats[full]

GitHub repo: https://github.com/hashberg-io/multiformats
