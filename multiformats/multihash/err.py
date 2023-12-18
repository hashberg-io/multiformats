"""
    Errors for the :mod:`~multiformats.multihash` module.
"""

from __future__ import annotations

import builtins

class MultihashKeyError(builtins.KeyError): # pylint: disable = redefined-builtin
    """ Class for :mod:`~multiformats.multihash` key errors. """

class MultihashValueError(builtins.ValueError): # pylint: disable = redefined-builtin
    """ Class :mod:`~multiformats.multihash` value errors. """
