"""
    Errors for the `multiformats.multiaddr` module.
"""

import builtins

class KeyError(builtins.KeyError): # pylint: disable = redefined-builtin
    """ Class `multiformats.multiaddr` key errors. """
    ...

class ValueError(builtins.ValueError): # pylint: disable = redefined-builtin
    """ Class `multiformats.multiaddr` value errors. """
    ...
