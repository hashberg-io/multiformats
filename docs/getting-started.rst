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

GitHub repo: https://github.com/hashberg-io/multiformats
