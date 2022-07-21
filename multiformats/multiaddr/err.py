"""
    Errors for the :mod:`~multiformats.multiaddr` module.
"""

import builtins

class MultiaddrKeyError(builtins.KeyError): # pylint: disable = redefined-builtin
    """ Class for :mod:`~multiformats.multiaddr` key errors. """


class MultiaddrValueError(builtins.ValueError): # pylint: disable = redefined-builtin
    """ Class for :mod:`~multiformats.multiaddr` value errors. """
