"""
    Errors for the :mod:`~multiformats.multicodec` module.
"""

from __future__ import annotations

import builtins

class MulticodecKeyError(builtins.KeyError): # pylint: disable = redefined-builtin
    """ Class for :mod:`~multiformats.multicodec` key errors. """

class MulticodecValueError(builtins.ValueError): # pylint: disable = redefined-builtin
    """ Class for :mod:`~multiformats.multicodec` value errors. """
