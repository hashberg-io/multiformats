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
- `typing-validation <https://github.com/hashberg-io/typing-validation>`_, for dynamic typechecking.
- `bases <https://github.com/hashberg-io/bases>`_, for implementation of base encodings used by Multibase.
- `multiformats-config <https://github.com/hashberg-io/multiformats-config>`_, handling pre-loading configuration of multicodec/multibase tables.

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

If you'd like to only load a selection of multicodecs and/or multibases, you can do so by calling ``multiformats_config.enable()`` **before** importing the
multiformats library, passing the desired multicodec names (as :obj:`str`) orcodes (as :obj:`int`) and the desired multibase names (as :obj:`str`) or codes (as :obj:`str` of length 1) to the ``codecs`` and ``bases`` keyword arguments, respectively:

.. code-block:: python

    import multiformats_config
    multiformats_config.enable(codecs=["sha1", 0x29], bases=["base64url", "9"])
    from multiformats import *

If ``codecs`` is not set (or set to :obj:`None`), all multicodecs are loaded. If ``bases`` is not set (or set to :obj:`None`), all multibases are loaded.
Using ``multiformats_config.enable(codecs=[], bases=[])`` results in a minimal set of (mandatory) multicodecs and multibases to be loaded:

.. code-block:: python

    _minimal_multicodecs = frozenset([
        0x00, # 'identity'
        0x01, # 'cidv1'
        0x02, # 'cidv2'
        0x12, # 'sha2-256'
        0x14, # 'sha3-512'
        0x16, # 'sha3-256'
        0x70, # 'dag-pb'
        0x71, # 'dag-cbor'
        0x72, # 'libp2p-key'
    ])

    _minimal_multibases = frozenset([
        "identity",
        "base16",
        "base32",
        "base58btc",
    ])

Calling ``multiformats_config.enable`` **after** the multiformats library has been imported will fail raising ``multiformats_config.LockedConfigError``.
The `multiformats-config <https://github.com/hashberg-io/multiformats-config>`_ repository also stores the tables specifying all multicodecs and multibases known to this package. 

GitHub repo: https://github.com/hashberg-io/multiformats
